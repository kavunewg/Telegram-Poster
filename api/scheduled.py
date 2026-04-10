"""
Scheduled posts routes (чистая версия)
"""

import json
from datetime import datetime

from fastapi import APIRouter, Request, Form, File, UploadFile
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.channel_repo import channel_repo
from repositories.schedule_repo import schedule_repo
from services.media_service import save_media_file, delete_media_file
from services.schedule_service import schedule_post

router = APIRouter(tags=["scheduled"])
templates: Jinja2Templates = None


def set_templates(t):
    global templates
    templates = t


def get_user(request: Request):
    user = getattr(request.state, "user", None)
    if user:
        return user

    session_id = request.cookies.get("session_id")
    return user_repo.get_by_session(session_id)


@router.get("/scheduled_posts", response_class=HTMLResponse)
async def scheduled_posts(request: Request):
    user = get_user(request)

    if not user:
        return RedirectResponse("/login", status_code=303)

    # Получаем ВСЕ посты пользователя
    all_posts = schedule_repo.get_user_scheduled_posts(user["id"])
    
    # Фильтруем: оставляем ТОЛЬКО посты со статусом 'pending'
    posts = [post for post in all_posts if post.get('status') == 'pending']
    
    # Статистика по ВСЕМ постам (для верхних карточек)
    stats = schedule_repo.get_stats(user["id"])

    return templates.TemplateResponse("scheduled_posts.html", {
        "request": request,
        "user": user,
        "scheduled_posts": posts,  # ← ТОЛЬКО PENDING
        "stats": stats,
        "pending_count": stats.get("pending", 0),
        "processing_count": stats.get("processing", 0),
        "success_count": stats.get("success", 0),
        "error_count": stats.get("error", 0),
        "project_name": user["project_name"]
    })