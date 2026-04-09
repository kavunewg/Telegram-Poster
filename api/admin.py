"""
Админские маршруты
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.channel_repo import channel_repo
from repositories.post_stats_repo import post_stats_repo
from utils.validators import validate_password

router = APIRouter(tags=["admin"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


@router.get("/admin/user/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(request: Request, user_id: int):
    admin_user = request.state.user if hasattr(request.state, 'user') else None
    if not admin_user:
        session_id = request.cookies.get("session_id")
        admin_user = user_repo.get_by_session(session_id)
    
    if not admin_user or admin_user["is_admin"] != 1:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    user = user_repo.get_by_id(user_id)
    if not user:
        return RedirectResponse(url="/dashboard?error=Пользователь не найден", status_code=303)
    
    stats = post_stats_repo.get_user_stats(user_id)
    channels = channel_repo.get_user_channels(user_id)
    posts = post_stats_repo.get_user_posts(user_id, 50)
    
    return templates.TemplateResponse("admin_user_detail.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "channels": channels,
        "posts": posts,
        "project_name": user["project_name"]
    })


@router.post("/admin/delete_user/{user_id}")
async def admin_delete_user(request: Request, user_id: int):
    admin_user = request.state.user if hasattr(request.state, 'user') else None
    if not admin_user:
        session_id = request.cookies.get("session_id")
        admin_user = user_repo.get_by_session(session_id)
    
    if not admin_user or admin_user["is_admin"] != 1:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    if admin_user["id"] == user_id:
        return RedirectResponse(url="/dashboard?error=Нельзя удалить самого себя", status_code=303)
    
    user_repo.delete_user(user_id)
    return RedirectResponse(url="/dashboard?success=Пользователь удален", status_code=303)


@router.post("/admin/reset_password")
async def admin_reset_password(
    request: Request,
    user_id: int = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    admin_user = request.state.user if hasattr(request.state, 'user') else None
    if not admin_user:
        session_id = request.cookies.get("session_id")
        admin_user = user_repo.get_by_session(session_id)
    
    if not admin_user or admin_user["is_admin"] != 1:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    if new_password != confirm_password:
        return RedirectResponse(url=f"/dashboard?error=Пароли не совпадают", status_code=303)
    
    is_valid, error_msg = validate_password(new_password)
    if not is_valid:
        return RedirectResponse(url=f"/dashboard?error={error_msg}", status_code=303)
    
    user_repo.update_password(user_id, new_password)
    return RedirectResponse(url=f"/dashboard?success=Пароль пользователя изменен", status_code=303)


@router.post("/admin/add_user")
async def admin_add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    project_name: str = Form(...)
):
    admin_user = request.state.user if hasattr(request.state, 'user') else None
    if not admin_user:
        session_id = request.cookies.get("session_id")
        admin_user = user_repo.get_by_session(session_id)
    
    if not admin_user or admin_user["is_admin"] != 1:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        return RedirectResponse(url=f"/dashboard?error={error_msg}", status_code=303)
    
    existing_user = user_repo.get_by_username(username)
    if existing_user:
        return RedirectResponse(url=f"/dashboard?error=Пользователь с таким логином уже существует", status_code=303)
    
    try:
        user_id = user_repo.create(
            username=username,
            password=password,
            full_name=full_name,
            project_name=project_name,
            created_by=admin_user["id"]
        )
    except ValueError as exc:
        return RedirectResponse(url=f"/dashboard?error={exc}", status_code=303)
    
    if user_id:
        return RedirectResponse(url=f"/dashboard?success=Пользователь {username} успешно добавлен", status_code=303)
    return RedirectResponse(url=f"/dashboard?error=Ошибка при создании пользователя", status_code=303)
