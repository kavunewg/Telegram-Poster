# core/middleware.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
import logging

logger = logging.getLogger(__name__)


class LanguageMiddleware(BaseHTTPMiddleware):
    """Middleware для автоматической установки языка из cookie"""
    async def dispatch(self, request: Request, call_next):
        # Получаем язык из cookie
        language = request.cookies.get("language", "ru")
        
        # Валидация
        if language not in ["ru", "en"]:
            language = "ru"
        
        # Сохраняем в state для использования в шаблонах
        request.state.language = language
        
        response = await call_next(request)
        return response


class MaxSizeMiddleware(BaseHTTPMiddleware):
    """Middleware для ограничения размера запроса"""
    async def dispatch(self, request: Request, call_next):
        max_size = 100 * 1024 * 1024  # 100 MB
        
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_size:
            return RedirectResponse(
                url="/error?message=File too large (max 100MB)",
                status_code=303
            )
        
        response = await call_next(request)
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware для аутентификации"""
    async def dispatch(self, request: Request, call_next):
        # Список публичных маршрутов
        public_paths = [
            "/login",
            "/register",
            "/static",
            "/media",
            "/translations",
            "/api/language",
            "/health",
            "/",
            "/favicon.ico"
        ]
        
        path = request.url.path
        is_public = any(path.startswith(public_path) for public_path in public_paths)
        
        if not is_public:
            session_id = request.cookies.get("session_id")
            
            if not session_id:
                logger.debug(f"Unauthorized access to {path}, redirecting to login")
                return RedirectResponse(url="/login", status_code=303)
        
        response = await call_next(request)
        return response