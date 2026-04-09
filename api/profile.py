"""
Управление профилем пользователя
"""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from api.auth import get_current_user
from repositories.user_repo import user_repo
from utils.validators import validate_password
from utils.helpers import clean_email

router = APIRouter(tags=["profile"])


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


@router.post("/change_password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Смена пароля"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Проверка текущего пароля
    from utils.helpers import hash_password
    if user.get("password") != hash_password(current_password):
        return JSONResponse({"error": "Неверный текущий пароль"}, status_code=400)
    
    if new_password != confirm_password:
        return JSONResponse({"error": "Пароли не совпадают"}, status_code=400)
    
    is_valid, error_msg = validate_password(new_password)
    if not is_valid:
        return JSONResponse({"error": error_msg}, status_code=400)
    
    user_repo.update_password(user["id"], new_password)
    return JSONResponse({"success": True, "message": "Пароль изменён"})


@router.post("/delete_account")
async def delete_account(request: Request):
    """Удаление аккаунта"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    user_repo.delete_user(user["id"])
    
    # Удаляем сессию
    session_id = request.cookies.get("session_id")
    if session_id:
        user_repo.delete_session(session_id)
    
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_id")
    return response