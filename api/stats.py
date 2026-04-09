"""
Маршруты для статистики и всех записей
"""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.post_stats_repo import post_stats_repo
from repositories.channel_repo import channel_repo

router = APIRouter(tags=["stats"])
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


@router.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    """Страница со всеми записями пользователя"""
    user = get_current_user(request)
    
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Получаем все посты пользователя
    all_posts = post_stats_repo.get_user_posts(user["id"], limit=500)
    
    # Получаем статистику
    stats = post_stats_repo.get_user_stats(user["id"])
    
    # Получаем каналы пользователя для фильтрации
    channels = channel_repo.get_user_channels(user["id"])
    
    # Преобразуем stats в безопасный формат
    if isinstance(stats, dict):
        stats_list = [
            stats.get("total", 0),
            stats.get("success", 0),
            stats.get("failed", stats.get("error", 0))
        ]
    elif isinstance(stats, (list, tuple)):
        stats_list = list(stats) if len(stats) >= 3 else [0, 0, 0]
    else:
        stats_list = [0, 0, 0]
    
    return templates.TemplateResponse("stats.html", {
        "request": request,
        "user": user,
        "posts": all_posts,
        "stats": stats_list,
        "channels": channels,
        "project_name": user.get("project_name")
    })


@router.get("/api/stats")
async def api_stats(request: Request):
    """API для получения статистики"""
    user = get_current_user(request)
    
    if not user:
        return {"error": "Unauthorized"}
    
    stats = post_stats_repo.get_user_stats(user["id"])
    
    if isinstance(stats, dict):
        return {
            "total": stats.get("total", 0),
            "success": stats.get("success", 0),
            "failed": stats.get("failed", stats.get("error", 0))
        }
    elif isinstance(stats, (list, tuple)):
        return {
            "total": stats[0] if len(stats) > 0 else 0,
            "success": stats[1] if len(stats) > 1 else 0,
            "failed": stats[2] if len(stats) > 2 else 0
        }
    
    return {"total": 0, "success": 0, "failed": 0}
