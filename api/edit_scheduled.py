"""
Маршруты для редактирования отложенных постов
"""
import json
import tempfile
from datetime import datetime
from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.schedule_repo import schedule_repo
from repositories.bot_repo import bot_repo
from repositories.channel_repo import channel_repo
from services.media_service import save_media_file, delete_media_file

router = APIRouter(tags=["edit_scheduled"])
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


@router.get("/edit_scheduled_post/{post_id}", response_class=HTMLResponse)
async def edit_scheduled_post_page(request: Request, post_id: int):
    """Страница редактирования отложенного поста"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Получаем пост
    post = schedule_repo.get_post_by_id(post_id, user["id"])
    if not post:
        return RedirectResponse(url="/scheduled_posts?error=Пост не найден", status_code=303)
    
    # Получаем каналы пользователя
    channels = channel_repo.get_user_channels(user["id"])
    bots = bot_repo.get_user_bots(user["id"])
    
    # Парсим каналы из поста
    post_channels = []
    if post.get("channels"):
        try:
            post_channels = json.loads(post["channels"]) if isinstance(post["channels"], str) else post["channels"]
        except:
            post_channels = []
    
    # Парсим кнопку
    button = None
    if post.get("button"):
        try:
            button = json.loads(post["button"]) if isinstance(post["button"], str) else post["button"]
        except:
            button = None
    
    # Парсим regular_settings
    regular_settings = {}
    if post.get("regular_settings"):
        try:
            regular_settings = json.loads(post["regular_settings"]) if isinstance(post["regular_settings"], str) else post["regular_settings"]
        except:
            regular_settings = {}
    
    return templates.TemplateResponse("edit_scheduled_post.html", {
        "request": request,
        "user": user,
        "post": post,
        "post_channels": post_channels,
        "channels": channels,
        "bots": bots,
        "button": button,
        "regular_settings": regular_settings,
        "is_regular": post.get("is_regular", 0),
        "project_name": user.get("project_name")
    })


@router.post("/update_scheduled_post/{post_id}")
async def update_scheduled_post(
    request: Request,
    post_id: int,
    channels_data: str = Form(...),
    post_text: str = Form(...),
    scheduled_date: str = Form(...),
    scheduled_time: str = Form(...),
    button_text: str = Form(None),
    button_url: str = Form(None),
    button_style: str = Form('success'),
    button_data: str = Form(None),
    media_file: UploadFile = File(None),
    delete_media: str = Form('0'),
    is_regular: str = Form('0'),
    regular_interval: int = Form(None),
    regular_end_date: str = Form(None),
    regular_end_time: str = Form(None)
):
    """Обновление отложенного поста"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        # Получаем существующий пост
        existing_post = schedule_repo.get_post_by_id(post_id, user["id"])
        if not existing_post:
            return RedirectResponse(url="/scheduled_posts?error=Пост не найден", status_code=303)
        
        # Парсим каналы
        try:
            channels = json.loads(channels_data)
        except:
            channels = []
        
        # Формируем кнопку
        button = None
        if button_data and button_data not in ['null', 'undefined', '']:
            try:
                button = json.loads(button_data)
            except:
                button = None
        
        if not button and button_text and button_url:
            url = button_url if button_url.startswith(('http://', 'https://')) else f"https://{button_url}"
            button = {
                "text": button_text,
                "url": url,
                "style": button_style
            }
        
        # Формируем дату и время
        import pytz
        scheduled_datetime = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
        scheduled_datetime = pytz.timezone('Europe/Moscow').localize(scheduled_datetime)
        scheduled_time_iso = scheduled_datetime.isoformat()
        
        # Обработка медиафайла
        media_path = existing_post.get("media_path")
        media_name = existing_post.get("media_name")
        media_size = existing_post.get("media_size")
        media_type = existing_post.get("media_type")
        
        # Удаление медиа
        if delete_media == '1' and media_path:
            delete_media_file(media_path)
            media_path = None
            media_name = None
            media_size = None
            media_type = None
        
        # Загрузка нового медиа
        if media_file and media_file.filename:
            # Удаляем старый файл
            if media_path:
                delete_media_file(media_path)
            
            # Сохраняем новый
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                while chunk := await media_file.read(1024 * 1024):
                    tmp.write(chunk)
                tmp_path = tmp.name
            
            with open(tmp_path, "rb") as f:
                file_bytes = f.read()
            
            file_info = save_media_file(user["id"], file_bytes, media_file.filename, "instant")
            media_path = file_info.get('path')
            media_name = file_info.get('name')
            media_size = file_info.get('size')
            media_type = file_info.get('type')
        
        # Настройки регулярного поста
        is_regular_flag = is_regular == '1'
        regular_settings = None
        if is_regular_flag:
            regular_settings = {
                "interval_hours": regular_interval or 24,
                "start_time": scheduled_time_iso,
                "end_date": regular_end_date if regular_end_date else None,
                "end_time": regular_end_time if regular_end_time else None
            }
        
        # Обновляем пост
        success = schedule_repo.update_post(
            post_id,
            user["id"],
            channels,
            post_text,
            media_path,
            media_name,
            media_size,
            media_type,
            button,
            scheduled_time_iso,
            is_regular_flag,
            regular_settings
        )
        
        if success:
            # Обновляем планировщик
            from services.schedule_service import reschedule_post
            reschedule_post(post_id, scheduled_datetime)
            
            return RedirectResponse(url="/scheduled_posts?success=Пост успешно обновлён", status_code=303)
        else:
            return RedirectResponse(url=f"/edit_scheduled_post/{post_id}?error=Ошибка при обновлении", status_code=303)
    
    except Exception as e:
        return RedirectResponse(url=f"/edit_scheduled_post/{post_id}?error={str(e)}", status_code=303)


@router.post("/delete_scheduled_post/{post_id}")
async def delete_scheduled_post(request: Request, post_id: int):
    """Удаление отложенного поста"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    post = schedule_repo.get_post_by_id(post_id, user["id"])
    if not post:
        return RedirectResponse(url="/scheduled_posts?error=Пост не найден", status_code=303)
    
    # Удаляем медиафайл
    if post.get("media_path"):
        delete_media_file(post["media_path"])
    
    # Удаляем пост из БД
    schedule_repo.delete_post(post_id)
    
    # Удаляем из планировщика
    from services.schedule_service import cancel_scheduled_post
    cancel_scheduled_post(post_id)
    
    return RedirectResponse(url="/scheduled_posts?success=Пост удалён", status_code=303)