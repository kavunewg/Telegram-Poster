"""
Панель управления - УПРОЩЁННАЯ ВЕРСИЯ
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta

from repositories.channel_repo import channel_repo
from repositories.user_repo import user_repo
from repositories.bot_repo import bot_repo
from repositories.post_stats_repo import post_stats_repo
from core.database import get_db_connection
from utils.helpers import clean_email
from utils.validators import validate_password

router = APIRouter(tags=["dashboard"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    """Получение текущего пользователя"""
    user = getattr(request.state, "user", None)
    if not user:
        session_id = request.cookies.get("session_id")
        if session_id:
            user = user_repo.get_by_session(session_id)
    return user


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Главная панель управления"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Админ панель
    if user.get("is_admin") == 1:
        return await admin_dashboard(request, user)
    
    # Пользовательская панель
    return await user_dashboard(request, user)


async def admin_dashboard(request: Request, user: dict):
    """Админ панель"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        
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
        
        # Последние посты
        cursor.execute("""
            SELECT ps.id, ps.user_id, ps.post_text, ps.status, ps.sent_at,
                   u.username, COALESCE(uc.channel_name, 'Unknown')
            FROM posts_stats ps
            LEFT JOIN users u ON ps.user_id = u.id
            LEFT JOIN user_channels uc ON ps.channel_id = uc.id
            ORDER BY ps.sent_at DESC
            LIMIT 100
        """)
        recent_posts = cursor.fetchall()
        
        users = user_repo.get_all_users()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": user,
        "users": users,
        "total_users": total_users,
        "total_channels": total_channels,
        "total_posts": total_posts,
        "total_success": total_success,
        "registrations_today": registrations_today,
        "recent_posts": recent_posts
    })


async def user_dashboard(request: Request, user: dict):
    """Пользовательская панель"""
    channels = channel_repo.get_user_channels(user["id"])
    bots = bot_repo.get_user_bots(user["id"])
    stats = post_stats_repo.get_user_stats(user["id"])
    recent_posts = post_stats_repo.get_user_posts(user["id"], 10)
    
    # Преобразуем stats в безопасный формат
    if isinstance(stats, dict):
        stats_list = [
            stats.get("total", 0),
            stats.get("success", 0),
            stats.get("failed", 0)
        ]
    elif isinstance(stats, (list, tuple)):
        stats_list = list(stats) if len(stats) >= 3 else [0, 0, 0]
    else:
        stats_list = [0, 0, 0]
    
    telegram_channels = [ch for ch in channels if ch.get("platform") == "telegram"]
    max_channels = [ch for ch in channels if ch.get("platform") == "max"]
    
    return templates.TemplateResponse("user_dashboard.html", {
        "request": request,
        "user": user,
        "channels": channels,
        "telegram_channels": telegram_channels,
        "max_channels": max_channels,
        "telegram_count": len(telegram_channels),
        "max_count": len(max_channels),
        "stats": stats_list,
        "recent_posts": recent_posts,
        "project_name": user.get("project_name"),
        "bots": bots
    })


# ==================== ПРОФИЛЬ (встроен в dashboard) ====================

@router.post("/update_profile")
async def update_profile(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    email: str = Form(""),
    youtube_api_key: str = Form(None)
):
    """Обновление профиля"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    email = clean_email(email) if email else None
    
    # Проверка уникальности username
    existing = user_repo.get_by_username(username)
    if existing and existing["id"] != user["id"]:
        return RedirectResponse(url="/dashboard?error=Логин уже занят", status_code=303)
    
    # Проверка уникальности email
    if email:
        existing_email = user_repo.get_by_email(email)
        if existing_email and existing_email["id"] != user["id"]:
            return RedirectResponse(url="/dashboard?error=Email уже используется", status_code=303)
    
    success = user_repo.update_profile(
        user["id"], username, full_name, email, youtube_api_key
    )
    
    if success:
        return RedirectResponse(url="/dashboard?success=Профиль обновлён", status_code=303)
    return RedirectResponse(url="/dashboard?error=Ошибка обновления профиля", status_code=303)


@router.post("/delete_account")
async def delete_account(request: Request):
    """Удаление аккаунта"""
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


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)

    channels = channel_repo.get_user_channels(user["id"])

    platforms = [
        {"key": "telegram", "name": "Telegram", "icon": "📡", "count": 3, "active": 2},
        {"key": "max", "name": "MAX", "icon": "🏢", "count": 1, "active": 1},
        {"key": "vk", "name": "VK", "icon": "📘", "count": 2, "active": 1},
        {"key": "youtube", "name": "YouTube", "icon": "🎬", "count": 1, "active": 1},
    ]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "channels": channels[:5],
        "platforms": platforms
    })