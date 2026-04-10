"""
Dashboard routes.
"""

from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.database import get_db_connection
from repositories.bot_repo import bot_repo
from repositories.channel_repo import channel_repo
from repositories.post_stats_repo import post_stats_repo
from repositories.youtube_repo import youtube_repo
from repositories.user_repo import user_repo
from utils.helpers import clean_email

try:
    from repositories.vk_repo import vk_repo
    VK_AVAILABLE = True
except ImportError:
    vk_repo = None
    VK_AVAILABLE = False

router = APIRouter(tags=["dashboard"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    return getattr(request.state, "user", None) or user_repo.get_by_session(request.cookies.get("session_id"))


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if user.get("is_admin") == 1:
        return await admin_dashboard(request, user)

    return await user_dashboard(request, user)


async def admin_dashboard(request: Request, user: dict):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM user_channels")
        total_channels = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM posts_stats")
        total_posts = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM posts_stats WHERE status = 'success'")
        total_success = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (today_start,))
        registrations_today = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT ps.id, ps.user_id, ps.post_text, ps.status, ps.sent_at,
                   u.username, COALESCE(uc.channel_name, 'Unknown')
            FROM posts_stats ps
            LEFT JOIN users u ON ps.user_id = u.id
            LEFT JOIN user_channels uc ON ps.channel_id = uc.id
            ORDER BY ps.sent_at DESC
            LIMIT 100
            """
        )
        recent_posts = cursor.fetchall()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_user": user,
            "users": user_repo.get_all_users(),
            "total_users": total_users,
            "total_channels": total_channels,
            "total_posts": total_posts,
            "total_success": total_success,
            "registrations_today": registrations_today,
            "recent_posts": recent_posts,
        },
    )


async def user_dashboard(request: Request, user: dict):
    channels = channel_repo.get_user_channels(user["id"])
    bots = bot_repo.get_user_bots(user["id"])
    stats = post_stats_repo.get_user_stats(user["id"])
    recent_posts = post_stats_repo.get_user_posts(user["id"], 10)

    if isinstance(stats, dict):
        stats_list = [stats.get("total", 0), stats.get("success", 0), stats.get("failed", 0)]
    elif isinstance(stats, (list, tuple)):
        stats_list = list(stats) if len(stats) >= 3 else [0, 0, 0]
    else:
        stats_list = [0, 0, 0]

    telegram_channels = [ch for ch in channels if ch.get("platform") == "telegram"]
    max_channels = [ch for ch in channels if ch.get("platform") == "max"]
    youtube_channels = youtube_repo.get_user_channels(user["id"])
    vk_channels = vk_repo.get_user_channels(user["id"]) if VK_AVAILABLE and vk_repo else []
    total_channels = len(telegram_channels) + len(max_channels) + len(youtube_channels) + len(vk_channels)

    return templates.TemplateResponse(
        "user_dashboard.html",
        {
            "request": request,
            "user": user,
            "channels": channels,
            "telegram_channels": telegram_channels,
            "max_channels": max_channels,
            "telegram_count": len(telegram_channels),
            "max_count": len(max_channels),
            "youtube_channels": youtube_channels,
            "youtube_count": len(youtube_channels),
            "vk_count": len(vk_channels),
            "total_channels": total_channels,
            "stats": stats_list,
            "recent_posts": recent_posts,
            "project_name": user.get("project_name"),
            "bots": bots,
        },
    )


@router.post("/update_profile")
async def update_profile(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(""),
    youtube_api_key: str = Form(None),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    email = clean_email(email) if email else None

    existing = user_repo.get_by_username(username)
    if existing and existing["id"] != user["id"]:
        return RedirectResponse(url="/dashboard?error=Р›РѕРіРёРЅ СѓР¶Рµ Р·Р°РЅСЏС‚", status_code=303)

    if email:
        existing_email = user_repo.get_by_email(email)
        if existing_email and existing_email["id"] != user["id"]:
            return RedirectResponse(url="/dashboard?error=Email СѓР¶Рµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ", status_code=303)

    success = user_repo.update_profile(
        user["id"],
        username=username,
        full_name=full_name,
        email=email,
        youtube_api_key=youtube_api_key,
    )
    if success:
        return RedirectResponse(url="/dashboard?success=РџСЂРѕС„РёР»СЊ РѕР±РЅРѕРІР»С‘РЅ", status_code=303)
    return RedirectResponse(url="/dashboard?error=РћС€РёР±РєР° РѕР±РЅРѕРІР»РµРЅРёСЏ РїСЂРѕС„РёР»СЏ", status_code=303)


@router.post("/delete_account")
async def delete_account(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_repo.delete_user(user["id"])
    session_id = request.cookies.get("session_id")
    if session_id:
        user_repo.delete_session(session_id)

    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_id")
    return response
