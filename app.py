"""
Главная точка входа FastAPI приложения
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from api import edit_scheduled
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from api import vk_posts
from services.vk_worker import start_vk_worker, stop_vk_worker

# =========================
# CONFIG
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# ROUTERS
# =========================
from api import auth, dashboard, channels, bots, posts, scheduled, debug, admin, youtube, queue as queue_router, stats
from api.translations import router as translations_router
from api.language import router as language_router

from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# =========================
# CORE
# =========================
from core.middleware import LanguageMiddleware, AuthMiddleware
from core.database import init_db
from core.queue_worker import start_queue_worker, stop_queue_worker

# =========================
# UTILS
# =========================
from languages import get_lang, get_lang_from_request

# Функция для проверки авторизации (пример)
async def get_current_user_optional(request: Request):
    # Ваша логика проверки сессии
    session_id = request.cookies.get("session_id")
    if session_id:
        # Проверяем сессию в БД
        user = await db.get_user_by_session(session_id)
        return user
    return None

# ГЛАВНАЯ СТРАНИЦА - ЛЕНДИНГ
@app.get("/")
async def landing_page(request: Request):
    user = await get_current_user_optional(request)
    
    if user:
        # Если пользователь уже авторизован → отправляем в админку
        return RedirectResponse(url="/dashboard")
    else:
        # Если не авторизован → показываем лендинг
        return templates.TemplateResponse("landing.html", {"request": request})

# СТРАНИЦА ВХОДА
@app.get("/login")
async def login_page(request: Request):
    user = await get_current_user_optional(request)
    
    if user:
        # Если уже авторизован → в админку
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse("login.html", {"request": request})

# СТРАНИЦА РЕГИСТРАЦИИ
@app.get("/register")
async def register_page(request: Request):
    user = await get_current_user_optional(request)
    
    if user:
        return RedirectResponse(url="/dashboard")
    
    return templates.TemplateResponse("register.html", {"request": request})

# =========================
# LIFECYCLE
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения
    """
    logger.info("🚀 Приложение запускается...")
    
    try:
        # Инициализация базы данных
        init_db()
        logger.info("✅ База данных инициализирована")
        
        # Запуск воркера очереди
        worker_task = asyncio.create_task(start_queue_worker())
        asyncio.create_task(start_vk_worker())
        logger.info("✅ Воркер очереди запущен")
        
        yield
        
    except asyncio.CancelledError:
        logger.info("🛑 Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске: {e}")
    finally:
        # Остановка воркера
        logger.info("🛑 Приложение останавливается...")
        await stop_queue_worker()
        logger.info("✅ Воркер остановлен")


# =========================
# APP INIT
# =========================
app = FastAPI(
    title="Telegram Poster",
    description="Система для публикации постов в Telegram и MAX",
    version="2.0.0",
    lifespan=lifespan
)

# =========================
# MIDDLEWARE
# =========================
# CORS для API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Кастомные middleware
app.add_middleware(LanguageMiddleware)
app.add_middleware(AuthMiddleware)

# =========================
# TEMPLATES
# =========================
templates = Jinja2Templates(directory="templates")

# Добавляем глобальные функции в шаблоны
templates.env.globals["get_lang"] = get_lang_from_request
templates.env.globals["t"] = lambda key, request: get_lang_from_request(request)  # Упрощённо

# Пробрасываем templates во все роутеры
auth.set_templates(templates)
dashboard.set_templates(templates)
channels.set_templates(templates)
bots.set_templates(templates)
posts.set_templates(templates)
scheduled.set_templates(templates)
debug.set_templates(templates)
admin.set_templates(templates)
youtube.set_templates(templates)
queue_router.set_templates(templates)
stats.set_templates(templates)
edit_scheduled.set_templates(templates)
vk_posts.set_templates(templates)

# =========================
# STATIC
# =========================
app.mount("/static", StaticFiles(directory="static"), name="static")

# =========================
# ROUTES
# =========================
# Основные HTML страницы
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(channels.router)
app.include_router(bots.router)
app.include_router(posts.router)
app.include_router(scheduled.router)
app.include_router(debug.router)
app.include_router(admin.router)
app.include_router(youtube.router)
app.include_router(queue_router.router)
app.include_router(stats.router)
app.include_router(edit_scheduled.router)
app.include_router(vk_posts.router)

# API роутеры
app.include_router(translations_router)
app.include_router(language_router)

# =========================
# ROOT ROUTES
# =========================
@app.get("/")
async def root(request: Request):
    """Корневой маршрут - редирект на дашборд или логин"""
    user = getattr(request.state, "user", None)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/queue")
async def queue_page(request: Request):
    """Страница очереди (редирект на queue роутер)"""
    return RedirectResponse(url="/queue/", status_code=307)


# =========================
# ERROR HANDLERS
# =========================
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Обработчик 404 ошибки"""
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Обработчик 500 ошибки"""
    logger.error(f"Internal Server Error: {exc}")
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )