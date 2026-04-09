"""
Вспомогательные функции
"""
import hashlib
import re
from typing import Tuple


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()


def clean_email(email: str) -> str:
    if not email:
        return ''
    email = email.strip()
    if '@' not in email:
        return ''
    return email


def escape_html(text: str) -> str:
    """Экранирование HTML символов"""
    if not text:
        return ''
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def format_datetime(dt_str: str, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """Форматирование даты и времени"""
    if not dt_str:
        return ''
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime(format_str)
    except Exception:
        return dt_str[:16] if dt_str else ''