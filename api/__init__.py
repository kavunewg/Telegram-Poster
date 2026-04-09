"""
API роутеры
"""
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from api import edit_scheduled

from api import auth, dashboard, channels, bots, posts, scheduled, debug, admin, youtube, queue as queue_router, stats, edit_scheduled

templates: Jinja2Templates = None


def setup_routes(app, templates_obj: Jinja2Templates):
    """Настройка всех роутеров"""
    global templates
    templates = templates_obj
    
    # Передаём шаблоны
    auth.set_templates(templates_obj)
    dashboard.set_templates(templates_obj)
    channels.set_templates(templates_obj)
    bots.set_templates(templates_obj)
    posts.set_templates(templates_obj)
    scheduled.set_templates(templates_obj)
    youtube.set_templates(templates_obj)
    admin.set_templates(templates_obj)
    queue.set_templates(templates_obj) 
    stats.set_templates(templates_obj)
    
    # Подключаем роутеры
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(channels.router)
    app.include_router(bots.router)
    app.include_router(posts.router)
    app.include_router(scheduled.router)
    app.include_router(youtube.router)
    app.include_router(admin.router)
    app.include_router(queue.router)
    app.include_router(stats.router)
    
    return app