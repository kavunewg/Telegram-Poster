"""
Маршруты для управления каналами
"""
import json
import logging
from urllib.parse import urlencode
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.channel_repo import channel_repo
from repositories.bot_repo import bot_repo
from repositories.youtube_repo import youtube_repo
from services.youtube_service import get_youtube_channel_info

# Добавляем импорт vk_repo
try:
    from repositories.vk_repo import vk_repo
    VK_AVAILABLE = True
except ImportError:
    VK_AVAILABLE = False
    vk_repo = None

router = APIRouter(tags=["channels"])
templates: Jinja2Templates = None
logger = logging.getLogger(__name__)


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    """Унифицированное получение текущего пользователя"""
    user = getattr(request.state, "user", None)
    if not user:
        session_id = request.cookies.get("session_id")
        if session_id:
            user = user_repo.get_by_session(session_id)
    return user


def _validate_platform_bot(user_id: int, bot_id: int | None, platform: str):
    if not bot_id:
        return None

    bot = bot_repo.get_by_id(bot_id, user_id)
    if not bot:
        return "Бот не найден"

    bot_platform = (bot.get("platform") or "").lower()
    channel_platform = (platform or "telegram").lower()
    if bot_platform != channel_platform:
        return f"Нельзя привязать бота платформы {bot_platform} к каналу платформы {channel_platform}"

    return None


def _my_channels_redirect(*, success: str = None, error: str = None):
    params = {}
    if success:
        params["success"] = success
    if error:
        params["error"] = error
    suffix = f"?{urlencode(params)}" if params else ""
    return RedirectResponse(url=f"/my_channels{suffix}", status_code=303)


def _parse_optional_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_youtube_api_key(user_id: int, bot_id: int = None):
    bot_key = bot_repo.get_user_youtube_api_key(user_id, bot_id)
    if bot_key and str(bot_key).strip():
        return str(bot_key).strip()

    return None


def _default_youtube_targets(user_id: int):
    user_channels = channel_repo.get_user_channels(user_id)
    return [
        {
            "id": ch.get("id"),
            "name": ch.get("channel_name"),
            "channel_name": ch.get("channel_name"),
            "channel_id": ch.get("channel_id"),
            "platform": ch.get("platform", "telegram"),
            "bot_token": ch.get("bot_token"),
        }
        for ch in user_channels
        if ch.get("platform") == "telegram"
    ]


@router.get("/my_channels", response_class=HTMLResponse)
async def my_channels_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Получаем все каналы
    channels = channel_repo.get_user_channels(user["id"])
    
    # Разделяем по платформам
    telegram_channels = [ch for ch in channels if ch.get("platform") == "telegram"]
    max_channels = [ch for ch in channels if ch.get("platform") == "max"]
    
    # Получаем ботов
    bots = bot_repo.get_user_bots(user["id"])
    
    # Получаем YouTube каналы
    youtube_channels = youtube_repo.get_user_channels(user["id"])
    
    # Получаем VK каналы (если модуль доступен)
    vk_channels = []
    if VK_AVAILABLE and vk_repo:
        vk_channels = vk_repo.get_user_channels(user["id"])
    
    return templates.TemplateResponse("my_channels.html", {
        "request": request,
        "user": user,
        "telegram_channels": telegram_channels,
        "max_channels": max_channels,
        "telegram_count": len(telegram_channels),
        "max_count": len(max_channels),
        "youtube_channels": youtube_channels,
        "youtube_count": len(youtube_channels),
        "vk_channels": vk_channels,
        "vk_count": len(vk_channels),
        "bots": bots,
        "project_name": user.get("project_name")
    })


@router.get("/get_channel/{channel_id}")
async def get_channel(request: Request, channel_id: int):
    """Получение данных канала для редактирования"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Получаем канал
    channels = channel_repo.get_user_channels(user["id"])
    channel = next((ch for ch in channels if ch.get("id") == channel_id), None)
    
    if not channel:
        return JSONResponse({"error": "Channel not found"}, status_code=404)
    
    # Получаем привязанного бота
    from core.database import get_db_connection
    bot_id = None
    bot_name = None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT bc.bot_id, ub.name 
            FROM bot_channels bc
            JOIN user_bots ub ON bc.bot_id = ub.id
            WHERE bc.channel_id = ?
        """, (channel_id,))
        row = cursor.fetchone()
        if row:
            bot_id = row[0]
            bot_name = row[1]
    
    return JSONResponse({
        "id": channel.get("id"),
        "channel_name": channel.get("channel_name"),
        "channel_id": channel.get("channel_id"),
        "channel_url": channel.get("channel_url"),
        "platform": channel.get("platform"),
        "bot_id": bot_id,
        "bot_name": bot_name
    })


@router.post("/add_channel")
async def add_channel(
    request: Request,
    channel_name: str = Form(""),
    channel_id: str = Form(...),
    channel_url: str = Form(None),
    platform: str = Form('telegram'),
    api_key: str = Form(None),
    bot_id: str = Form(None)
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    parsed_bot_id = _parse_optional_int(bot_id)
    validation_error = _validate_platform_bot(user["id"], parsed_bot_id, platform)
    if validation_error:
        return _my_channels_redirect(error=validation_error)

    if (platform or "").lower() == "youtube":
        if not parsed_bot_id:
            return _my_channels_redirect(error="Для YouTube выберите YouTube API key в поле бота")

        youtube_api_key = _resolve_youtube_api_key(user["id"], parsed_bot_id)
        if not youtube_api_key:
            return _my_channels_redirect(error="Сначала добавьте YouTube API key в разделе Мои боты")

        channel_info = await get_youtube_channel_info(channel_id, youtube_api_key)
        if "error" in channel_info:
            return _my_channels_redirect(error=channel_info["error"])

        youtube_repo.add_channel(
            user["id"],
            channel_info["id"],
            channel_info["name"],
            channel_info["url"],
            _default_youtube_targets(user["id"]),
            None,
            0,
            None,
            "success",
            parsed_bot_id,
        )
        return _my_channels_redirect(success="YouTube канал добавлен")
    
    new_channel_id = channel_repo.add_channel(
        user["id"], channel_name, channel_id, channel_url, platform, api_key
    )
    
    if parsed_bot_id and new_channel_id:
        bot_repo.add_bot_channel(parsed_bot_id, new_channel_id)
    
    return _my_channels_redirect(success="Канал добавлен")


@router.post("/update_channel")
async def update_channel(
    request: Request,
    channel_id: int = Form(...),
    channel_name: str = Form(...),
    channel_id_value: str = Form(...),
    channel_url: str = Form(None),
    platform: str = Form('telegram'),
    api_key: str = Form(None),
    bot_id: str = Form(None)
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    parsed_bot_id = _parse_optional_int(bot_id)
    validation_error = _validate_platform_bot(user["id"], parsed_bot_id, platform)
    if validation_error:
        return _my_channels_redirect(error=validation_error)
    
    success = channel_repo.update_channel(
        channel_id, user["id"], channel_name, channel_id_value, channel_url, platform, api_key
    )
    
    if not success:
        return _my_channels_redirect(error="Канал не найден")
    
    from core.database import get_db_connection
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bot_channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
    
    if parsed_bot_id and parsed_bot_id > 0:
        bot_repo.add_bot_channel(parsed_bot_id, channel_id)
    
    return _my_channels_redirect(success="Канал обновлен")


@router.post("/delete_channel/{channel_id}")
async def delete_channel_by_id(request: Request, channel_id: int):
    """Удаление канала по ID из URL"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Проверяем, что канал принадлежит пользователю
    channels = channel_repo.get_user_channels(user["id"])
    channel_ids = [ch.get("id") for ch in channels]
    
    if channel_id in channel_ids:
        try:
            channel_repo.delete_channel(channel_id, user["id"])
        except Exception as exc:
            logger.exception("Channel delete failed: user_id=%s channel_id=%s", user["id"], channel_id)
            return _my_channels_redirect(error=f"Ошибка удаления канала: {exc}")
        return _my_channels_redirect(success="Канал удален")
    
    return _my_channels_redirect(error="Канал не найден")


@router.post("/delete_channel/")
async def delete_channel_post(request: Request):
    """Удаление канала - альтернативный маршрут для форм"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    form_data = await request.form()
    channel_id = form_data.get("channel_id")
    
    if not channel_id:
        return _my_channels_redirect(error="Не указан ID канала")
    
    try:
        channel_id = int(channel_id)
    except ValueError:
        return _my_channels_redirect(error="Неверный ID канала")
    
    channels = channel_repo.get_user_channels(user["id"])
    channel_ids = [ch.get("id") for ch in channels]
    
    if channel_id in channel_ids:
        try:
            channel_repo.delete_channel(channel_id, user["id"])
        except Exception as exc:
            logger.exception("Channel delete failed (form): user_id=%s channel_id=%s", user["id"], channel_id)
            return _my_channels_redirect(error=f"Ошибка удаления канала: {exc}")
        return _my_channels_redirect(success="Канал удален")
    
    return _my_channels_redirect(error="Канал не найден")
