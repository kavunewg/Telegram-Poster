from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
import logging

from repositories.user_repo import user_repo

logger = logging.getLogger(__name__)


class LanguageMiddleware(BaseHTTPMiddleware):
    """Set the current UI language from cookies."""

    async def dispatch(self, request: Request, call_next):
        language = request.cookies.get("language", "ru")
        if language not in ["ru", "en"]:
            language = "ru"

        request.state.language = language
        return await call_next(request)


class MaxSizeMiddleware(BaseHTTPMiddleware):
    """Reject requests that are too large."""

    async def dispatch(self, request: Request, call_next):
        max_size = 100 * 1024 * 1024
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_size:
            return RedirectResponse(
                url="/error?message=File too large (max 100MB)",
                status_code=303,
            )

        return await call_next(request)


class AuthMiddleware(BaseHTTPMiddleware):
    """Load the current user and guard private routes."""

    async def dispatch(self, request: Request, call_next):
        request.state.user = None

        public_paths = [
            "/login",
            "/register",
            "/logout",
            "/index",
            "/index.html",
            "/static",
            "/media",
            "/translations",
            "/api/language",
            "/health",
            "/favicon.ico",
        ]

        session_id = request.cookies.get("session_id")
        if session_id:
            request.state.user = user_repo.get_by_session(session_id)

        path = request.url.path
        is_public = path == "/" or any(path.startswith(public_path) for public_path in public_paths)
        if not is_public and not request.state.user:
            logger.debug("Unauthorized access to %s, redirecting to login", path)
            return RedirectResponse(url="/login", status_code=303)

        return await call_next(request)
