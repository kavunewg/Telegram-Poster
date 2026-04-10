"""
Маршруты для YouTube мониторинга
"""
import json
from datetime import datetime
from urllib.parse import urlencode
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


def resolve_youtube_api_key(user_id: int) -> str | None:
    user_data = user_repo.get_by_id(user_id)
    profile_key = (user_data or {}).get("youtube_api_key")
    if profile_key and str(profile_key).strip():
        return str(profile_key).strip()

    bot_key = bot_repo.get_user_youtube_api_key(user_id)
    if bot_key and str(bot_key).strip():
        return str(bot_key).strip()

    return None


def _my_channels_redirect(*, success: str = None, error: str = None):
    params = {}
    if success:
        params["success"] = success
    if error:
        params["error"] = error
    suffix = f"?{urlencode(params)}" if params else ""
    return RedirectResponse(url=f"/my_channels{suffix}", status_code=303)


@router.post("/add_youtube_channel")
async def add_youtube_channel_endpoint(
    request: Request,
    youtube_url: str = Form(...),
    target_channels: str = Form(None),
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
    
    user_api_key = resolve_youtube_api_key(user["id"])
    if not user_api_key:
        return RedirectResponse(
            url="/my_channels?error=Сначала добавьте YouTube API ключ в настройках профиля",
            status_code=303
        )
    
    channel_info = await get_youtube_channel_info(youtube_url, user_api_key)
    if "error" in channel_info:
        return RedirectResponse(url=f"/my_channels?error={channel_info['error']}", status_code=303)
    
    try:
        target_list = json.loads(target_channels) if target_channels else []
    except json.JSONDecodeError:
        return RedirectResponse(url="/my_channels?error=Неверный список целевых каналов", status_code=303)
    
    if not target_list:
        user_channels = channel_repo.get_user_channels(user["id"])
        target_list = [
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

    if not target_list:
        return RedirectResponse(
            url="/my_channels?error=Р”РѕР±Р°РІСЊС‚Рµ С…РѕС‚СЏ Р±С‹ РѕРґРёРЅ Telegram РєР°РЅР°Р» РґР»СЏ YouTube-СѓРІРµРґРѕРјР»РµРЅРёР№",
            status_code=303
        )

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
    current_targets = current_channel.get('target_channels', [])
    current_button_url = current_channel.get('button_url')
    current_button_style = current_channel.get('button_style', 'success')
    
    success = youtube_repo.update_channel(
        channel_id, 
        user["id"], 
        current_targets,  # оставляем существующие целевые каналы
        post_template, 
        include_description,
        current_button_url,
        current_button_style
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
    
    user_api_key = resolve_youtube_api_key(user["id"])

    info = await get_youtube_channel_info(url, user_api_key)
    return JSONResponse(info)


@router.get("/api/youtube/channel-analytics/{channel_id}")
async def api_youtube_channel_analytics(request: Request, channel_id: int, days: int = 30):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    channel = youtube_repo.get_channel_by_id(channel_id, user["id"])
    if not channel:
        return JSONResponse({"error": "Channel not found"}, status_code=404)

    user_api_key = resolve_youtube_api_key(user["id"])
    if not user_api_key:
        return JSONResponse({"error": "YouTube API key is not configured"}, status_code=400)

    current_info = await get_youtube_channel_info(channel["youtube_channel_id"], user_api_key)
    if "error" in current_info:
        return JSONResponse(current_info, status_code=400)

    if not youtube_repo.has_recent_analytics_snapshot(channel_id, minutes=60):
        youtube_repo.add_analytics_snapshot(
            user_id=user["id"],
            youtube_channel_db_id=channel_id,
            youtube_channel_id=channel["youtube_channel_id"],
            subscriber_count=int(current_info.get("subscriber_count", 0)),
            view_count=int(current_info.get("view_count", 0)),
            video_count=int(current_info.get("video_count", 0)),
        )

    history = youtube_repo.get_analytics_history(channel_id, user["id"], days=max(1, min(days, 365)))

    labels = []
    subscribers = []
    views = []
    videos = []

    for point in history:
        recorded_at = point.get("recorded_at")
        try:
            dt = datetime.fromisoformat(recorded_at)
            labels.append(dt.strftime("%d.%m"))
        except Exception:
            labels.append(recorded_at or "")
        subscribers.append(int(point.get("subscriber_count") or 0))
        views.append(int(point.get("view_count") or 0))
        videos.append(int(point.get("video_count") or 0))

    first_point = history[0] if history else None
    current_subscribers = int(current_info.get("subscriber_count", 0) or 0)
    current_views = int(current_info.get("view_count", 0) or 0)
    current_videos = int(current_info.get("video_count", 0) or 0)

    delta = {
        "subscribers": current_subscribers - int(first_point.get("subscriber_count", 0) or 0) if first_point else 0,
        "views": current_views - int(first_point.get("view_count", 0) or 0) if first_point else 0,
        "videos": current_videos - int(first_point.get("video_count", 0) or 0) if first_point else 0,
    }

    return JSONResponse(
        {
            "channel": {
                "id": channel["id"],
                "name": channel["youtube_channel_name"],
                "youtube_channel_id": channel["youtube_channel_id"],
                "url": channel.get("youtube_channel_url"),
            },
            "period_days": days,
            "current": {
                "subscribers": current_subscribers,
                "views": current_views,
                "videos": current_videos,
            },
            "delta": delta,
            "series": {
                "labels": labels,
                "subscribers": subscribers,
                "views": views,
                "videos": videos,
            },
        }
    )
