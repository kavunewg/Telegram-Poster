"""
Маршруты для работы с очередью
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from repositories.user_repo import user_repo
from repositories.queue_repo import queue_repo

router = APIRouter(tags=["queue"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        session_id = request.cookies.get("session_id")
        if session_id:
            user = user_repo.get_by_session(session_id)
    return user


@router.get("/queue", response_class=HTMLResponse)
async def queue_page(request: Request):
    """Страница очереди"""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse("queue.html", {
        "request": request,
        "user": user,
        "project_name": user.get("project_name")
    })


@router.get("/api/queue")
async def api_get_queue(request: Request):
    """API получения очереди"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    try:
        # Пробуем получить очередь пользователя
        queue_items = queue_repo.get_user_queue(user["id"])
        
        # Если результат None или не список, возвращаем пустой массив
        if not queue_items:
            return JSONResponse([])
        
        # Приводим к списку словарей
        result = []
        for item in queue_items:
            if isinstance(item, dict):
                result.append(item)
            elif isinstance(item, (list, tuple)):
                result.append({
                    "id": item[0] if len(item) > 0 else None,
                    "status": item[1] if len(item) > 1 else "pending",
                    "channel": item[2] if len(item) > 2 else None,
                    "text": item[3] if len(item) > 3 else "",
                    "created_at": item[4] if len(item) > 4 else None
                })
            else:
                result.append({"raw": str(item)})
        
        return JSONResponse(result)
        
    except Exception as e:
        print(f"Error getting queue: {e}")
        return JSONResponse([], status_code=200)  # Возвращаем пустой массив при ошибке


@router.post("/api/queue/retry/{task_id}")
async def api_retry_task(request: Request, task_id: int):
    """Повторная отправка задачи из очереди"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    try:
        success = queue_repo.retry_task(task_id, user["id"])
        if success:
            return JSONResponse({"success": True, "message": "Задача добавлена в очередь"})
        return JSONResponse({"error": "Не удалось повторить задачу"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/queue/{task_id}")
async def api_delete_task(request: Request, task_id: int):
    """Удаление задачи из очереди"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    try:
        success = queue_repo.delete_task(task_id, user["id"])
        if success:
            return JSONResponse({"success": True, "message": "Задача удалена"})
        return JSONResponse({"error": "Не удалось удалить задачу"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)