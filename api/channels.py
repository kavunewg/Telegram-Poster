"""
Маршруты для управления каналами
"""
import json
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.channel_repo import channel_repo
from repositories.bot_repo import bot_repo
from repositories.youtube_repo import youtube_repo

# Добавляем импорт vk_repo
try:
    from repositories.vk_repo import vk_repo
    VK_AVAILABLE = True
except ImportError:
    VK_AVAILABLE = False
    vk_repo = None

router = APIRouter(tags=["channels"])
templates: Jinja2Templates = None


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
    channel_name: str = Form(...),
    channel_id: str = Form(...),
    channel_url: str = Form(None),
    platform: str = Form('telegram'),
    api_key: str = Form(None),
    bot_id: int = Form(None)
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    new_channel_id = channel_repo.add_channel(
        user["id"], channel_name, channel_id, channel_url, platform, api_key
    )
    
    if bot_id and new_channel_id:
        bot_repo.add_bot_channel(bot_id, new_channel_id)
    
    return RedirectResponse(url="/my_channels?success=Канал добавлен", status_code=303)


@router.post("/update_channel")
async def update_channel(
    request: Request,
    channel_id: int = Form(...),
    channel_name: str = Form(...),
    channel_id_value: str = Form(...),
    channel_url: str = Form(None),
    platform: str = Form('telegram'),
    api_key: str = Form(None),
    bot_id: int = Form(None)
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    success = channel_repo.update_channel(
        channel_id, user["id"], channel_name, channel_id_value, channel_url, platform, api_key
    )
    
    if not success:
        return RedirectResponse(url="/my_channels?error=Канал не найден", status_code=303)
    
    from core.database import get_db_connection
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bot_channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
    
    if bot_id and bot_id > 0:
        bot_repo.add_bot_channel(bot_id, channel_id)
    
    return RedirectResponse(url="/my_channels?success=Канал обновлен", status_code=303)


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
        channel_repo.delete_channel(channel_id, user["id"])
        return RedirectResponse(url="/my_channels?success=Канал удален", status_code=303)
    
    return RedirectResponse(url="/my_channels?error=Канал не найден", status_code=303)


@router.post("/delete_channel/")
async def delete_channel_post(request: Request):
    """Удаление канала - альтернативный маршрут для форм"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    form_data = await request.form()
    channel_id = form_data.get("channel_id")
    
    if not channel_id:
        return RedirectResponse(url="/my_channels?error=Не указан ID канала", status_code=303)
    
    try:
        channel_id = int(channel_id)
    except ValueError:
        return RedirectResponse(url="/my_channels?error=Неверный ID канала", status_code=303)
    
    channels = channel_repo.get_user_channels(user["id"])
    channel_ids = [ch.get("id") for ch in channels]
    
    if channel_id in channel_ids:
        channel_repo.delete_channel(channel_id, user["id"])
        return RedirectResponse(url="/my_channels?success=Канал удален", status_code=303)
    
    return RedirectResponse(url="/my_channels?error=Канал не найден", status_code=303)