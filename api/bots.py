"""
Routes for bot management.
"""
import json
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.config import DB_PATH, REQUEST_CONFIG
from repositories.bot_repo import bot_repo
from repositories.user_repo import user_repo

router = APIRouter(tags=["bots"])
templates: Jinja2Templates = None


def set_templates(templates_obj: Jinja2Templates):
    global templates
    templates = templates_obj


def get_current_user(request: Request):
    return getattr(request.state, "user", None) or user_repo.get_by_session(request.cookies.get("session_id"))


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


def _bot_groups(user_id: int) -> dict:
    bots = bot_repo.get_user_bots(user_id)
    grouped = {
        "telegram_bots": [bot for bot in bots if bot.get("platform") == "telegram"],
        "max_bots": [bot for bot in bots if bot.get("platform") == "max"],
        "vk_bots": [bot for bot in bots if bot.get("platform") == "vk"],
        "youtube_bots": [bot for bot in bots if bot.get("platform") == "youtube"],
    }
    grouped["telegram_count"] = len(grouped["telegram_bots"])
    grouped["max_count"] = len(grouped["max_bots"])
    grouped["vk_count"] = len(grouped["vk_bots"])
    grouped["youtube_count"] = len(grouped["youtube_bots"])
    return grouped


def _token_exists(token: str, exclude_bot_id: int = None) -> bool:
    if not token:
        return False

    query = "SELECT id FROM user_bots WHERE token = ?"
    params = [token]
    if exclude_bot_id is not None:
        query += " AND id != ?"
        params.append(exclude_bot_id)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return cursor.fetchone() is not None


def _youtube_key_exists(youtube_api_key: str, exclude_bot_id: int = None) -> bool:
    if not youtube_api_key:
        return False

    query = "SELECT id FROM user_bots WHERE youtube_api_key = ?"
    params = [youtube_api_key]
    if exclude_bot_id is not None:
        query += " AND id != ?"
        params.append(exclude_bot_id)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        return cursor.fetchone() is not None


async def _normalize_bot_payload(
    bot_name: str,
    bot_token: str,
    platform: str,
    inn: str = None,
    youtube_api_key: str = None,
    existing_bot_id: int = None,
) -> tuple[dict | None, str | None]:
    platform = (platform or "telegram").lower()
    normalized = {
        "name": (bot_name or "").strip(),
        "token": (bot_token or "").strip(),
        "platform": platform,
        "inn": (inn or "").strip() or None,
        "youtube_api_key": (youtube_api_key or "").strip() or None,
    }

    if platform == "youtube":
        if not normalized["youtube_api_key"]:
            return None, "Для YouTube бота требуется API Key"
        if not normalized["youtube_api_key"].startswith("AIza"):
            return None, "Неверный формат YouTube API Key"
        if _youtube_key_exists(normalized["youtube_api_key"], existing_bot_id):
            return None, "YouTube бот с таким API Key уже существует"
        normalized["token"] = normalized["youtube_api_key"]
        normalized["inn"] = None
        return normalized, None

    if not normalized["token"]:
        return None, "Токен бота обязателен"

    if platform == "max":
        if not normalized["inn"]:
            return None, "Для MAX бота требуется ИНН"
        if not normalized["inn"].isdigit() or len(normalized["inn"]) not in (10, 12):
            return None, "ИНН должен содержать 10 или 12 цифр"

    if platform == "telegram":
        try:
            from telegram import Bot

            test_bot = Bot(token=normalized["token"], request=REQUEST_CONFIG)
            bot_info = await test_bot.get_me()
            normalized["name"] = bot_info.username or normalized["name"]
        except Exception as exc:
            return None, f"Не удалось проверить токен бота: {exc}"

    if _token_exists(normalized["token"], existing_bot_id):
        return None, "Бот с таким токеном уже существует"

    return normalized, None


@router.get("/my_bots", response_class=HTMLResponse)
async def my_bots_page(request: Request):
    user = get_current_user(request)
    if not user:
        return _redirect("/login")

    context = {
        "request": request,
        "user": user,
        "project_name": user.get("project_name"),
    }
    context.update(_bot_groups(user["id"]))
    return templates.TemplateResponse("my_bots.html", context)


@router.post("/add_bot")
async def add_bot(
    request: Request,
    bot_name: str = Form(...),
    bot_token: str = Form(""),
    platform: str = Form("telegram"),
    inn: str = Form(None),
    youtube_api_key: str = Form(None),
):
    user = get_current_user(request)
    if not user:
        return _redirect("/login")

    payload, error = await _normalize_bot_payload(bot_name, bot_token, platform, inn, youtube_api_key)
    if error:
        return _redirect(f"/my_bots?error={error}")

    try:
        bot_repo.add_bot(
            user["id"],
            payload["name"] or payload["platform"],
            payload["token"],
            payload["platform"],
            payload["inn"],
            payload["youtube_api_key"],
        )
    except sqlite3.IntegrityError as exc:
        return _redirect(f"/my_bots?error=Ошибка при добавлении бота: {exc}")

    return _redirect("/my_bots?success=Бот успешно добавлен")


@router.post("/delete_bot/{bot_id}")
async def delete_bot(request: Request, bot_id: int):
    user = get_current_user(request)
    if not user:
        return _redirect("/login")

    if not bot_repo.get_by_id(bot_id, user["id"]):
        return _redirect("/my_bots?error=Бот не найден")

    bot_repo.delete_bot(bot_id, user["id"])
    return _redirect("/my_bots?success=Бот удален")


@router.post("/delete_bot/")
async def delete_bot_post(request: Request):
    user = get_current_user(request)
    if not user:
        return _redirect("/login")

    form_data = await request.form()
    try:
        bot_id = int(form_data.get("bot_id"))
    except (TypeError, ValueError):
        return _redirect("/my_bots?error=Неверный ID бота")

    if not bot_repo.get_by_id(bot_id, user["id"]):
        return _redirect("/my_bots?error=Бот не найден")

    bot_repo.delete_bot(bot_id, user["id"])
    return _redirect("/my_bots?success=Бот удален")


@router.get("/bot_channels/{bot_id}")
async def get_bot_channels(request: Request, bot_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    bot = bot_repo.get_by_id(bot_id, user["id"])
    if not bot:
        return JSONResponse({"error": "Bot not found"}, status_code=404)

    return JSONResponse({"channels": bot_repo.get_bot_channels(bot_id)})


@router.post("/api/add_bot")
async def api_add_bot(
    request: Request,
    bot_name: str = Form(...),
    bot_token: str = Form(""),
    platform: str = Form("telegram"),
    inn: str = Form(None),
    youtube_api_key: str = Form(None),
):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"success": False, "error": "Не авторизован"}, status_code=401)

    payload, error = await _normalize_bot_payload(bot_name, bot_token, platform, inn, youtube_api_key)
    if error:
        return JSONResponse({"success": False, "error": error}, status_code=400)

    try:
        bot_id = bot_repo.add_bot(
            user["id"],
            payload["name"] or payload["platform"],
            payload["token"],
            payload["platform"],
            payload["inn"],
            payload["youtube_api_key"],
        )
    except sqlite3.IntegrityError as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)

    return JSONResponse({"success": True, "message": "Бот успешно добавлен", "bot_id": bot_id})


@router.get("/api/bots")
async def api_get_bots(request: Request):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"success": False, "error": "Не авторизован"}, status_code=401)

    return JSONResponse({"success": True, "bots": bot_repo.get_user_bots(user["id"])})


@router.get("/get_bot/{bot_id}")
async def get_bot(request: Request, bot_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    bot = bot_repo.get_by_id(bot_id, user["id"])
    if not bot:
        return JSONResponse({"error": "Bot not found"}, status_code=404)

    return JSONResponse(
        {
            "id": bot["id"],
            "user_id": bot["user_id"],
            "name": bot["name"],
            "token": bot["token"],
            "platform": bot.get("platform", "telegram"),
            "inn": bot.get("inn"),
            "created_at": bot.get("created_at"),
            "youtube_api_key": bot.get("youtube_api_key"),
            "check_interval": bot.get("check_interval", 15),
        }
    )


@router.post("/update_bot/{bot_id}")
async def update_bot(request: Request, bot_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    bot = bot_repo.get_by_id(bot_id, user["id"])
    if not bot:
        return JSONResponse({"error": "Bot not found"}, status_code=404)

    form_data = await request.form()
    bot_name = form_data.get("bot_name") or bot["name"]
    bot_token = form_data.get("bot_token") or bot["token"]
    inn = form_data.get("inn")
    youtube_api_key = form_data.get("youtube_api_key")
    check_interval_raw = form_data.get("check_interval")
    channel_ids_json = form_data.get("channel_ids")

    payload, error = await _normalize_bot_payload(
        bot_name,
        bot_token,
        bot.get("platform", "telegram"),
        inn if inn is not None else bot.get("inn"),
        youtube_api_key if youtube_api_key is not None else bot.get("youtube_api_key"),
        existing_bot_id=bot_id,
    )
    if error:
        return JSONResponse({"error": error}, status_code=400)

    check_interval = bot.get("check_interval", 15)
    if check_interval_raw:
        try:
            check_interval = int(check_interval_raw)
        except ValueError:
            return JSONResponse({"error": "Неверный интервал проверки"}, status_code=400)

    success = bot_repo.update_bot(
        bot_id,
        user["id"],
        payload["name"] or bot["name"],
        payload["token"],
        payload["platform"],
        payload["inn"],
        payload["youtube_api_key"],
        check_interval,
    )
    if not success:
        return JSONResponse({"error": "Не удалось обновить бота"}, status_code=400)

    if channel_ids_json is not None:
        try:
            channel_ids = json.loads(channel_ids_json) if channel_ids_json else []
        except json.JSONDecodeError:
            return JSONResponse({"error": "Неверный список каналов"}, status_code=400)

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bot_channels WHERE bot_id = ?", (bot_id,))
            for channel_id in channel_ids:
                cursor.execute(
                    "INSERT INTO bot_channels (bot_id, channel_id, created_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (bot_id, channel_id),
                )
            conn.commit()

    return JSONResponse({"success": True, "message": "Бот обновлен"})
