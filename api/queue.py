"""
Routes for viewing and managing the send queue.
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from repositories.queue_repo import queue_repo
from repositories.user_repo import user_repo

router = APIRouter(tags=["queue"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    return getattr(request.state, "user", None) or user_repo.get_by_session(request.cookies.get("session_id"))


@router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        "queue.html",
        {
            "request": request,
            "user": user,
            "project_name": user.get("project_name"),
        },
    )


@router.get("/api/queue")
async def api_get_queue(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        return JSONResponse(queue_repo.get_user_queue(user["id"]) or [])
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.post("/api/queue/retry/{task_id}")
async def api_retry_task(request: Request, task_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        success = queue_repo.retry_task(task_id, user["id"])
        if success:
            return JSONResponse({"success": True, "message": "Задача добавлена в очередь"})
        return JSONResponse({"error": "Не удалось повторить задачу"}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.delete("/api/queue/{task_id}")
async def api_delete_task(request: Request, task_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        success = queue_repo.delete_task(task_id, user["id"])
        if success:
            return JSONResponse({"success": True, "message": "Задача удалена"})
        return JSONResponse({"error": "Не удалось удалить задачу"}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
