"""
Services for sending posts to external platforms.
"""

import asyncio
import json
import logging
import os

import aiohttp

from repositories.bot_repo import bot_repo
from repositories.channel_repo import channel_repo
from repositories.post_stats_repo import post_stats_repo

logger = logging.getLogger(__name__)


def setup_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


async def send_to_telegram(channel_session: dict, session_id: str) -> dict:
    log = setup_logger(__name__)
    bot_token = channel_session.get("bot_token")

    if not bot_token and channel_session.get("user_id"):
        for bot in bot_repo.get_user_bots(channel_session["user_id"]):
            if bot.get("platform") == "telegram":
                bot_token = bot.get("token")
                break

    if not bot_token:
        return {"success": False, "error": "Bot token not found"}

    channel_id = channel_session.get("channel_id")
    if not channel_id:
        return {"success": False, "error": "Channel ID not found"}

    caption = channel_session.get("post_text", "")
    if not caption:
        return {"success": False, "error": "Post text is empty"}

    media_path = channel_session.get("media_path")
    media_type = channel_session.get("media_type", "text")
    button = channel_session.get("button")
    reply_markup = None
    if button and button.get("text") and button.get("url"):
        tg_button = {"text": button["text"], "url": button["url"]}
        button_style = (button.get("style") or "").strip().lower()
        # Backward-compatible: older project versions sent Telegram button style directly.
        if button_style in {"primary", "success", "danger"}:
            tg_button["style"] = button_style
        reply_markup = {"inline_keyboard": [[tg_button]]}

    try:
        async with aiohttp.ClientSession() as session:
            if media_path and os.path.exists(media_path):
                ext = os.path.splitext(media_path)[1].lower()
                if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                    method = "sendPhoto"
                    field_name = "photo"
                elif ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
                    method = "sendVideo"
                    field_name = "video"
                else:
                    method = "sendDocument"
                    field_name = "document"

                with open(media_path, "rb") as file_obj:
                    data = aiohttp.FormData()
                    data.add_field("chat_id", str(channel_id))
                    data.add_field("caption", caption)
                    data.add_field("parse_mode", "HTML")
                    if reply_markup:
                        data.add_field("reply_markup", json.dumps(reply_markup))
                    data.add_field(field_name, file_obj, filename=os.path.basename(media_path))

                    url = f"https://api.telegram.org/bot{bot_token}/{method}"
                    async with session.post(url, data=data) as response:
                        result = await response.json()
            else:
                payload = {"chat_id": channel_id, "text": caption, "parse_mode": "HTML"}
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                async with session.post(url, json=payload) as response:
                    result = await response.json()

        if not result.get("ok"):
            raise Exception(result.get("description", "Unknown Telegram error"))

        post_stats_repo.add_stat(
            channel_session.get("user_id"),
            channel_session.get("channel_db_id"),
            "telegram",
            caption,
            media_type,
            "success",
        )

        return {"success": True, "message": "Post sent successfully"}
    except Exception as exc:
        error_msg = str(exc)
        log.error("Telegram send failed: %s", error_msg)
        post_stats_repo.add_stat(
            channel_session.get("user_id"),
            channel_session.get("channel_db_id"),
            "telegram",
            caption,
            media_type,
            "error",
            error_msg,
        )
        return {"success": False, "error": error_msg}


async def send_to_max(channel_session: dict, session_id: str) -> dict:
    log = setup_logger(__name__)
    await asyncio.sleep(0.1)
    caption = channel_session.get("post_text", "")
    media_type = channel_session.get("media_type", "text")

    post_stats_repo.add_stat(
        channel_session.get("user_id"),
        channel_session.get("channel_db_id"),
        "max",
        caption,
        media_type,
        "success",
    )

    log.info("MAX send is still mocked")
    return {"success": True, "message": "MAX post sent (mock)"}


async def send_to_vk(channel_session: dict, session_id: str) -> dict:
    log = setup_logger(__name__)

    bot_token = channel_session.get("bot_token")
    if not bot_token and channel_session.get("user_id"):
        for bot in bot_repo.get_user_bots(channel_session["user_id"]):
            if bot.get("platform") == "vk":
                bot_token = bot.get("token")
                break

    group_id = channel_session.get("channel_id")
    post_text = channel_session.get("post_text", "")
    if not bot_token:
        return {"success": False, "error": "VK token not found"}
    if not group_id:
        return {"success": False, "error": "VK group ID not found"}
    if not post_text:
        return {"success": False, "error": "Post text is empty"}

    button = channel_session.get("button")
    if button and button.get("text") and button.get("url"):
        post_text += f"\n\n{button['text']}: {button['url']}"

    try:
        from services.vk_service import VKService

        vk = VKService(bot_token)
        result = await vk.post_to_wall(owner_id=-abs(int(group_id)), message=post_text, from_group=True)

        post_stats_repo.add_stat(
            channel_session.get("user_id"),
            channel_session.get("channel_db_id"),
            "vk",
            post_text,
            channel_session.get("media_type", "text"),
            "success",
        )

        return {"success": True, "post_id": result.get("post_id")}
    except Exception as exc:
        error_msg = str(exc)
        log.error("VK send failed: %s", error_msg)
        post_stats_repo.add_stat(
            channel_session.get("user_id"),
            channel_session.get("channel_db_id"),
            "vk",
            post_text,
            channel_session.get("media_type", "text"),
            "error",
            error_msg,
        )
        return {"success": False, "error": error_msg}


async def send_post_async(
    user_id_or_session_id,
    channel_id_or_session,
    text: str = None,
    media_path: str = None,
    button: dict = None,
):
    """Compatibility layer for direct sends and session-based queue/scheduler sends."""
    if isinstance(channel_id_or_session, dict):
        session_id = str(user_id_or_session_id)
        session = channel_id_or_session
        results = {"success": 0, "failed": 0}

        for channel in session.get("channels", []):
            channel_session = {
                "user_id": session.get("user_id"),
                "channel_db_id": channel.get("id"),
                "channel_id": channel.get("channel_id"),
                "channel_name": channel.get("channel_name") or channel.get("name"),
                "platform": channel.get("platform", "telegram"),
                "post_text": session.get("post_text", ""),
                "media_path": session.get("media_path"),
                "media_name": session.get("media_name"),
                "media_size": session.get("media_size"),
                "media_type": session.get("media_type", "text"),
                "button": session.get("button"),
                "bot_token": channel.get("bot_token") or channel.get("token"),
            }

            if channel_session["platform"] == "telegram":
                result = await send_to_telegram(channel_session, session_id)
            elif channel_session["platform"] == "max":
                result = await send_to_max(channel_session, session_id)
            elif channel_session["platform"] == "vk":
                result = await send_to_vk(channel_session, session_id)
            else:
                result = {"success": False, "error": f"Unknown platform: {channel_session['platform']}"}

            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1

        return results

    user_id = user_id_or_session_id
    channel_id = channel_id_or_session
    channel = channel_repo.get_channel_by_id(channel_id, user_id)
    if not channel:
        raise Exception(f"Channel not found: id={channel_id}, user_id={user_id}")

    channel_session = {
        "user_id": user_id,
        "channel_db_id": channel.get("id"),
        "channel_id": channel.get("channel_id"),
        "channel_name": channel.get("channel_name"),
        "platform": channel.get("platform", "telegram"),
        "post_text": text,
        "media_path": media_path,
        "media_type": "text" if not media_path else "media",
        "button": button,
        "bot_token": channel.get("bot_token"),
    }

    if channel_session["platform"] == "telegram":
        result = await send_to_telegram(channel_session, "direct")
    elif channel_session["platform"] == "max":
        result = await send_to_max(channel_session, "direct")
    elif channel_session["platform"] == "vk":
        result = await send_to_vk(channel_session, "direct")
    else:
        raise Exception(f"Unknown platform: {channel_session['platform']}")

    if result.get("success"):
        return True

    raise Exception(result.get("error", "Unknown error"))
