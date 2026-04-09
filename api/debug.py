"""
Отладочные маршруты
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.channel_repo import channel_repo
from repositories.bot_repo import bot_repo
from repositories.post_stats_repo import post_stats_repo
from repositories.youtube_repo import youtube_repo
from services.youtube_service import get_latest_video, format_youtube_post
from services.post_service import send_to_telegram
from core.config import POST_SESSIONS, TELEGRAM_TOKEN
import uuid
import json

from fastapi import APIRouter

router = APIRouter()

router = APIRouter(tags=["debug"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


@router.get("/debug", response_class=HTMLResponse)
async def debug_page(request: Request):
    """Главная страница отладки"""
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        session_id = request.cookies.get("session_id")
        user = user_repo.get_by_session(session_id)
    
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Получаем YouTube каналы пользователя
    youtube_channels = youtube_repo.get_user_channels(user["id"])
    
    return templates.TemplateResponse("debug.html", {
        "request": request,
        "user": user,
        "youtube_channels": youtube_channels
    })


@router.get("/debug/channels")
async def debug_channels(request: Request):
    """Получение списка каналов"""
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        session_id = request.cookies.get("session_id")
        user = user_repo.get_by_session(session_id)
    
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    channels = channel_repo.get_user_channels(user["id"])
    return JSONResponse({
        "count": len(channels),
        "channels": [
    {
            "id": ch.get("id"),
            "name": ch.get("channel_name"),
            "platform": ch.get("platform")
    }
    for ch in channels
]
    })


@router.get("/debug/bots")
async def debug_bots(request: Request):
    """Получение списка ботов"""
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        session_id = request.cookies.get("session_id")
        user = user_repo.get_by_session(session_id)
    
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    bots = bot_repo.get_user_bots(user["id"])
    return JSONResponse({
        "count": len(bots),
        "bots": bots
    })


@router.post("/debug/test_send")
async def debug_test_send(request: Request):
    """Тестовая отправка сообщения"""
    data = await request.json()
    channel_id = data.get("channel_id")
    bot_token = data.get("bot_token")
    message = data.get("message", "Test message")
    
    if not channel_id or not bot_token:
        return JSONResponse({"error": "channel_id and bot_token required"}, status_code=400)
    
    try:
        from services.post_service import send_to_telegram
        
        test_session = {
            "user_id": 1,
            "channel_db_id": 0,
            "channel_id": channel_id,
            "channel_name": "Test Channel",
            "platform": "telegram",
            "post_text": message,
            "media_path": None,
            "media_name": None,
            "media_size": None,
            "media_type": "text",
            "button": None,
            "bot_token": bot_token
        }
        
        result = await send_to_telegram(test_session, "test_session")
        
        return JSONResponse({
            "success": True,
            "message": "Message sent successfully",
            "result": result
        })
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)


@router.get("/debug/post_session/{session_id}")
async def debug_post_session(request: Request, session_id: str):
    """Просмотр сессии поста"""
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        session_cookie = request.cookies.get("session_id")
        user = user_repo.get_by_session(session_cookie)
    
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    if session_id not in POST_SESSIONS:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    session = POST_SESSIONS[session_id]
    return JSONResponse({
        "user_id": session.get("user_id"),
        "channels_count": len(session.get("channels", [])),
        "post_text_preview": session.get("post_text", "")[:100],
        "has_media": bool(session.get("media_path")),
        "has_button": bool(session.get("button")),
        "publishing": session.get("publishing", False),
        "progress": session.get("progress", 0),
        "completed_count": session.get("completed_count", 0),
        "results": session.get("results")
    })


# ========== НОВЫЕ МАРШРУТЫ ДЛЯ YOUTUBE DEBUG ==========

@router.get("/debug/youtube_channels")
async def debug_youtube_channels(request: Request):
    """Получение списка YouTube каналов пользователя"""
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        session_id = request.cookies.get("session_id")
        user = user_repo.get_by_session(session_id)
    
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    channels = youtube_repo.get_user_channels(user["id"])
    return JSONResponse({
        "count": len(channels),
        "channels": channels
    })


@router.post("/debug/force_youtube_notification")
async def debug_force_youtube_notification(
    request: Request,
    youtube_channel_id: int = Form(...)
):
    """Принудительная отправка уведомления о последнем видео с YouTube канала"""
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        session_id = request.cookies.get("session_id")
        user = user_repo.get_by_session(session_id)
    
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Получаем YouTube канал из БД
    channel = youtube_repo.get_channel_by_id(youtube_channel_id, user["id"])
    
    if not channel:
        return JSONResponse({"error": "YouTube канал не найден"}, status_code=404)
    
    # Получаем API ключ пользователя
    user_data = user_repo.get_by_id(user["id"])
    user_api_key = user_data[10] if len(user_data) > 10 else None
    
    if not user_api_key:
        return JSONResponse({"error": "YouTube API ключ не настроен"}, status_code=400)
    
    # Парсим данные канала
    youtube_channel_id_api = channel[1]
    youtube_channel_name = channel[2]
    target_channels = json.loads(channel[4]) if channel[4] else []
    post_template = channel[5]
    include_description = bool(channel[6])
    button_url = channel[11] if len(channel) > 11 else None
    button_style = channel[12] if len(channel) > 12 else 'success'
    
    # Получаем последнее видео
    video_info = await get_latest_video(youtube_channel_id_api, user_api_key)
    
    if not video_info:
        return JSONResponse({"error": "Не удалось получить видео с канала"}, status_code=404)
    
    # Форматируем пост
    post_text, button = format_youtube_post(
        video_info,
        youtube_channel_name,
        post_template,
        include_description,
        button_url,
        button_style
    )
    
    # Отправляем уведомления во все целевые каналы
    results = []
    success_count = 0
    failed_count = 0
    
    for target in target_channels:
        try:
            # Получаем токен бота для канала
            target_channel_id = target.get('id')
            
            # Ищем бота для этого канала
            with bot_repo._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT b.token FROM user_channels uc
                    JOIN bot_channels bc ON bc.channel_id = uc.id
                    JOIN user_bots b ON bc.bot_id = b.id
                    WHERE uc.id = ?
                ''', (target_channel_id,))
                bot_row = cursor.fetchone()
                bot_token = bot_row[0] if bot_row else TELEGRAM_TOKEN
            
            channel_session = {
                "user_id": user["id"],
                "channel_db_id": target_channel_id,
                "channel_id": target.get('channel_id'),
                "channel_name": target.get('name'),
                "platform": "telegram",
                "post_text": post_text,
                "media_path": None,
                "media_name": None,
                "media_size": None,
                "media_type": "text",
                "button": button,
                "bot_token": bot_token
            }
            
            temp_session_id = str(uuid.uuid4())
            await send_to_telegram(channel_session, temp_session_id)
            
            results.append({
                "channel": target.get('name'),
                "status": "success",
                "video_id": video_info['id'],
                "video_title": video_info['title'][:100]
            })
            success_count += 1
            
        except Exception as e:
            results.append({
                "channel": target.get('name'),
                "status": "error",
                "error": str(e)
            })
            failed_count += 1
    
    return JSONResponse({
        "success": True,
        "message": f"Уведомление отправлено. Успешно: {success_count}, Ошибок: {failed_count}",
        "video_info": {
            "id": video_info['id'],
            "title": video_info['title'],
            "url": video_info['url'],
            "published_at": video_info.get('published_at'),
            "views": video_info.get('views', 0)
        },
        "results": results,
        "success_count": success_count,
        "failed_count": failed_count
    })


@router.get("/debug/test_youtube_post")
async def debug_test_youtube_post(request: Request):
    """Тестовая отправка уведомления (без сохранения в БД)"""
    user = request.state.user if hasattr(request.state, 'user') else None
    if not user:
        session_id = request.cookies.get("session_id")
        user = user_repo.get_by_session(session_id)
    
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Получаем YouTube каналы пользователя
    youtube_channels = youtube_repo.get_user_channels(user["id"])
    
    if not youtube_channels:
        return JSONResponse({"error": "Нет добавленных YouTube каналов"}, status_code=404)
    
    # Берём первый канал
    yt_channel = youtube_channels[0]
    
    # Получаем API ключ пользователя
    user_data = user_repo.get_by_id(user["id"])
    user_api_key = user_data[10] if len(user_data) > 10 else None
    
    if not user_api_key:
        return JSONResponse({"error": "YouTube API ключ не настроен"}, status_code=400)
    
    # Получаем последнее видео
    video_info = await get_latest_video(yt_channel['youtube_channel_id'], user_api_key)
    
    if not video_info:
        return JSONResponse({"error": "Не удалось получить видео с канала"}, status_code=404)
    
    # Форматируем пост для предпросмотра
    post_text, button = format_youtube_post(
        video_info,
        yt_channel['youtube_channel_name'],
        yt_channel.get('post_template'),
        yt_channel.get('include_description', False),
        yt_channel.get('button_url'),
        yt_channel.get('button_style', 'success')
    )
    
    return JSONResponse({
        "video_info": {
            "id": video_info['id'],
            "title": video_info['title'],
            "url": video_info['url'],
            "description_preview": video_info.get('description', '')[:200],
            "published_at": video_info.get('published_at'),
            "views": video_info.get('views', 0)
        },
        "post_preview": {
            "text": post_text[:500],
            "button": button
        },
        "youtube_channel": {
            "id": yt_channel['id'],
            "name": yt_channel['youtube_channel_name'],
            "target_channels": yt_channel.get('target_channels', [])
        }
    })

from fastapi import Request

@router.get("/debug/me")
async def debug_me(request: Request):
    return {
        "session": dict(request.session)
    }