"""
Main FastAPI application entrypoint.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api import admin, auth, bots, channels, dashboard, debug, edit_scheduled
from api import posts, queue as queue_router, scheduled, stats, vk_posts, youtube
from api.language import router as language_router
from api.translations import router as translations_router
from core.database import init_db
from core.middleware import AuthMiddleware, LanguageMiddleware
from core.queue_worker import start_queue_worker, stop_queue_worker
from languages import get_lang_from_request
from services.schedule_service import init_scheduler, shutdown_scheduler
from services.vk_worker import start_vk_worker, stop_vk_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hooks."""
    logger.info("Application startup...")

    queue_task = None
    vk_task = None

    try:
        init_db()
        await init_scheduler()
        queue_task = asyncio.create_task(start_queue_worker())
        vk_task = asyncio.create_task(start_vk_worker())
        yield
    finally:
        logger.info("Application shutdown...")
        await shutdown_scheduler()
        await stop_queue_worker()
        await stop_vk_worker()

        for task in (queue_task, vk_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


app = FastAPI(
    title="Telegram Poster",
    description="System for publishing posts to Telegram, VK and MAX",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LanguageMiddleware)
app.add_middleware(AuthMiddleware)

templates = Jinja2Templates(directory="templates")
templates.env.globals["get_lang"] = get_lang_from_request
templates.env.globals["t"] = lambda key, request: get_lang_from_request(request)

for module in (
    auth,
    dashboard,
    channels,
    bots,
    posts,
    scheduled,
    debug,
    admin,
    youtube,
    queue_router,
    stats,
    edit_scheduled,
    vk_posts,
):
    module.set_templates(templates)

app.mount("/static", StaticFiles(directory="static"), name="static")

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
app.include_router(translations_router)
app.include_router(language_router)


@app.get("/")
async def root(request: Request):
    """Redirect authenticated users to dashboard and guests to login."""
    user = getattr(request.state, "user", None)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse("404.html", {"request": request}, status_code=404)


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error("Internal Server Error: %s", exc)
    return templates.TemplateResponse("500.html", {"request": request}, status_code=500)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True, log_level="info")
