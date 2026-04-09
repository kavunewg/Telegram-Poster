"""
Маршруты для создания и публикации постов
"""
import json
import uuid
import tempfile
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import pytz

from repositories.user_repo import user_repo
from repositories.channel_repo import channel_repo
from repositories.bot_repo import bot_repo
from repositories.schedule_repo import schedule_repo
from repositories.queue_repo import queue_repo
from services.media_service import save_media_file, delete_media_file
from services.schedule_service import schedule_post
from core.config import POST_SESSIONS
from languages import get_lang

router = APIRouter(tags=["posts"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Получение текущего пользователя из сессии"""
    user = getattr(request.state, "user", None)
    if not user:
        session_id = request.cookies.get("session_id")
        if session_id:
            user = user_repo.get_by_session(session_id)
    return user


def validate_channels(channels: List[Dict]) -> tuple:
    """Валидация списка каналов"""
    if not channels:
        return False, "Выберите хотя бы один канал"
    
    for channel in channels:
        if not channel.get("channel_id"):
            return False, "У канала отсутствует ID"
        if channel.get("platform") == "telegram" and not channel.get("bot_token"):
            return False, f"Для канала {channel.get('name')} не указан бот"
    
    return True, "OK"


def parse_button_data(button_data: Optional[str]) -> Optional[Dict]:
    """Парсинг данных кнопки"""
    if not button_data or button_data in ['null', 'undefined', '']:
        return None
    
    try:
        button = json.loads(button_data)
        # Валидация кнопки
        if button.get("text") and button.get("url"):
            # Нормализуем URL
            url = button["url"]
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            button["url"] = url
            return button
    except json.JSONDecodeError:
        pass
    
    return None


def parse_button_from_form(
    button_text: Optional[str],
    button_url: Optional[str],
    button_style: str = 'success'
) -> Optional[Dict]:
    """Создание кнопки из полей формы"""
    if button_text and button_url:
        url = button_url if button_url.startswith(('http://', 'https://')) else f"https://{button_url}"
        return {
            "text": button_text,
            "url": url,
            "style": button_style
        }
    return None


async def save_uploaded_media(user_id: int, media_file: UploadFile) -> Optional[Dict]:
    """Сохранение загруженного медиафайла"""
    if not media_file or not media_file.filename:
        return None
    
    try:
        # Сохраняем во временный файл
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            while chunk := await media_file.read(1024 * 1024):
                tmp.write(chunk)
            tmp_path = tmp.name
        
        # Читаем и сохраняем через медиа сервис
        with open(tmp_path, "rb") as f:
            file_bytes = f.read()
        
        # Удаляем временный файл
        import os
        os.unlink(tmp_path)
        
        return save_media_file(user_id, file_bytes, media_file.filename, "instant")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка загрузки файла: {str(e)}")


def create_post_session(
    session_id: str,
    user_id: int,
    channels: List[Dict],
    post_text: str,
    media_info: Optional[Dict],
    button: Optional[Dict]
) -> None:
    """Создание сессии поста для отслеживания"""
    POST_SESSIONS[session_id] = {
        "user_id": user_id,
        "channels": channels,
        "post_text": post_text,
        "media_path": media_info.get('path') if media_info else None,
        "media_name": media_info.get('name') if media_info else None,
        "media_size": media_info.get('size') if media_info else None,
        "media_type": media_info.get('type') if media_info else None,
        "button": button,
        "publishing": True,
        "progress": 0,
        "completed_count": 0,
        "results": {"success": 0, "failed": 0},
        "created_at": datetime.now().isoformat()
    }


def add_tasks_to_queue(user_id: int, channels: List[Dict], post_text: str, media_info: Optional[Dict], button: Optional[Dict]) -> int:
    """Добавление задач в очередь"""
    tasks_count = 0
    
    for channel in channels:
        # Убеждаемся, что bot_token передан правильно
        bot_token = channel.get("bot_token")
        
        # Если bot_token нет в channel, пробуем получить из других мест
        if not bot_token:
            bot_token = channel.get("token")
        
        # Логируем для отладки
        print(f"DEBUG: Добавление задачи для канала {channel.get('name')}, bot_token: {bot_token[:20] if bot_token else 'None'}...")
        
        task_id = queue_repo.create_task(
            user_id=user_id,
            channel_id=channel.get("id"),
            platform=channel.get("platform", "telegram"),
            action="send_post",
            payload={
                "user_id": user_id,
                "text": post_text,
                "media_path": media_info.get('path') if media_info else None,
                "media_name": media_info.get('name') if media_info else None,
                "media_size": media_info.get('size') if media_info else None,
                "media_type": media_info.get('type') if media_info else None,
                "button": button,
                "channel": {
                    "id": channel.get("id"),
                    "name": channel.get("name"),
                    "channel_id": channel.get("channel_id"),
                    "platform": channel.get("platform"),
                    "bot_token": bot_token  # Явно передаём bot_token
                },
                "channel_db_id": channel.get("id"),
                "bot_token": bot_token  # Дублируем на верхний уровень для удобства
            }
        )
        tasks_count += 1
        print(f"DEBUG: Задача {task_id} создана")
    
    return tasks_count


# ==================== ОСНОВНЫЕ МАРШРУТЫ ====================

@router.get("/create_post", response_class=HTMLResponse)
async def create_post_page(request: Request):
    print("=" * 50)
    print("🔍 create_post_page вызван")
    
    user = get_current_user(request)
    print(f"Пользователь: {user}")
    
    if not user or user.get("is_admin") == 1:
        print("❌ Пользователь не авторизован или админ")
        return RedirectResponse(url="/dashboard", status_code=303)
    
    channels = channel_repo.get_user_channels(user["id"])
    print(f"Каналы: {len(channels) if channels else 0}")
    
    bots = bot_repo.get_user_bots(user["id"])
    print(f"Боты: {len(bots) if bots else 0}")
    
    # Преобразуем каналы в удобный формат
    formatted_channels = []
    for ch in channels:
        formatted_channels.append({
            "id": ch.get("id"),
            "channel_name": ch.get("channel_name"),
            "channel_id": ch.get("channel_id"),
            "channel_url": ch.get("channel_url"),
            "platform": ch.get("platform"),
            "bot_token": ch.get("bot_token"),
            "bot_name": ch.get("bot_name")
        })
    
    print("✅ Рендеринг шаблона create_post.html")
    
    return templates.TemplateResponse("create_post.html", {
        "request": request,
        "user": user,
        "channels": formatted_channels,
        "bots": bots,
        "project_name": user.get("project_name")
    })

@router.post("/publish_unified")
async def publish_unified(
    request: Request,
    channels_data: str = Form(...),
    post_text: str = Form(...),
    media_file: UploadFile = File(None),
    button_data: str = Form(None)
):
    """Мгновенная публикация поста"""
    user = get_current_user(request)
    
    if not user or user.get("is_admin") == 1:
        return RedirectResponse(url="/dashboard", status_code=303)
    
    # Парсим данные
    try:
        channels = json.loads(channels_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат данных каналов")
    
    # Валидация
    is_valid, error_msg = validate_channels(channels)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    if not post_text or not post_text.strip():
        raise HTTPException(status_code=400, detail="Введите текст поста")
    
    # Парсим кнопку
    button = parse_button_data(button_data)
    
    # Сохраняем медиафайл
    media_info = None
    if media_file and media_file.filename:
        try:
            media_info = await save_uploaded_media(user["id"], media_file)
        except HTTPException as e:
            # Возвращаем на страницу с ошибкой
            channels = channel_repo.get_user_channels(user["id"])
            bots = bot_repo.get_user_bots(user["id"])
            return templates.TemplateResponse("create_post.html", {
                "request": request,
                "get_lang": get_lang,
                "channels": channels,
                "bots": bots,
                "project_name": user.get("project_name"),
                "error": str(e.detail)
            })
    
    # Добавляем задачи в очередь
    tasks_count = add_tasks_to_queue(user["id"], channels, post_text, media_info, button)
    
    # Создаём сессию для отслеживания
    post_session_id = str(uuid.uuid4())
    create_post_session(post_session_id, user["id"], channels, post_text, media_info, button)
    
    # Возвращаем JSON для AJAX или редирект для обычной отправки
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse({
            "success": True,
            "session_id": post_session_id,
            "tasks_count": tasks_count,
            "message": f"Пост добавлен в очередь. Будет отправлен в {tasks_count} каналов."
        })
    
    response = RedirectResponse(url=f"/publish_unified/{post_session_id}", status_code=303)
    response.set_cookie(key="post_session_id", value=post_session_id)
    return response


@router.post("/schedule_post")
async def schedule_post_endpoint(
    request: Request,
    channels_data: str = Form(...),
    post_text: str = Form(...),
    scheduled_date: str = Form(...),
    scheduled_time: str = Form(...),
    button_text: str = Form(None),
    button_url: str = Form(None),
    button_style: str = Form('success'),
    button_data: str = Form(None),
    media_file: UploadFile = File(None),
    is_regular: str = Form('0'),
    regular_interval: int = Form(None),
    regular_end_date: str = Form(None),
    regular_end_time: str = Form(None)
):
    """Запланированная публикация поста"""
    user = get_current_user(request)
    
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        # Парсим каналы
        try:
            channels = json.loads(channels_data)
        except json.JSONDecodeError:
            return RedirectResponse(url="/create_post?error=Неверный формат данных каналов", status_code=303)
        
        # Валидация
        if not channels:
            return RedirectResponse(url="/create_post?error=Выберите хотя бы один канал", status_code=303)
        
        if not post_text or not post_text.strip():
            return RedirectResponse(url="/create_post?error=Введите текст поста", status_code=303)
        
        # Парсим кнопку
        button = parse_button_data(button_data)
        if not button:
            button = parse_button_from_form(button_text, button_url, button_style)
        
        # Формируем дату и время
        try:
            scheduled_datetime = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
            scheduled_datetime = pytz.timezone('Europe/Moscow').localize(scheduled_datetime)
            scheduled_time_iso = scheduled_datetime.isoformat()
        except ValueError:
            return RedirectResponse(url="/create_post?error=Неверный формат даты или времени", status_code=303)
        
        # Проверка времени (минимум +5 минут)
        now = datetime.now(pytz.timezone('Europe/Moscow'))
        if scheduled_datetime < now:
            return RedirectResponse(url="/create_post?error=Время публикации не может быть в прошлом", status_code=303)
        
        # Сохраняем медиафайл
        media_info = None
        if media_file and media_file.filename:
            try:
                media_info = await save_uploaded_media(user["id"], media_file)
            except HTTPException as e:
                return RedirectResponse(url=f"/create_post?error={e.detail}", status_code=303)
        
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
        
        # Сохраняем в БД
        post_id = schedule_repo.save_post(
            user["id"],
            channels,
            post_text,
            media_info.get('path') if media_info else None,
            media_info.get('name') if media_info else None,
            media_info.get('size') if media_info else None,
            media_info.get('type') if media_info else None,
            button,
            scheduled_time_iso,
            is_regular_flag,
            regular_settings
        )
        
        if not post_id:
            return RedirectResponse(url="/create_post?error=Ошибка сохранения поста", status_code=303)
        
        # Добавляем в планировщик (только для нерегулярных постов)
        if not is_regular_flag:
            schedule_post(post_id, scheduled_datetime)
        
        success_message = "Регулярный пост создан" if is_regular_flag else "Пост запланирован"
        return RedirectResponse(url=f"/scheduled_posts?success={success_message}", status_code=303)
    
    except Exception as e:
        print(f"Schedule error: {e}")
        return RedirectResponse(url=f"/create_post?error=Ошибка: {str(e)}", status_code=303)


@router.get("/check_status/{post_session_id}")
async def check_status(post_session_id: str):
    """Проверка статуса публикации"""
    if post_session_id not in POST_SESSIONS:
        return JSONResponse({"status": "not_found"})
    
    session = POST_SESSIONS[post_session_id]
    
    if session.get("publishing"):
        return JSONResponse({
            "status": "processing",
            "progress": session.get("progress", 0),
            "channels": session.get("channels", []),
            "total": len(session.get("channels", [])),
            "completed": session.get("completed_count", 0)
        })
    
    results = session.get("results", {"success": 0, "failed": 0})
    return JSONResponse({
        "status": "error" if results.get("failed", 0) > 0 and results.get("success", 0) == 0 else "success",
        "results": results
    })


@router.get("/publish_unified/{post_session_id}", response_class=HTMLResponse)
async def publish_unified_page(request: Request, post_session_id: str):
    """Страница статуса публикации"""
    if post_session_id not in POST_SESSIONS:
        return RedirectResponse(url="/create_post", status_code=303)
    
    session = POST_SESSIONS[post_session_id]
    
    if not session.get("publishing"):
        session["publishing"] = True
        session["progress"] = 0
        session["completed_count"] = 0
        session["results"] = {"success": 0, "failed": 0}
    
    return templates.TemplateResponse("processing.html", {
        "request": request,
        "session_id": post_session_id,
        "total_channels": len(session.get("channels", []))
    })


@router.post("/cancel_publish/{post_session_id}")
async def cancel_publish(request: Request, post_session_id: str):
    """Отмена публикации (удаление из очереди)"""
    user = get_current_user(request)
    
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    if post_session_id not in POST_SESSIONS:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    
    session = POST_SESSIONS[post_session_id]
    
    if session.get("user_id") != user["id"]:
        return JSONResponse({"error": "Forbidden"}, status_code=403)
    
    # Удаляем сессию
    del POST_SESSIONS[post_session_id]
    
    return JSONResponse({"success": True, "message": "Публикация отменена"})