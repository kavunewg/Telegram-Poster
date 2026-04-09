"""
Debug routes for manual diagnostics.
"""
import json
import uuid

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.config import POST_SESSIONS, TELEGRAM_TOKEN
from core.database import get_db_connection
from repositories.bot_repo import bot_repo
from repositories.channel_repo import channel_repo
from repositories.post_stats_repo import post_stats_repo
from repositories.user_repo import user_repo
from repositories.youtube_repo import youtube_repo
from services.post_service import send_to_telegram
from services.youtube_service import format_youtube_post, get_latest_video

router = APIRouter(tags=["debug"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    return getattr(request.state, "user", None) or user_repo.get_by_session(request.cookies.get("session_id"))


@router.get("/debug", response_class=HTMLResponse)
async def debug_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "debug.html",
        {"request": request, "user": user, "youtube_channels": youtube_repo.get_user_channels(user["id"])},
    )


@router.get("/debug/channels")
async def debug_channels(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    channels = channel_repo.get_user_channels(user["id"])
    return JSONResponse(
        {
            "count": len(channels),
            "channels": [
                {"id": ch.get("id"), "name": ch.get("channel_name"), "platform": ch.get("platform")}
                for ch in channels
            ],
        }
    )


@router.get("/debug/bots")
async def debug_bots(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    bots = bot_repo.get_user_bots(user["id"])
    return JSONResponse({"count": len(bots), "bots": bots})


@router.post("/debug/test_send")
async def debug_test_send(request: Request):
    data = await request.json()
    channel_id = data.get("channel_id")
    bot_token = data.get("bot_token")
    message = data.get("message", "Test message")

    if not channel_id or not bot_token:
        return JSONResponse({"error": "channel_id and bot_token required"}, status_code=400)

    try:
        result = await send_to_telegram(
            {
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
                "bot_token": bot_token,
            },
            "test_session",
        )
        return JSONResponse({"success": True, "message": "Message sent successfully", "result": result})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@router.get("/debug/post_session/{session_id}")
async def debug_post_session(request: Request, session_id: str):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    if session_id not in POST_SESSIONS:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    session = POST_SESSIONS[session_id]
    return JSONResponse(
        {
            "user_id": session.get("user_id"),
            "channels_count": len(session.get("channels", [])),
            "post_text_preview": session.get("post_text", "")[:100],
            "has_media": bool(session.get("media_path")),
            "has_button": bool(session.get("button")),
            "publishing": session.get("publishing", False),
            "progress": session.get("progress", 0),
            "completed_count": session.get("completed_count", 0),
            "results": session.get("results"),
        }
    )


@router.get("/debug/youtube_channels")
async def debug_youtube_channels(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    channels = youtube_repo.get_user_channels(user["id"])
    return JSONResponse({"count": len(channels), "channels": channels})


@router.post("/debug/force_youtube_notification")
async def debug_force_youtube_notification(request: Request, youtube_channel_id: int = Form(...)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    channel = youtube_repo.get_channel_by_id(youtube_channel_id, user["id"])
    if not channel:
        return JSONResponse({"error": "YouTube канал не найден"}, status_code=404)

    user_data = user_repo.get_by_id(user["id"])
    user_api_key = user_data.get("youtube_api_key") if user_data else None
    if not user_api_key:
        return JSONResponse({"error": "YouTube API ключ не настроен"}, status_code=400)

    video_info = await get_latest_video(channel["youtube_channel_id"], user_api_key)
    if not video_info:
        return JSONResponse({"error": "Не удалось получить видео с канала"}, status_code=404)

    post_text, button = format_youtube_post(
        video_info,
        channel["youtube_channel_name"],
        channel.get("post_template"),
        channel.get("include_description", False),
        channel.get("button_url"),
        channel.get("button_style", "success"),
    )

    results = []
    success_count = 0
    failed_count = 0

    for target in channel.get("target_channels", []):
        try:
            target_channel_id = target.get("id")
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT b.token FROM user_channels uc
                    JOIN bot_channels bc ON bc.channel_id = uc.id
                    JOIN user_bots b ON bc.bot_id = b.id
                    WHERE uc.id = ?
                    """,
                    (target_channel_id,),
                )
                bot_row = cursor.fetchone()
                bot_token = bot_row[0] if bot_row else TELEGRAM_TOKEN

            await send_to_telegram(
                {
                    "user_id": user["id"],
                    "channel_db_id": target_channel_id,
                    "channel_id": target.get("channel_id"),
                    "channel_name": target.get("name"),
                    "platform": "telegram",
                    "post_text": post_text,
                    "media_path": None,
                    "media_name": None,
                    "media_size": None,
                    "media_type": "text",
                    "button": button,
                    "bot_token": bot_token,
                },
                str(uuid.uuid4()),
            )

            results.append({"channel": target.get("name"), "status": "success"})
            success_count += 1
        except Exception as exc:
            results.append({"channel": target.get("name"), "status": "error", "error": str(exc)})
            failed_count += 1

    return JSONResponse(
        {
            "success": True,
            "message": f"Успешно: {success_count}, Ошибок: {failed_count}",
            "video_info": {
                "id": video_info["id"],
                "title": video_info["title"],
                "url": video_info["url"],
                "published_at": video_info.get("published_at"),
                "views": video_info.get("views", 0),
            },
            "results": results,
            "success_count": success_count,
            "failed_count": failed_count,
        }
    )


@router.get("/debug/test_youtube_post")
async def debug_test_youtube_post(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    youtube_channels = youtube_repo.get_user_channels(user["id"])
    if not youtube_channels:
        return JSONResponse({"error": "Нет добавленных YouTube каналов"}, status_code=404)

    yt_channel = youtube_channels[0]
    user_data = user_repo.get_by_id(user["id"])
    user_api_key = user_data.get("youtube_api_key") if user_data else None
    if not user_api_key:
        return JSONResponse({"error": "YouTube API ключ не настроен"}, status_code=400)

    video_info = await get_latest_video(yt_channel["youtube_channel_id"], user_api_key)
    if not video_info:
        return JSONResponse({"error": "Не удалось получить видео с канала"}, status_code=404)

    post_text, button = format_youtube_post(
        video_info,
        yt_channel["youtube_channel_name"],
        yt_channel.get("post_template"),
        yt_channel.get("include_description", False),
        yt_channel.get("button_url"),
        yt_channel.get("button_style", "success"),
    )

    return JSONResponse(
        {
            "video_info": {
                "id": video_info["id"],
                "title": video_info["title"],
                "url": video_info["url"],
                "description_preview": video_info.get("description", "")[:200],
                "published_at": video_info.get("published_at"),
                "views": video_info.get("views", 0),
            },
            "post_preview": {"text": post_text[:500], "button": button},
            "youtube_channel": {
                "id": yt_channel["id"],
                "name": yt_channel["youtube_channel_name"],
                "target_channels": yt_channel.get("target_channels", []),
            },
        }
    )


@router.get("/debug/me")
async def debug_me(request: Request):
    user = getattr(request.state, "user", None)
    return {
        "authenticated": bool(user),
        "user": user,
        "cookies": {"session_id": request.cookies.get("session_id")},
    }
