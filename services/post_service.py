"""
Сервис для отправки постов в Telegram и MAX
"""
import asyncio
import os
import json
import logging
from typing import Dict, Optional

import aiohttp
from telegram.error import RetryAfter

from core.config import TELEGRAM_TOKEN, REQUEST_CONFIG, ALLOWED_EXTENSIONS
from repositories.post_stats_repo import post_stats_repo
from repositories.channel_repo import channel_repo
from repositories.bot_repo import bot_repo
from services.media_service import delete_media_file

logger = logging.getLogger(__name__)


def setup_logger(name: str) -> logging.Logger:
    """Настройка логгера"""
    return logging.getLogger(name)


# =========================
# RETRY для Telegram
# =========================
async def safe_telegram_call(func, *args, retries=5, **kwargs):
    """Безопасный вызов Telegram API с повторами"""
    for attempt in range(retries):
        try:
            return await func(*args, **kwargs)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception as e:
            if attempt == retries - 1:
                raise e
            await asyncio.sleep(2 ** attempt)


# =========================
# TELEGRAM
# =========================
async def send_to_telegram(channel_session: dict, session_id: str) -> dict:
    """Отправка поста в Telegram с поддержкой цветных кнопок (Bot API 9.4+)"""
    log = setup_logger(__name__)
    
    log.info("🔍 send_to_telegram вызвана")
    log.info(f"   channel_session keys: {list(channel_session.keys())}")
    
    # Получаем токен бота
    bot_token = channel_session.get('bot_token')
    
    if not bot_token:
        user_id = channel_session.get('user_id')
        if user_id:
            bots = bot_repo.get_user_bots(user_id)
            for bot in bots:
                if bot.get('platform') == 'telegram':
                    bot_token = bot.get('token')
                    break
    
    if not bot_token:
        error_msg = "Отсутствует токен бота"
        log.error(error_msg)
        return {"success": False, "error": error_msg}
    
    log.info(f"   bot_token: {bot_token[:20]}...")
    
    # Получаем ID канала
    channel_id_raw = channel_session.get('channel_id')
    
    # Нормализуем channel_id
    if isinstance(channel_id_raw, str):
        if channel_id_raw.startswith('@'):
            channel_id = channel_id_raw
        else:
            try:
                channel_id = int(channel_id_raw)
            except ValueError:
                return {"success": False, "error": f"Неверный channel_id: {channel_id_raw}"}
    elif isinstance(channel_id_raw, int):
        channel_id = channel_id_raw
    else:
        return {"success": False, "error": f"Неверный формат channel_id: {channel_id_raw}"}
    
    log.info(f"   channel_id: {channel_id}")
    
    # Получаем текст поста
    caption = channel_session.get('post_text', '')
    if not caption:
        return {"success": False, "error": "Отсутствует текст поста"}
    
    media_path = channel_session.get("media_path")
    media_type = channel_session.get("media_type", "text")
    button_config = channel_session.get("button")
    
    # ========== КНОПКА С ЦВЕТОМ (Bot API 9.4+) ==========
    reply_markup = None
    if button_config and button_config.get("text") and button_config.get("url"):
        button_text = button_config["text"]
        button_url = button_config["url"]
        button_style = button_config.get("style", "")  # primary, success, danger или пусто
        
        # Создаём кнопку
        button = {
            "text": button_text,
            "url": button_url
        }
        
        # Добавляем цвет ТОЛЬКО для валидных значений (Bot API 9.4+)
        if button_style in ["primary", "success", "danger"]:
            button["style"] = button_style
            log.info(f"   🎨 кнопка с цветом: {button_style}")
        else:
            log.info(f"   🔘 кнопка без цвета (стандартная)")
        
        # Создаём inline клавиатуру
        keyboard = {
            "inline_keyboard": [[button]]
        }
        reply_markup = json.dumps(keyboard)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Отправка с медиа
            if media_path and os.path.exists(media_path):
                file_ext = os.path.splitext(media_path)[1].lower()
                
                if file_ext in ALLOWED_EXTENSIONS.get('video', []):
                    method = "sendVideo"
                    field_name = "video"
                elif file_ext in ALLOWED_EXTENSIONS.get('photo', []):
                    method = "sendPhoto"
                    field_name = "photo"
                else:
                    method = "sendDocument"
                    field_name = "document"
                
                log.info(f"   📤 отправка с медиа, метод: {method}")
                
                with open(media_path, "rb") as f:
                    data = aiohttp.FormData()
                    data.add_field("chat_id", str(channel_id))
                    data.add_field("caption", caption)
                    data.add_field("parse_mode", "HTML")
                    
                    if reply_markup:
                        data.add_field("reply_markup", reply_markup)
                    
                    data.add_field(field_name, f, filename=os.path.basename(media_path))
                    
                    url = f"https://api.telegram.org/bot{bot_token}/{method}"
                    
                    async with session.post(url, data=data) as resp:
                        result = await resp.json()
                        
                        if not result.get("ok"):
                            raise Exception(result.get("description", "Unknown error"))
                        
                        log.info(f"   ✅ медиа отправлено, message_id: {result.get('result', {}).get('message_id')}")
            
            # Отправка без медиа
            else:
                log.info("   📤 отправка текстового сообщения")
                
                payload = {
                    "chat_id": channel_id,
                    "text": caption,
                    "parse_mode": "HTML"
                }
                
                if reply_markup:
                    payload["reply_markup"] = reply_markup
                
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                
                async with session.post(url, json=payload) as resp:
                    result = await resp.json()
                    
                    if not result.get("ok"):
                        raise Exception(result.get("description", "Unknown error"))
                    
                    log.info(f"   ✅ сообщение отправлено, message_id: {result.get('result', {}).get('message_id')}")
        
        # Успешная отправка
        log.info("✅ Пост успешно отправлен!")
        
        post_stats_repo.add_stat(
            channel_session.get("user_id"),
            channel_session.get("channel_db_id"),
            "telegram",
            caption,
            media_type,
            "success"
        )
        
        if media_path and os.path.exists(media_path):
            delete_media_file(media_path)
        
        return {"success": True, "message": "Post sent successfully"}
    
    except Exception as e:
        error_msg = str(e)
        log.error(f"❌ Ошибка отправки: {error_msg}")
        
        post_stats_repo.add_stat(
            channel_session.get("user_id"),
            channel_session.get("channel_db_id"),
            "telegram",
            caption,
            media_type,
            "error",
            error_msg
        )
        
        return {"success": False, "error": error_msg}


# =========================
# MAX
# =========================
async def send_to_max(channel_session: dict, session_id: str) -> dict:
    """Отправка поста в MAX"""
    log = setup_logger(__name__)
    log.info("🔍 send_to_max вызвана")
    
    try:
        # TODO: Реализовать реальную отправку в MAX
        # Пока имитируем успешную отправку
        await asyncio.sleep(1)
        
        caption = channel_session.get('post_text', '')
        media_type = channel_session.get("media_type", "text")
        
        log.info("✅ Пост в MAX отправлен (заглушка)")
        
        # Сохраняем статистику
        post_stats_repo.add_stat(
            channel_session.get("user_id"),
            channel_session.get("channel_db_id"),
            "max",
            caption,
            media_type,
            "success"
        )
        
        # Удаляем медиафайл
        media_path = channel_session.get("media_path")
        if media_path and os.path.exists(media_path):
            delete_media_file(media_path)
        
        return {"success": True, "message": "MAX post sent (mock)"}
    
    except Exception as e:
        error_msg = str(e)
        log.error(f"❌ Ошибка отправки в MAX: {error_msg}")
        
        post_stats_repo.add_stat(
            channel_session.get("user_id"),
            channel_session.get("channel_db_id"),
            "max",
            channel_session.get('post_text', ''),
            channel_session.get("media_type", "text"),
            "error",
            error_msg
        )
        
        return {"success": False, "error": error_msg}
    
    # services/post_service.py

async def send_to_vk(channel_session: dict, session_id: str) -> dict:
    """Отправка поста в VK"""
    log = setup_logger(__name__)
    
    log.info("🔍 send_to_vk вызвана")
    
    # Получаем токен бота
    bot_token = channel_session.get('bot_token')
    if not bot_token:
        user_id = channel_session.get('user_id')
        if user_id:
            from repositories.bot_repo import bot_repo
            bots = bot_repo.get_user_bots(user_id)
            for bot in bots:
                if bot.get('platform') == 'vk':
                    bot_token = bot.get('token')
                    break
    
    if not bot_token:
        error_msg = "Отсутствует токен VK. Добавьте VK бота на странице 'Мои боты'"
        log.error(error_msg)
        return {"success": False, "error": error_msg}
    
    # Получаем ID группы
    group_id = channel_session.get('channel_id')
    if not group_id:
        error_msg = "Отсутствует ID группы VK"
        log.error(error_msg)
        return {"success": False, "error": error_msg}
    
    try:
        group_id = int(group_id)
    except ValueError:
        error_msg = f"Неверный ID группы VK: {group_id}"
        log.error(error_msg)
        return {"success": False, "error": error_msg}
    
    # Получаем текст поста
    post_text = channel_session.get('post_text', '')
    if not post_text:
        error_msg = "Отсутствует текст поста"
        log.error(error_msg)
        return {"success": False, "error": error_msg}
    
    # Получаем медиафайл
    media_path = channel_session.get('media_path')
    button = channel_session.get('button')
    
    # Добавляем кнопку в текст если есть
    if button and button.get('text') and button.get('url'):
        post_text += f"\n\n🔗 {button['text']}: {button['url']}"
    
    try:
        from services.vk_service import VKService
        
        vk = VKService(bot_token)
        
        # Отправляем пост
        result = await vk.post_to_wall(
            owner_id=-abs(group_id),  # Отрицательный ID для группы
            message=post_text,
            from_group=True
        )
        
        log.info(f"✅ Пост отправлен в VK группу {group_id}")
        
        # Сохраняем статистику
        post_stats_repo.add_stat(
            channel_session.get("user_id"),
            channel_session.get("channel_db_id"),
            "vk",
            post_text,
            channel_session.get("media_type", "text"),
            "success"
        )
        
        # Удаляем медиафайл
        if media_path and os.path.exists(media_path):
            delete_media_file(media_path)
        
        return {"success": True, "post_id": result.get("post_id")}
        
    except Exception as e:
        error_msg = str(e)
        log.error(f"❌ Ошибка отправки в VK: {error_msg}")
        
        post_stats_repo.add_stat(
            channel_session.get("user_id"),
            channel_session.get("channel_db_id"),
            "vk",
            post_text,
            channel_session.get("media_type", "text"),
            "error",
            error_msg
        )
        
        return {"success": False, "error": error_msg}


# =========================
# ОТПРАВКА ВО ВСЕ КАНАЛЫ (для прямого вызова)
# =========================
async def send_post_async(
    user_id: int,
    channel_id: int,
    text: str,
    media_path: str = None,
    button: dict = None
) -> bool:
    """Отправка поста в один канал (для прямого вызова)"""
    log = setup_logger(__name__)
    
    log.info(f"🔍 Поиск канала: id={channel_id}, user_id={user_id}")
    
    # Получаем канал
    channel = channel_repo.get_channel_by_id(channel_id, user_id)
    
    if not channel:
        error_msg = f"Канал не найден: id={channel_id}, user_id={user_id}"
        log.error(error_msg)
        raise Exception(error_msg)
    
    log.info(f"✅ Канал найден: {channel.get('channel_name')}")
    
    # Получаем бота для канала
    bot_token = None
    bots = bot_repo.get_user_bots(user_id)
    for bot in bots:
        if bot.get('platform') == channel.get('platform'):
            bot_token = bot.get('token')
            break
    
    # Формируем сессию
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
        "bot_token": bot_token
    }
    
    try:
        # Роутинг по платформе
        if channel_session["platform"] == "telegram":
            log.info("📤 Отправка в Telegram")
            result = await send_to_telegram(channel_session, "direct")
        elif channel_session["platform"] == "max":
            log.info("📤 Отправка в MAX")
            result = await send_to_max(channel_session, "direct")
        else:
            raise Exception(f"Неизвестная платформа: {channel_session['platform']}")
        
        # Проверяем результат
        if result.get("success"):
            log.info("✅ send_post_async завершён успешно")
            return True
        else:
            raise Exception(result.get("error", "Unknown error"))
    
    except Exception as e:
        log.error(f"❌ Ошибка send_post_async: {str(e)}")
        raise