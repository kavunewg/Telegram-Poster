"""
Маршруты для работы с VK
"""
import json
import tempfile
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.vk_repo import vk_repo
from services.vk_service import VKService, VKAPIError
from services.media_service import save_media_file

router = APIRouter(tags=["vk"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        session_id = request.cookies.get("session_id")
        if session_id:
            user = user_repo.get_by_session(session_id)
    return user


@router.get("/vk_channels", response_class=HTMLResponse)
async def vk_channels_page(request: Request):
    """Страница управления VK каналами"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    channels = vk_repo.get_user_channels(user["id"])
    
    return templates.TemplateResponse("vk_channels.html", {
        "request": request,
        "user": user,
        "channels": channels,
        "project_name": user.get("project_name")
    })


@router.post("/add_vk_channel")
async def add_vk_channel(
    request: Request,
    group_id: int = Form(...),
    access_token: str = Form(...)
):
    """Добавление VK канала"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        # Проверяем токен и получаем информацию о группе
        vk = VKService(access_token)
        group_info = await vk.get_group_info(group_id)
        
        if not group_info:
            return RedirectResponse(url="/vk_channels?error=Группа не найдена", status_code=303)
        
        group_name = group_info.get("name", f"Группа {group_id}")
        group_screen_name = group_info.get("screen_name", "")
        
        # Сохраняем канал
        vk_repo.add_channel(
            user["id"],
            group_id,
            group_name,
            group_screen_name,
            access_token
        )
        
        return RedirectResponse(url="/vk_channels?success=Канал добавлен", status_code=303)
        
    except VKAPIError as e:
        return RedirectResponse(url=f"/vk_channels?error=VK API Error: {e.error_msg}", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/vk_channels?error={str(e)}", status_code=303)


@router.post("/delete_vk_channel/{channel_id}")
async def delete_vk_channel(request: Request, channel_id: int):
    """Удаление VK канала"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    vk_repo.delete_channel(channel_id, user["id"])
    return RedirectResponse(url="/vk_channels?success=Канал удален", status_code=303)


@router.post("/toggle_vk_channel/{channel_id}")
async def toggle_vk_channel(request: Request, channel_id: int, is_active: int = Form(...)):
    """Включение/выключение канала"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    vk_repo.toggle_active(channel_id, user["id"], bool(is_active))
    return RedirectResponse(url="/vk_channels?success=Статус обновлен", status_code=303)


@router.post("/create_vk_post")
async def create_vk_post(
    request: Request,
    channel_id: int = Form(...),
    post_text: str = Form(...),
    media_file: UploadFile = File(None),
    publish_now: bool = Form(True)
):
    """Создание VK поста"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Сохраняем медиа если есть
    media_path = None
    if media_file and media_file.filename:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            while chunk := await media_file.read(1024 * 1024):
                tmp.write(chunk)
            tmp_path = tmp.name
        
        with open(tmp_path, "rb") as f:
            file_bytes = f.read()
        
        file_info = save_media_file(user["id"], file_bytes, media_file.filename, "vk")
        media_path = file_info.get('path')
    
    # Добавляем пост в очередь
    vk_repo.add_post(user["id"], channel_id, post_text, media_path)
    
    return RedirectResponse(url="/vk_posts?success=Пост добавлен в очередь", status_code=303)


@router.get("/vk_posts", response_class=HTMLResponse)
async def vk_posts_page(request: Request):
    """Страница VK постов"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # TODO: Получить список постов пользователя
    
    return templates.TemplateResponse("vk_posts.html", {
        "request": request,
        "user": user,
        "project_name": user.get("project_name")
    })