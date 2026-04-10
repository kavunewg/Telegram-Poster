"""
Services for sending posts to external platforms.
"""

import asyncio
import json
import logging
import os

import aiohttp

from typing import Dict, Any, Optional, List
from datetime import datetime
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
    """
    Отправка сообщения в MAX с поддержкой:
    - текста
    - фото (image)
    - видео (video)
    - кнопки (inline_keyboard)
    """
    log = logging.getLogger(__name__)
    
    # Нормализация ключей
    if 'text' in channel_session and 'post_text' not in channel_session:
        channel_session['post_text'] = channel_session['text']
        log.info("🔧 Перенесён ключ 'text' в 'post_text'")
    
    # 1. Получение токена бота
    bot_token = channel_session.get("bot_token")
    
    if not bot_token and channel_session.get("user_id"):
        user_bots = bot_repo.get_user_bots(channel_session["user_id"])
        max_bot = next((bot for bot in user_bots if bot.get("platform") == "max"), None)
        if max_bot:
            bot_token = max_bot.get("token")
    
    if not bot_token:
        return {"success": False, "error": "Bot token not found"}

    # 2. Получение ID чата
    channel_id = channel_session.get("channel_id")
    if not channel_id:
        return {"success": False, "error": "Channel ID not found"}

    # 3. Получение текста
    caption = channel_session.get("post_text", "")
    if not caption:
        return {"success": False, "error": "Post text is empty"}

    # ========== 4. ОБРАБОТКА МЕДИА ==========
    media_path = channel_session.get("media_path")
    media_attachment = None
    
    if media_path and os.path.exists(media_path):
        ext = os.path.splitext(media_path)[1].lower()
        
        # 4.1 ВИДЕО
        if ext in ['.mp4', '.mov', '.mkv', '.webm']:
            log.info(f"📤 Загрузка видео: {media_path}")
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Шаг 1: Получаем URL и токен для видео
                    upload_url_req = "https://platform-api.max.ru/uploads?type=video"
                    headers = {"Authorization": bot_token}
                    
                    async with session.post(upload_url_req, headers=headers) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            raise Exception(f"Failed to get upload URL: {error_text}")
                        
                        upload_data = await resp.json()
                        upload_url = upload_data.get("url")
                        video_token = upload_data.get("token")
                        
                        if not upload_url or not video_token:
                            raise Exception(f"Missing url or token: {upload_data}")
                        
                        log.info(f"📥 Получен токен для видео")
                    
                    # Шаг 2: Загружаем видео
                    with open(media_path, 'rb') as f:
                        form_data = aiohttp.FormData()
                        form_data.add_field('data', f, filename=os.path.basename(media_path))
                        
                        async with session.post(upload_url, headers=headers, data=form_data) as upload_resp:
                            if upload_resp.status != 200:
                                error_text = await upload_resp.text()
                                raise Exception(f"Failed to upload video: {error_text}")
                            
                            log.info(f"📥 Видео загружено")
                    
                    # Шаг 3: Формируем attachment
                    media_attachment = {
                        "type": "video",
                        "payload": {"token": video_token}
                    }
                    log.info("✅ Видео готово к отправке")
                    await asyncio.sleep(1)
                    
            except Exception as e:
                log.error(f"❌ Ошибка при загрузке видео: {e}")
                media_attachment = None
        
        # 4.2 ИЗОБРАЖЕНИЕ
        elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
            log.info(f"📤 Загрузка изображения: {media_path}")
            
            try:
                async with aiohttp.ClientSession() as session:
                    # Шаг 1: Получаем URL для загрузки изображения
                    upload_url_req = "https://platform-api.max.ru/uploads?type=image"
                    headers = {"Authorization": bot_token}
                    
                    async with session.post(upload_url_req, headers=headers) as resp:
                        if resp.status != 200:
                            error_text = await resp.text()
                            raise Exception(f"Failed to get upload URL: {error_text}")
                        
                        upload_data = await resp.json()
                        upload_url = upload_data.get("url")
                        
                        if not upload_url:
                            raise Exception(f"No upload URL: {upload_data}")
                        
                        log.info(f"📥 Получен URL для изображения")
                    
                    # Шаг 2: Загружаем изображение
                    with open(media_path, 'rb') as f:
                        form_data = aiohttp.FormData()
                        form_data.add_field('data', f, filename=os.path.basename(media_path))
                        
                        async with session.post(upload_url, headers=headers, data=form_data) as upload_resp:
                            if upload_resp.status != 200:
                                error_text = await upload_resp.text()
                                raise Exception(f"Failed to upload image: {error_text}")
                            
                            upload_result = await upload_resp.json()
                            log.info(f"📥 Изображение загружено")
                    
                    # Шаг 3: Формируем attachment
                    media_attachment = {
                        "type": "image",
                        "payload": upload_result
                    }
                    log.info("✅ Изображение готово к отправке")
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                log.error(f"❌ Ошибка при загрузке изображения: {e}")
                media_attachment = None
        
        else:
            log.warning(f"⚠️ Неподдерживаемый тип файла: {ext}")

       # ========== 5. ФОРМИРОВАНИЕ КНОПКИ (ИСПРАВЛЕННЫЙ ФОРМАТ) ==========
    button_attachment = None
    button = channel_session.get("button")
    if button and button.get("text") and button.get("url"):
        # ВАЖНО: MAX Bot API НЕ поддерживает цвет кнопки в сообщениях бота.
        # Убираем поле "color", оставляем только обязательные "type", "text", "url".
        button_attachment = {
            "type": "inline_keyboard",
            "payload": {
                "buttons": [
                    [
                        {
                            "type": "link",
                            "text": button["text"],
                            "url": button["url"]
                        }
                    ]
                ]
            }
        }
        
        log.info(f"🔘 Добавлена кнопка: {button['text']}")

    # ========== 6. ОТПРАВКА СООБЩЕНИЯ ==========
    url = f"https://platform-api.max.ru/messages?chat_id={channel_id}"
    headers = {
        "Authorization": bot_token,
        "Content-Type": "application/json"
    }
    
    # Собираем attachments
    attachments = []
    if media_attachment:
        attachments.append(media_attachment)
    if button_attachment:
        attachments.append(button_attachment)
    
    payload = {"text": caption}
    if attachments:
        payload["attachments"] = attachments
    
    # Ограничение длины текста (MAX: 4000 символов)
    if len(payload["text"]) > 4000:
        payload["text"] = payload["text"][:3997] + "..."
    
    # Логируем payload для отладки
    import json
    log.info(f"📤 Отправка в MAX:")
    log.info(f"   Chat ID: {channel_id}")
    log.info(f"   Текст: {caption[:100]}...")
    log.info(f"   Attachments: {len(attachments)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                response_text = await response.text()
                log.info(f"📥 Ответ MAX API: статус {response.status}")
                
                if response.status == 200:
                    # Успешная отправка
                    post_stats_repo.add_stat(
                        user_id=channel_session.get("user_id"),
                        channel_db_id=channel_session.get("channel_db_id"),
                        platform="max",
                        post_text=caption,
                        media_type=channel_session.get("media_type", "text"),
                        status="success",
                    )
                    
                    # Удаляем временный медиафайл
                    if media_path and os.path.exists(media_path):
                        try:
                            os.remove(media_path)
                            log.info(f"🗑️ Удалён медиафайл: {media_path}")
                        except Exception as e:
                            log.warning(f"Не удалось удалить файл: {e}")
                    
                    return {"success": True, "message": "Post sent successfully"}
                else:
                    error_msg = f"MAX API error {response.status}: {response_text[:200]}"
                    raise Exception(error_msg)
                    
    except Exception as exc:
        error_msg = str(exc)
        log.error(f"❌ MAX send failed: {error_msg}")
        
        post_stats_repo.add_stat(
            user_id=channel_session.get("user_id"),
            channel_db_id=channel_session.get("channel_db_id"),
            platform="max",
            post_text=caption,
            media_type=channel_session.get("media_type", "text"),
            status="error",
            error=error_msg,
        )
        
        # Удаляем временный медиафайл даже при ошибке
        if media_path and os.path.exists(media_path):
            try:
                os.remove(media_path)
                log.info(f"🗑️ Удалён медиафайл после ошибки: {media_path}")
            except Exception:
                pass
        
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
