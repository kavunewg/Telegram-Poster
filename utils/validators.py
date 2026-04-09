"""
Валидаторы
"""
import re
from typing import Tuple


def validate_password(password: str) -> Tuple[bool, str]:
    """Валидация пароля"""
    if len(password) < 6:
        return False, "Пароль должен содержать не менее 6 символов"
    if not re.search(r'[A-Z]', password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву (A-Z)"
    if not re.search(r'[!@#$%^&*]', password):
        return False, "Пароль должен содержать хотя бы один специальный символ (!@#$%^&*)"
    return True, ""


def validate_inn(inn: str) -> bool:
    """Валидация ИНН (10 или 12 цифр)"""
    if not inn:
        return False
    return bool(re.match(r'^\d{10}$|^\d{12}$', inn.strip()))


def validate_channel_id(channel_id: str) -> bool:
    """Валидация ID канала"""
    if not channel_id:
        return False
    # Telegram ID может быть числом (с минусом) или @username
    if channel_id.startswith('@'):
        return True
    try:
        int(channel_id)
        return True
    except ValueError:
        return False
    
def validate_username(username: str) -> bool:
    """Проверка валидности username"""
    if not username:
        return False
    if len(username) < 3 or len(username) > 20:
        return False
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False
    return True


def validate_password(password: str) -> tuple:
    """Проверка сложности пароля"""
    if not password:
        return False, "Пароль не может быть пустым"
    
    if len(password) < 6:
        return False, "Пароль должен содержать минимум 6 символов"
    
    if len(password) > 100:
        return False, "Пароль слишком длинный"
    
    return True, "OK"