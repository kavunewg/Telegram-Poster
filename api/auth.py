"""
Аутентификация и регистрация - УПРОЩЁННАЯ ВЕРСИЯ
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from utils.helpers import hash_password, clean_email
from languages import get_lang_from_request

router = APIRouter(tags=["auth"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    """Получение текущего пользователя из сессии"""
    user = getattr(request.state, "user", None)
    if not user:
        session_id = request.cookies.get("session_id")
        if session_id:
            user = user_repo.get_by_session(session_id)
    return user


# ==================== HTML СТРАНИЦЫ ====================

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации"""
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/logout")
async def logout(request: Request):
    """Выход из системы"""
    session_id = request.cookies.get("session_id")
    if session_id:
        user_repo.delete_session(session_id)
    
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_id")
    return response


# ==================== ОБРАБОТЧИКИ ФОРМ ====================

@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Обработка входа"""
    user = user_repo.get_by_username(username)
    
    # Простая проверка пароля
    if not user or user.get("password_hash") != hash_password(password):
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "Неверный логин или пароль"}
        )
    
    # Создаём сессию
    session_id = user_repo.create_session(user["id"])
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=86400)
    
    # Устанавливаем язык
    lang = get_lang_from_request(request)
    response.set_cookie(key="language", value=lang, httponly=True, max_age=31536000)
    
    return response


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    full_name: str = Form(...),
    email: str = Form("")
):
    """Обработка регистрации"""
    # Простые проверки
    if len(username) < 3:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Логин должен содержать минимум 3 символа"}
        )
    
    if len(password) < 6:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Пароль должен содержать минимум 6 символов"}
        )
    
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Пароли не совпадают"}
        )
    
    email = clean_email(email) if email else None
    
    # Проверка существования
    if user_repo.get_by_username(username):
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Пользователь с таким логином уже существует"}
        )
    
    if email and user_repo.get_by_email(email):
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Пользователь с таким email уже существует"}
        )
    
    # Создаём пользователя
    user_id = user_repo.create(username, password, full_name, email)
    
    if not user_id:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "error": "Ошибка при создании пользователя"}
        )
    
    # Автоматический вход
    session_id = user_repo.create_session(user_id)
    
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=86400)
    
    lang = get_lang_from_request(request)
    response.set_cookie(key="language", value=lang, httponly=True, max_age=31536000)
    
    return response


@router.post("/set_language")
async def set_language(request: Request, language: str = Form(...)):
    """Смена языка"""
    from languages import loc
    if language in ['ru', 'en']:
        loc.set_language(language)
        response = RedirectResponse(url=request.headers.get('referer', '/dashboard'), status_code=303)
        response.set_cookie(key="language", value=language, httponly=True, max_age=31536000)
        return response
    return RedirectResponse(url='/dashboard', status_code=303)
