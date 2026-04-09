"""
Service helpers for YouTube API and monitoring.
"""
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    build = None
    HttpError = Exception
    logger.warning("google-api-python-client is not installed; YouTube monitoring is unavailable")


async def get_youtube_channel_info(url_or_id: str, api_key: str = None) -> Dict:
    if not YOUTUBE_AVAILABLE:
        return {"error": "YouTube API не установлен. Установите google-api-python-client"}

    if not api_key:
        from core.config import YOUTUBE_API_KEY

        api_key = YOUTUBE_API_KEY

    if not api_key:
        return {"error": "Не указан YouTube API ключ"}

    try:
        channel_id = _extract_channel_id(url_or_id)
        youtube = build("youtube", "v3", developerKey=api_key)

        if channel_id:
            request = youtube.channels().list(part="snippet,statistics", id=channel_id)
        else:
            request = youtube.channels().list(part="snippet,statistics", forUsername=url_or_id)

        response = request.execute()
        if not response.get("items"):
            return {"error": "Канал не найден"}

        channel = response["items"][0]
        return {
            "id": channel["id"],
            "name": channel["snippet"]["title"],
            "description": channel["snippet"].get("description", ""),
            "url": f"https://youtube.com/channel/{channel['id']}",
            "subscriber_count": channel["statistics"].get("subscriberCount", 0),
            "video_count": channel["statistics"].get("videoCount", 0),
            "view_count": channel["statistics"].get("viewCount", 0),
            "thumbnail": channel["snippet"]["thumbnails"]["default"]["url"],
        }
    except HttpError as exc:
        error_msg = f"YouTube API ошибка: {exc}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as exc:
        error_msg = f"Ошибка получения информации о канале: {exc}"
        logger.error(error_msg)
        return {"error": error_msg}


def _extract_channel_id(url_or_id: str) -> Optional[str]:
    import re

    if url_or_id.startswith("UC") and len(url_or_id) == 24:
        return url_or_id

    patterns = [
        r"youtube\.com/channel/([^/?]+)",
        r"youtube\.com/c/([^/?]+)",
        r"youtube\.com/@([^/?]+)",
        r"youtu\.be/([^/?]+)",
        r"youtube\.com/watch\?v=([^&]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)

    return None


async def get_latest_video(channel_id: str, api_key: str) -> Optional[Dict]:
    if not YOUTUBE_AVAILABLE or not api_key:
        return None

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=1,
            order="date",
            type="video",
        )
        response = request.execute()
        if not response["items"]:
            return None

        video = response["items"][0]
        video_id = video["id"]["videoId"]
        video_request = youtube.videos().list(part="snippet,statistics,contentDetails", id=video_id)
        video_response = video_request.execute()

        if not video_response["items"]:
            return None

        video_info = video_response["items"][0]
        return {
            "id": video_id,
            "title": video_info["snippet"]["title"],
            "description": video_info["snippet"]["description"][:500] if video_info["snippet"]["description"] else "",
            "thumbnail": video_info["snippet"]["thumbnails"]["high"]["url"],
            "url": f"https://youtu.be/{video_id}",
            "published_at": video_info["snippet"]["publishedAt"],
            "duration": video_info["contentDetails"].get("duration", ""),
            "views": video_info["statistics"].get("viewCount", 0),
        }
    except Exception as exc:
        logger.error("Ошибка получения видео: %s", exc)
        return None


def format_youtube_post(
    video_info: Dict,
    channel_name: str,
    template: str = None,
    include_description: bool = False,
    button_url: str = None,
    button_style: str = "success",
) -> Tuple[str, Optional[Dict]]:
    if template and "\\u" in template:
        try:
            template = template.encode("utf-8").decode("unicode-escape")
        except Exception:
            pass

    if button_url and "\\u" in button_url:
        try:
            button_url = button_url.encode("utf-8").decode("unicode-escape")
        except Exception:
            pass

    if template:
        post = template
        post = post.replace("{video_title}", video_info.get("title", ""))
        post = post.replace("{video_url}", video_info.get("url", ""))
        post = post.replace("{channel_name}", channel_name)
        post = post.replace("{views}", str(video_info.get("views", "0")))
        if include_description and video_info.get("description"):
            post = post.replace("{video_description}", video_info.get("description", "")[:300])
        else:
            post = post.replace("{video_description}", "")
    else:
        post = "НОВОЕ ВИДЕО!\n\n"
        post += f"{video_info.get('title', '')}\n\n"
        if include_description and video_info.get("description"):
            post += f"{video_info['description'][:200]}...\n\n"
        post += video_info.get("url", "")

    button = None
    if button_url:
        button = {
            "text": "Подписаться",
            "url": button_url,
            "style": button_style or "success",
        }

    return post, button


async def check_youtube_channels():
    if not YOUTUBE_AVAILABLE:
        logger.info("YouTube API client is unavailable, skipping monitor pass")
        return

    import uuid

    from core.config import TELEGRAM_TOKEN
    from core.database import get_db_connection
    from repositories.youtube_repo import youtube_repo
    from services.post_service import send_to_telegram

    active_channels = youtube_repo.get_active_channels()
    logger.info("Checking %s active YouTube channels", len(active_channels))

    for channel in active_channels:
        channel_id = channel["id"]
        user_id = channel["user_id"]
        youtube_channel_id = channel["youtube_channel_id"]
        youtube_channel_name = channel["youtube_channel_name"]
        target_channels = channel.get("target_channels", [])
        post_template = channel.get("post_template")
        include_description = bool(channel.get("include_description"))
        last_video_id = channel.get("last_video_id")
        user_api_key = channel.get("youtube_api_key")
        button_url = channel.get("button_url")
        button_style = channel.get("button_style", "success")

        if not user_api_key:
            logger.warning("Skipping YouTube channel %s because user %s has no API key", youtube_channel_name, user_id)
            continue

        try:
            video_info = await get_latest_video(youtube_channel_id, user_api_key)
            if not video_info or video_info["id"] == last_video_id:
                logger.debug("No new videos for %s", youtube_channel_name)
                continue

            logger.info("New video detected for %s: %s", youtube_channel_name, video_info["id"])
            post_text, button = format_youtube_post(
                video_info,
                youtube_channel_name,
                post_template,
                include_description,
                button_url,
                button_style,
            )

            for target_channel in target_channels:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            SELECT b.token FROM user_channels uc
                            JOIN bot_channels bc ON bc.channel_id = uc.id
                            JOIN user_bots b ON bc.bot_id = b.id
                            WHERE uc.id = ?
                            """,
                            (target_channel.get("id"),),
                        )
                        bot_row = cursor.fetchone()
                        bot_token = bot_row[0] if bot_row else TELEGRAM_TOKEN

                    channel_session = {
                        "user_id": user_id,
                        "channel_db_id": target_channel.get("id"),
                        "channel_id": target_channel.get("channel_id"),
                        "channel_name": target_channel.get("name"),
                        "platform": "telegram",
                        "post_text": post_text,
                        "media_path": None,
                        "media_name": None,
                        "media_size": None,
                        "media_type": "text",
                        "button": button,
                        "bot_token": bot_token,
                    }

                    await send_to_telegram(channel_session, str(uuid.uuid4()))
                    logger.info("YouTube notification sent to %s", target_channel.get("name"))
                except Exception as exc:
                    logger.error("Failed to send YouTube notification to %s: %s", target_channel.get("name"), exc)

            youtube_repo.update_last_video(channel_id, video_info["id"])
        except Exception as exc:
            logger.exception("YouTube monitor failed for channel %s: %s", youtube_channel_name, exc)
