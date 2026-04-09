"""
API routers bootstrap.
"""
from fastapi.templating import Jinja2Templates

from api import admin, auth, bots, channels, dashboard, debug, edit_scheduled, posts, queue as queue_router, scheduled, stats, youtube

templates: Jinja2Templates = None


def setup_routes(app, templates_obj: Jinja2Templates):
    """Configure application routers and shared templates."""
    global templates
    templates = templates_obj

    auth.set_templates(templates_obj)
    dashboard.set_templates(templates_obj)
    channels.set_templates(templates_obj)
    bots.set_templates(templates_obj)
    posts.set_templates(templates_obj)
    scheduled.set_templates(templates_obj)
    youtube.set_templates(templates_obj)
    admin.set_templates(templates_obj)
    queue_router.set_templates(templates_obj)
    stats.set_templates(templates_obj)

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(channels.router)
    app.include_router(bots.router)
    app.include_router(posts.router)
    app.include_router(scheduled.router)
    app.include_router(debug.router)
    app.include_router(youtube.router)
    app.include_router(admin.router)
    app.include_router(queue_router.router)
    app.include_router(stats.router)
    app.include_router(edit_scheduled.router)

    return app
