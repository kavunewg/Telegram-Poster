"""
Маршруты для YouTube мониторинга
"""
import json
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.youtube_repo import youtube_repo
from repositories.channel_repo import channel_repo
from repositories.bot_repo import bot_repo
from services.youtube_service import get_youtube_channel_info
from core.config import TELEGRAM_TOKEN

router = APIRouter(tags=["youtube"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    """Единая функция получения текущего пользователя"""
    user = getattr(request.state, "user", None)
    if not user:
        session_id = request.cookies.get("session_id")
        if session_id:
            user = user_repo.get_by_session(session_id)
    return user


@router.post("/add_youtube_channel")
async def add_youtube_channel_endpoint(
    request: Request,
    youtube_url: str = Form(...),
    target_channels: str = Form(...),
    post_template: str = Form(None),
    include_description: int = Form(0),
    button_url: str = Form(None),
    button_style: str = Form('success')
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    user_data = user_repo.get_by_id(user["id"])
    if not user_data:
        return RedirectResponse(url="/login", status_code=303)
    
    user_api_key = user_data.get("youtube_api_key")
    if not user_api_key:
        return RedirectResponse(
            url="/my_channels?error=Сначала добавьте YouTube API ключ в настройках профиля",
            status_code=303
        )
    
    channel_info = await get_youtube_channel_info(youtube_url, user_api_key)
    if "error" in channel_info:
        return RedirectResponse(url=f"/my_channels?error={channel_info['error']}", status_code=303)
    
    target_list = json.loads(target_channels)
    
    youtube_repo.add_channel(
        user["id"],
        channel_info['id'],
        channel_info['name'],
        channel_info['url'],
        target_list,
        post_template,
        include_description,
        button_url,
        button_style
    )
    
    return RedirectResponse(url="/my_channels?success=YouTube канал добавлен", status_code=303)


@router.post("/delete_youtube_channel/{channel_id}")
async def delete_youtube_channel_endpoint(request: Request, channel_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    if youtube_repo.delete(channel_id, user["id"]):
        return RedirectResponse(url="/my_channels?success=Канал удален", status_code=303)
    return RedirectResponse(url="/my_channels?error=Ошибка удаления", status_code=303)


@router.post("/toggle_youtube_channel/{channel_id}")
async def toggle_youtube_channel_endpoint(
    request: Request,
    channel_id: int,
    is_active: int = Form(...)
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    if youtube_repo.toggle_active(channel_id, user["id"], bool(is_active)):
        return RedirectResponse(url="/my_channels?success=Статус обновлен", status_code=303)
    return RedirectResponse(url="/my_channels?error=Ошибка обновления", status_code=303)


@router.get("/get_youtube_channel/{channel_id}")
async def get_youtube_channel(request: Request, channel_id: int):
    """Получение данных YouTube канала для модального окна"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Получаем канал
    channel = youtube_repo.get_channel_by_id(channel_id, user["id"])
    
    if not channel:
        return JSONResponse({"error": "Channel not found"}, status_code=404)
    
    # Преобразуем Row в dict
    channel_dict = dict(channel)
    
    # Возвращаем только нужные для модалки поля
    return JSONResponse({
        'id': channel_dict.get('id'),
        'youtube_channel_name': channel_dict.get('youtube_channel_name'),
        'youtube_channel_url': channel_dict.get('youtube_channel_url'),
        'post_template': channel_dict.get('post_template'),
        'include_description': bool(channel_dict.get('include_description', 0))
    })

@router.post("/update_youtube_channel")
async def update_youtube_channel(
    request: Request,
    channel_id: int = Form(...),
    post_template: str = Form(None),
    include_description: int = Form(0)
):
    """Обновление YouTube канала (без target_channels)"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Получаем текущий канал, чтобы сохранить существующие target_channels
    current_channel = youtube_repo.get_channel_by_id(channel_id, user["id"])
    
    if not current_channel:
        return RedirectResponse(url="/my_channels?error=Канал не найден", status_code=303)
    
    # Сохраняем существующие target_channels или пустой список
    current_targets = current_channel.get('target_channels', '[]')
    
    success = youtube_repo.update_channel(
        channel_id, 
        user["id"], 
        current_targets,  # оставляем существующие целевые каналы
        post_template, 
        include_description,
        None,  # button_url
        'success'  # button_style
    )
    
    if success:
        return RedirectResponse(url="/my_channels?success=YouTube канал обновлен", status_code=303)
    else:
        return RedirectResponse(url="/my_channels?error=Ошибка обновления", status_code=303)


@router.get("/api/youtube_channel_info")
async def api_youtube_channel_info(request: Request, url: str):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    user_data = user_repo.get_by_id(user["id"])
    user_api_key = user_data.get("youtube_api_key") if user_data else None
    
    info = await get_youtube_channel_info(url, user_api_key)
    return JSONResponse(info)