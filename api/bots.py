"""
Маршруты для управления ботами - ПОЛНАЯ ВЕРСИЯ
"""
import sqlite3
from datetime import datetime
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.bot_repo import bot_repo
from core.config import REQUEST_CONFIG, DB_PATH
from languages import get_lang_from_request

import json

router = APIRouter(tags=["bots"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    """Унифицированное получение текущего пользователя"""
    user = getattr(request.state, "user", None)
    if not user:
        session_id = request.cookies.get("session_id")
        if session_id:
            user = user_repo.get_by_session(session_id)
    return user


@router.get("/my_bots", response_class=HTMLResponse)
async def my_bots_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    bots = bot_repo.get_user_bots(user["id"])
    telegram_bots = [b for b in bots if b.get('platform') == 'telegram']
    max_bots = [b for b in bots if b.get('platform') == 'max']
    youtube_bots = [b for b in bots if b.get('platform') == 'youtube']
    
    return templates.TemplateResponse("my_bots.html", {
        "request": request,
        "user": user,
        "telegram_bots": telegram_bots,
        "max_bots": max_bots,
        "youtube_bots": youtube_bots,
        "telegram_count": len(telegram_bots),
        "max_count": len(max_bots),
        "youtube_count": len(youtube_bots),
        "project_name": user.get("project_name")
    })


@router.post("/add_bot")
async def add_bot(
    request: Request,
    bot_name: str = Form(...),
    bot_token: str = Form(...),
    platform: str = Form('telegram'),
    inn: str = Form(None),
    youtube_api_key: str = Form(None)
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    lang = get_lang_from_request(request)
    
    # Для YouTube бота
    if platform == 'youtube':
        if not youtube_api_key:
            error_msg = "Для YouTube мониторинга требуется API Key" if lang == 'ru' else "YouTube API Key is required"
            return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        if not youtube_api_key.startswith('AIza'):
            error_msg = "Неверный формат YouTube API Key" if lang == 'ru' else "Invalid YouTube API Key format"
            return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        # Проверяем уникальность youtube_api_key
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_bots WHERE youtube_api_key = ?", (youtube_api_key,))
            existing = cursor.fetchone()
            if existing:
                error_msg = "YouTube бот с таким API Key уже существует" if lang == 'ru' else "YouTube bot with this API Key already exists"
                return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        actual_token = youtube_api_key
        actual_youtube_key = youtube_api_key
        actual_inn = None

    # В api/bots.py, в функции add_bot, после обработки YouTube бота:

    # Для VK бота
    elif platform == 'vk':
        if not bot_token:
            error_msg = "Токен доступа VK обязателен" if lang == 'ru' else "VK access token is required"
            return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        # Проверяем VK токен
        try:
            from services.vk_service import VKService, VKAPIError
            vk = VKService(bot_token)
            await vk.check_token()
        except VKAPIError as e:
            error_msg = f"Неверный токен VK: {e.error_msg}" if lang == 'ru' else f"Invalid VK token: {e.error_msg}"
            return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        except Exception as e:
            error_msg = f"Ошибка проверки токена: {str(e)}"
            return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        actual_token = bot_token
        actual_youtube_key = None
        actual_inn = None
    
    # Для MAX бота
    elif platform == 'max':
        if not inn:
            error_msg = "Для подключения MAX бота требуется ИНН" if lang == 'ru' else "INN is required for MAX bot"
            return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        if not inn.isdigit() or len(inn) not in [10, 12]:
            error_msg = "ИНН должен содержать 10 или 12 цифр" if lang == 'ru' else "INN must contain 10 or 12 digits"
            return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        # Проверяем уникальность токена
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_bots WHERE token = ?", (bot_token,))
            existing = cursor.fetchone()
            if existing:
                error_msg = "Бот с таким токеном уже существует" if lang == 'ru' else "Bot with this token already exists"
                return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        actual_token = bot_token
        actual_youtube_key = None
        actual_inn = inn
    
    # Для Telegram бота
    else:  # platform == 'telegram'
        if not bot_token:
            error_msg = "Токен бота обязателен" if lang == 'ru' else "Bot token is required"
            return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        # Проверяем Telegram бота
        try:
            from telegram import Bot
            test_bot = Bot(token=bot_token, request=REQUEST_CONFIG)
            bot_info = await test_bot.get_me()
            bot_name = bot_info.username or bot_name
        except Exception as e:
            error_msg = f"Не удалось проверить токен бота: {str(e)}"
            return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        # Проверяем уникальность токена
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM user_bots WHERE token = ?", (bot_token,))
            existing = cursor.fetchone()
            if existing:
                error_msg = "Бот с таким токеном уже существует" if lang == 'ru' else "Bot with this token already exists"
                return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)
        
        actual_token = bot_token
        actual_youtube_key = None
        actual_inn = None
    
    # Добавляем бота
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO user_bots (user_id, name, token, platform, inn, youtube_api_key, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user["id"], bot_name, actual_token, platform, actual_inn, actual_youtube_key, datetime.now().isoformat()))
            conn.commit()
            bot_id = cursor.lastrowid
            
            success_msg = "Бот успешно добавлен" if lang == 'ru' else "Bot successfully added"
            return RedirectResponse(url=f"/my_bots?success={success_msg}", status_code=303)
            
        except sqlite3.IntegrityError as e:
            error_msg = f"Ошибка при добавлении бота: {e}" if lang == 'ru' else f"Error adding bot: {e}"
            return RedirectResponse(url=f"/my_bots?error={error_msg}", status_code=303)


@router.post("/delete_bot/{bot_id}")
async def delete_bot(request: Request, bot_id: int):
    """Удаление бота по ID из URL"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Проверяем, что бот принадлежит пользователю
    bot = bot_repo.get_by_id(bot_id, user["id"])
    if not bot:
        return RedirectResponse(url="/my_bots?error=Бот не найден", status_code=303)
    
    bot_repo.delete_bot(bot_id)
    return RedirectResponse(url="/my_bots?success=Бот удален", status_code=303)


@router.get("/my_bots", response_class=HTMLResponse)
async def my_bots_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    bots = bot_repo.get_user_bots(user["id"])
    telegram_bots = [b for b in bots if b.get('platform') == 'telegram']
    max_bots = [b for b in bots if b.get('platform') == 'max']
    vk_bots = [b for b in bots if b.get('platform') == 'vk']
    youtube_bots = [b for b in bots if b.get('platform') == 'youtube']
    
    return templates.TemplateResponse("my_bots.html", {
        "request": request,
        "user": user,
        "telegram_bots": telegram_bots,
        "max_bots": max_bots,
        "vk_bots": vk_bots,
        "youtube_bots": youtube_bots,
        "telegram_count": len(telegram_bots),
        "max_count": len(max_bots),
        "vk_count": len(vk_bots),
        "youtube_count": len(youtube_bots),
        "project_name": user.get("project_name")
    })


@router.post("/delete_bot/")
async def delete_bot_post(request: Request):
    """Удаление бота (альтернативный маршрут для форм без ID в URL)"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    form_data = await request.form()
    bot_id = form_data.get("bot_id")
    
    if not bot_id:
        return RedirectResponse(url="/my_bots?error=Не указан ID бота", status_code=303)
    
    try:
        bot_id = int(bot_id)
    except ValueError:
        return RedirectResponse(url="/my_bots?error=Неверный ID бота", status_code=303)
    
    bot = bot_repo.get_by_id(bot_id, user["id"])
    if not bot:
        return RedirectResponse(url="/my_bots?error=Бот не найден", status_code=303)
    
    bot_repo.delete_bot(bot_id)
    return RedirectResponse(url="/my_bots?success=Бот удален", status_code=303)


@router.get("/bot_channels/{bot_id}")
async def get_bot_channels(request: Request, bot_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Проверяем, что бот принадлежит пользователю
    bot = bot_repo.get_by_id(bot_id, user["id"])
    if not bot:
        return JSONResponse({"error": "Bot not found"}, status_code=404)
    
    channels = bot_repo.get_bot_channels(bot_id)
    return JSONResponse({"channels": channels})


@router.post("/api/add_bot")
async def api_add_bot(
    request: Request,
    bot_name: str = Form(...),
    bot_token: str = Form(...),
    platform: str = Form('telegram'),
    inn: str = Form(None),
    youtube_api_key: str = Form(None)
):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"success": False, "error": "Не авторизован"}, status_code=401)
    
    lang = get_lang_from_request(request)
    
    if platform == 'max' and not inn:
        return JSONResponse({"success": False, "error": "Для MAX бота требуется ИНН"}, status_code=400)
    
    if platform == 'youtube' and not youtube_api_key:
        return JSONResponse({"success": False, "error": "Для YouTube бота требуется API Key"}, status_code=400)
    
    if platform == 'telegram':
        try:
            from telegram import Bot
            test_bot = Bot(token=bot_token, request=REQUEST_CONFIG)
            bot_info = await test_bot.get_me()
            bot_name = bot_info.username or bot_name
        except Exception as e:
            return JSONResponse({"success": False, "error": f"Не удалось проверить токен бота: {str(e)}"}, status_code=400)
    
    bot_id = bot_repo.add_bot(user["id"], bot_name, bot_token, platform, inn, youtube_api_key)
    
    if bot_id:
        return JSONResponse({"success": True, "message": "Бот успешно добавлен", "bot_id": bot_id})
    else:
        return JSONResponse({"success": False, "error": "Бот с таким токеном уже существует"}, status_code=400)


@router.get("/api/bots")
async def api_get_bots(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"success": False, "error": "Не авторизован"}, status_code=401)
    
    bots = bot_repo.get_user_bots(user["id"])
    return JSONResponse({"success": True, "bots": bots})


@router.get("/get_bot/{bot_id}")
async def get_bot(request: Request, bot_id: int):
    """Получение данных бота для редактирования"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Получаем бота
    bot = bot_repo.get_by_id(bot_id, user["id"])
    if not bot:
        return JSONResponse({"error": "Bot not found"}, status_code=404)
    
    # Получаем данные бота
    bot_data = {
        "id": bot["id"],
        "user_id": bot["user_id"],
        "name": bot["name"],
        "token": bot["token"],
        "platform": bot.get("platform", "telegram"),
        "inn": bot.get("inn"),
        "created_at": bot.get("created_at"),
        "youtube_api_key": bot.get("youtube_api_key"),
        "check_interval": bot.get("check_interval", 15)
    }
    
    return JSONResponse(bot_data)


@router.post("/update_bot/{bot_id}")
async def update_bot(request: Request, bot_id: int):
    """Обновление данных бота"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Проверяем, что бот принадлежит пользователю
    bot = bot_repo.get_by_id(bot_id, user["id"])
    if not bot:
        return JSONResponse({"error": "Bot not found"}, status_code=404)
    
    form_data = await request.form()
    
    bot_name = form_data.get("bot_name")
    bot_token = form_data.get("bot_token")
    inn = form_data.get("inn")
    youtube_api_key = form_data.get("youtube_api_key")
    check_interval = form_data.get("check_interval")
    channel_ids_json = form_data.get("channel_ids")
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Обновляем название бота
        if bot_name:
            cursor.execute("UPDATE user_bots SET name = ? WHERE id = ? AND user_id = ?", 
                          (bot_name, bot_id, user["id"]))
        
        # Обновляем токен ТОЛЬКО если он указан и отличается от текущего
        if bot_token and bot_token.strip():
            # Проверяем, не занят ли токен другим ботом
            cursor.execute("SELECT id FROM user_bots WHERE token = ? AND id != ?", (bot_token.strip(), bot_id))
            existing = cursor.fetchone()
            if existing:
                return JSONResponse({"error": "Бот с таким токеном уже существует"}, status_code=400)
            
            cursor.execute("UPDATE user_bots SET token = ? WHERE id = ? AND user_id = ?", 
                          (bot_token.strip(), bot_id, user["id"]))
        
        # Обновляем ИНН (для MAX)
        if inn is not None:
            cursor.execute("UPDATE user_bots SET inn = ? WHERE id = ? AND user_id = ?", 
                          (inn if inn else None, bot_id, user["id"]))
        
        # Обновляем YouTube API Key (только если указан и отличается)
        if youtube_api_key is not None and youtube_api_key.strip():
            # Проверяем, не занят ли ключ другим ботом
            cursor.execute("SELECT id FROM user_bots WHERE youtube_api_key = ? AND id != ?", (youtube_api_key.strip(), bot_id))
            existing = cursor.fetchone()
            if existing:
                return JSONResponse({"error": "YouTube бот с таким API Key уже существует"}, status_code=400)
            
            cursor.execute("UPDATE user_bots SET youtube_api_key = ? WHERE id = ? AND user_id = ?", 
                          (youtube_api_key.strip(), bot_id, user["id"]))
        
        # Обновляем частоту проверки
        if check_interval:
            cursor.execute("UPDATE user_bots SET check_interval = ? WHERE id = ? AND user_id = ?", 
                          (int(check_interval), bot_id, user["id"]))
        
        # Обновляем привязку каналов
        if channel_ids_json:
            channel_ids = json.loads(channel_ids_json)
            
            # Удаляем старые связи
            cursor.execute("DELETE FROM bot_channels WHERE bot_id = ?", (bot_id,))
            
            # Добавляем новые
            for channel_id in channel_ids:
                cursor.execute("""
                    INSERT INTO bot_channels (bot_id, channel_id, created_at)
                    VALUES (?, ?, ?)
                """, (bot_id, channel_id, datetime.now().isoformat()))

    # ==================== ДОПОЛНИТЕЛЬНЫЕ МАРШРУТЫ ДЛЯ УДАЛЕНИЯ ====================

    @router.post("/delete_bot/")
    async def delete_bot_post(request: Request):
        """Удаление бота - альтернативный маршрут для форм"""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)
        
        form_data = await request.form()
        bot_id = form_data.get("bot_id")
        
        if not bot_id:
            return RedirectResponse(url="/my_bots?error=Не указан ID бота", status_code=303)
        
        try:
            bot_id = int(bot_id)
        except ValueError:
            return RedirectResponse(url="/my_bots?error=Неверный ID бота", status_code=303)
        
        bot = bot_repo.get_by_id(bot_id, user["id"])
        if not bot:
            return RedirectResponse(url="/my_bots?error=Бот не найден", status_code=303)
        
        bot_repo.delete_bot(bot_id)
        return RedirectResponse(url="/my_bots?success=Бот удален", status_code=303)
        
    conn.commit()
    
    return JSONResponse({"success": True, "message": "Бот обновлён"})