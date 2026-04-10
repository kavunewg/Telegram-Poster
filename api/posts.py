"""
Routes for creating, publishing, and scheduling posts.
"""

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytz
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core.config import POST_SESSIONS, TIMEZONE
from repositories.bot_repo import bot_repo
from repositories.channel_repo import channel_repo
from repositories.queue_repo import queue_repo
from repositories.schedule_repo import schedule_repo
from repositories.user_repo import user_repo
from services.media_service import save_media_file
from services.schedule_service import schedule_post

logger = logging.getLogger(__name__)

router = APIRouter(tags=["posts"])
templates: Optional[Jinja2Templates] = None


def set_templates(templates_obj: Jinja2Templates) -> None:
    global templates
    templates = templates_obj


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    user = getattr(request.state, "user", None)
    if user:
        return user

    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    return user_repo.get_by_session(session_id)


def _is_ajax(request: Request) -> bool:
    requested_with = request.headers.get("X-Requested-With", "")
    accept = request.headers.get("Accept", "")
    return requested_with == "XMLHttpRequest" or "application/json" in accept.lower()


def _parse_channels_data(channels_data: str) -> List[Dict[str, Any]]:
    try:
        parsed = json.loads(channels_data)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid channels payload") from exc

    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="Channels payload must be a list")
    return parsed


def _parse_button_data(button_data: Optional[str]) -> Optional[Dict[str, Any]]:
    if not button_data or button_data in {"null", "undefined", ""}:
        return None

    try:
        button = json.loads(button_data)
    except json.JSONDecodeError:
        return None

    if not isinstance(button, dict):
        return None

    text = (button.get("text") or "").strip()
    url = (button.get("url") or "").strip()
    if not text or not url:
        return None

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    return {"text": text, "url": url, "style": button.get("style", "success")}


def _parse_button_from_form(
    button_text: Optional[str],
    button_url: Optional[str],
    button_style: str = "success",
) -> Optional[Dict[str, Any]]:
    text = (button_text or "").strip()
    url = (button_url or "").strip()
    if not text or not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return {"text": text, "url": url, "style": button_style or "success"}


def _normalize_channel_id(raw_channel: Dict[str, Any]) -> Optional[int]:
    channel_id = raw_channel.get("id")
    if channel_id is None:
        return None
    try:
        return int(channel_id)
    except (TypeError, ValueError):
        return None


def _build_validated_channels(user_id: int, raw_channels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not raw_channels:
        return []

    db_channels = channel_repo.get_user_channels(user_id)
    db_channels_by_id = {int(ch["id"]): ch for ch in db_channels if ch.get("id") is not None}

    bots = bot_repo.get_user_bots(user_id)
    bots_by_id = {int(b["id"]): b for b in bots if b.get("id") is not None}

    default_bot_by_platform: Dict[str, str] = {}
    for bot in bots:
        platform = bot.get("platform")
        token = bot.get("token")
        if platform and token and platform not in default_bot_by_platform:
            default_bot_by_platform[platform] = token

    validated: List[Dict[str, Any]] = []
    for raw in raw_channels:
        channel_db_id = _normalize_channel_id(raw)
        if channel_db_id is None:
            continue

        db_channel = db_channels_by_id.get(channel_db_id)
        if not db_channel:
            continue

        platform = db_channel.get("platform") or raw.get("platform") or "telegram"
        bot_token = db_channel.get("bot_token")

        if not bot_token:
            raw_bot_id = raw.get("bot_id")
            if raw_bot_id is not None:
                try:
                    bot = bots_by_id.get(int(raw_bot_id))
                    if bot and bot.get("platform") == platform:
                        bot_token = bot.get("token")
                except (TypeError, ValueError):
                    pass

        if not bot_token:
            bot_token = raw.get("bot_token") or raw.get("token") or default_bot_by_platform.get(platform)

        validated.append(
            {
                "id": channel_db_id,
                "name": db_channel.get("channel_name") or raw.get("name") or "Unknown",
                "channel_name": db_channel.get("channel_name") or raw.get("channel_name"),
                "channel_id": db_channel.get("channel_id") or raw.get("channel_id"),
                "platform": platform,
                "bot_token": bot_token,
            }
        )

    return validated


def _validate_channels(channels: List[Dict[str, Any]]) -> Tuple[bool, str]:
    if not channels:
        return False, "Select at least one channel"

    for channel in channels:
        if not channel.get("channel_id"):
            return False, "One of selected channels has empty channel ID"
        if channel.get("platform") == "telegram" and not channel.get("bot_token"):
            return False, f"Telegram bot token missing for channel: {channel.get('name') or channel.get('channel_name')}"

    return True, "OK"


async def _save_uploaded_media(user_id: int, media_file: Optional[UploadFile]) -> Optional[Dict[str, Any]]:
    if not media_file or not media_file.filename:
        return None

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            while True:
                chunk = await media_file.read(1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            file_bytes = f.read()

        return save_media_file(user_id, file_bytes, media_file.filename, "instant")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"File upload failed: {exc}") from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _create_post_session(
    session_id: str,
    user_id: int,
    channels: List[Dict[str, Any]],
    post_text: str,
    media_info: Optional[Dict[str, Any]],
    button: Optional[Dict[str, Any]],
) -> None:
    POST_SESSIONS[session_id] = {
        "user_id": user_id,
        "channels": channels,
        "post_text": post_text,
        "media_path": media_info.get("path") if media_info else None,
        "media_name": media_info.get("name") if media_info else None,
        "media_size": media_info.get("size") if media_info else None,
        "media_type": media_info.get("type") if media_info else None,
        "button": button,
        "publishing": True,
        "progress": 0,
        "completed_count": 0,
        "results": {"success": 0, "failed": 0},
        "created_at": datetime.now().isoformat(),
    }


def _add_tasks_to_queue(
    user_id: int,
    post_session_id: str,
    channels: List[Dict[str, Any]],
    post_text: str,
    media_info: Optional[Dict[str, Any]],
    button: Optional[Dict[str, Any]],
) -> int:
    tasks_count = 0
    for channel in channels:
        bot_token = channel.get("bot_token")
        payload = {
            "user_id": user_id,
            "post_session_id": post_session_id,
            "text": post_text,
            "media_path": media_info.get("path") if media_info else None,
            "media_name": media_info.get("name") if media_info else None,
            "media_size": media_info.get("size") if media_info else None,
            "media_type": media_info.get("type") if media_info else None,
            "button": button,
            "channel": {
                "id": channel.get("id"),
                "name": channel.get("name") or channel.get("channel_name"),
                "channel_id": channel.get("channel_id"),
                "platform": channel.get("platform", "telegram"),
                "bot_token": bot_token,
            },
            "channel_id": channel.get("channel_id"),
            "channel_db_id": channel.get("id"),
            "bot_token": bot_token,
        }

        queue_repo.create_task(
            user_id=user_id,
            channel_id=channel.get("id"),
            platform=channel.get("platform", "telegram"),
            action="send_post",
            payload=payload,
        )
        tasks_count += 1
    return tasks_count


def _parse_scheduled_datetime(scheduled_date: str, scheduled_time: str) -> datetime:
    local_tz = pytz.timezone(TIMEZONE)
    last_error = None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(f"{scheduled_date} {scheduled_time}", fmt)
            return local_tz.localize(dt)
        except ValueError as exc:
            last_error = exc
    raise HTTPException(status_code=400, detail="Invalid date/time format") from last_error


async def _schedule_post_internal(
    *,
    user: Dict[str, Any],
    channels: List[Dict[str, Any]],
    post_text: str,
    scheduled_date: str,
    scheduled_time: str,
    is_regular: str,
    regular_interval: Optional[int],
    regular_end_date: Optional[str],
    regular_end_time: Optional[str],
    media_file: Optional[UploadFile],
    button: Optional[Dict[str, Any]],
) -> int:
    scheduled_dt = _parse_scheduled_datetime(scheduled_date, scheduled_time)
    now_local = datetime.now(pytz.timezone(TIMEZONE))
    if scheduled_dt <= now_local:
        raise HTTPException(status_code=400, detail="Scheduled time cannot be in the past")

    try:
        media_info = await _save_uploaded_media(user["id"], media_file)
    except Exception:
        # scheduled flow has no post session yet
        raise
    is_regular_flag = is_regular == "1"
    regular_settings = None
    if is_regular_flag:
        regular_settings = {
            "interval_hours": regular_interval or 24,
            "start_time": scheduled_dt.isoformat(),
            "end_date": regular_end_date or None,
            "end_time": regular_end_time or None,
        }

    post_id = schedule_repo.save_post(
        user_id=user["id"],
        channels=channels,
        post_text=post_text,
        media_path=media_info.get("path") if media_info else None,
        media_name=media_info.get("name") if media_info else None,
        media_size=media_info.get("size") if media_info else None,
        media_type=media_info.get("type") if media_info else None,
        button=button,
        scheduled_at=scheduled_dt.isoformat(),
        is_regular=is_regular_flag,
        regular_settings=regular_settings,
    )

    if not post_id:
        raise HTTPException(status_code=500, detail="Failed to save scheduled post")

    if not is_regular_flag:
        schedule_post(post_id, scheduled_dt)

    return post_id


@router.get("/create_post", response_class=HTMLResponse)
async def create_post_page(request: Request):
    user = get_current_user(request)
    if not user or user.get("is_admin") == 1:
        return RedirectResponse(url="/dashboard", status_code=303)

    channels = channel_repo.get_user_channels(user["id"])
    bots = bot_repo.get_user_bots(user["id"])
    formatted_channels = [
        {
            "id": ch.get("id"),
            "channel_name": ch.get("channel_name"),
            "channel_id": ch.get("channel_id"),
            "channel_url": ch.get("channel_url"),
            "platform": ch.get("platform"),
            "bot_token": ch.get("bot_token"),
            "bot_name": ch.get("bot_name"),
        }
        for ch in channels
    ]

    return templates.TemplateResponse(
        "create_post.html",
        {
            "request": request,
            "user": user,
            "channels": formatted_channels,
            "bots": bots,
            "project_name": user.get("project_name"),
        },
    )


@router.post("/publish_unified")
async def publish_unified(
    request: Request,
    channels_data: str = Form(...),
    post_text: str = Form(...),
    media_file: UploadFile = File(None),
    button_data: str = Form(None),
    scheduled_date: str = Form(None),
    scheduled_time: str = Form(None),
    is_regular: str = Form("0"),
    regular_interval: Optional[int] = Form(None),
    regular_end_date: str = Form(None),
    regular_end_time: str = Form(None),
):
    user = get_current_user(request)
    if not user or user.get("is_admin") == 1:
        return RedirectResponse(url="/dashboard", status_code=303)

    raw_channels = _parse_channels_data(channels_data)
    channels = _build_validated_channels(user["id"], raw_channels)
    if len(channels) != len(raw_channels):
        raise HTTPException(status_code=400, detail="Some selected channels are invalid or unavailable")
    is_valid, error_msg = _validate_channels(channels)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    clean_post_text = (post_text or "").strip()
    if not clean_post_text:
        raise HTTPException(status_code=400, detail="Enter post text")

    button = _parse_button_data(button_data)

    if scheduled_date and scheduled_time:
        try:
            post_id = await _schedule_post_internal(
                user=user,
                channels=channels,
                post_text=clean_post_text,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time,
                is_regular=is_regular,
                regular_interval=regular_interval,
                regular_end_date=regular_end_date,
                regular_end_time=regular_end_time,
                media_file=media_file,
                button=button,
            )
        except HTTPException as exc:
            if _is_ajax(request):
                return JSONResponse({"success": False, "detail": exc.detail}, status_code=exc.status_code)
            raise
        except Exception as exc:
            logger.exception("Scheduling via /publish_unified failed")
            if _is_ajax(request):
                return JSONResponse({"success": False, "detail": str(exc)}, status_code=500)
            raise
        if _is_ajax(request):
            return JSONResponse(
                {
                    "success": True,
                    "scheduled": True,
                    "post_id": post_id,
                    "message": "Post scheduled successfully",
                }
            )
        return RedirectResponse(url="/scheduled_posts?success=Post+scheduled", status_code=303)

    post_session_id = str(uuid.uuid4())
    _create_post_session(
        session_id=post_session_id,
        user_id=user["id"],
        channels=channels,
        post_text=clean_post_text,
        media_info=None,
        button=button,
    )

    media_info = await _save_uploaded_media(user["id"], media_file)
    tasks_count = _add_tasks_to_queue(
        user_id=user["id"],
        post_session_id=post_session_id,
        channels=channels,
        post_text=clean_post_text,
        media_info=media_info,
        button=button,
    )
    session = POST_SESSIONS.get(post_session_id)
    if session:
        session["media_path"] = media_info.get("path") if media_info else None
        session["media_name"] = media_info.get("name") if media_info else None
        session["media_size"] = media_info.get("size") if media_info else None
        session["media_type"] = media_info.get("type") if media_info else None

    if _is_ajax(request):
        return JSONResponse(
            {
                "success": True,
                "session_id": post_session_id,
                "tasks_count": tasks_count,
                "message": f"Post queued for {tasks_count} channel(s)",
            }
        )

    response = RedirectResponse(url=f"/publish_unified/{post_session_id}", status_code=303)
    response.set_cookie(key="post_session_id", value=post_session_id)
    return response


@router.post("/schedule_post")
async def schedule_post_endpoint(
    request: Request,
    channels_data: str = Form(...),
    post_text: str = Form(...),
    scheduled_date: str = Form(...),
    scheduled_time: str = Form(...),
    button_text: str = Form(None),
    button_url: str = Form(None),
    button_style: str = Form("success"),
    button_data: str = Form(None),
    media_file: UploadFile = File(None),
    is_regular: str = Form("0"),
    regular_interval: Optional[int] = Form(None),
    regular_end_date: str = Form(None),
    regular_end_time: str = Form(None),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    raw_channels = _parse_channels_data(channels_data)
    channels = _build_validated_channels(user["id"], raw_channels)
    if len(channels) != len(raw_channels):
        return RedirectResponse(url="/create_post?error=Some+channels+are+invalid", status_code=303)
    is_valid, error_msg = _validate_channels(channels)
    if not is_valid:
        return RedirectResponse(url=f"/create_post?error={error_msg}", status_code=303)

    clean_post_text = (post_text or "").strip()
    if not clean_post_text:
        return RedirectResponse(url="/create_post?error=Enter+post+text", status_code=303)

    button = _parse_button_data(button_data) or _parse_button_from_form(button_text, button_url, button_style)

    try:
        await _schedule_post_internal(
            user=user,
            channels=channels,
            post_text=clean_post_text,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            is_regular=is_regular,
            regular_interval=regular_interval,
            regular_end_date=regular_end_date,
            regular_end_time=regular_end_time,
            media_file=media_file,
            button=button,
        )
    except HTTPException as exc:
        return RedirectResponse(url=f"/create_post?error={exc.detail}", status_code=303)
    except Exception as exc:
        logger.exception("Schedule post failed")
        return RedirectResponse(url=f"/create_post?error={exc}", status_code=303)

    success_message = "Regular post created" if is_regular == "1" else "Post scheduled"
    return RedirectResponse(url=f"/scheduled_posts?success={success_message}", status_code=303)


@router.get("/check_status/{post_session_id}")
async def check_status(post_session_id: str):
    session = POST_SESSIONS.get(post_session_id)
    if not session:
        return JSONResponse({"status": "not_found"})

    if session.get("publishing"):
        channels = session.get("channels", [])
        return JSONResponse(
            {
                "status": "processing",
                "progress": session.get("progress", 0),
                "channels": channels,
                "total": len(channels),
                "completed": session.get("completed_count", 0),
            }
        )

    channels = session.get("channels", [])
    results = session.get("results", {"success": 0, "failed": 0})
    results["total"] = len(channels)
    final_status = "error" if results.get("failed", 0) > 0 and results.get("success", 0) == 0 else "success"
    return JSONResponse({"status": final_status, "results": results})


@router.get("/publish_unified/{post_session_id}", response_class=HTMLResponse)
async def publish_unified_page(request: Request, post_session_id: str):
    session = POST_SESSIONS.get(post_session_id)
    if not session:
        return RedirectResponse(url="/create_post", status_code=303)

    return templates.TemplateResponse(
        "processing.html",
        {
            "request": request,
            "session_id": post_session_id,
            "total_channels": len(session.get("channels", [])),
        },
    )


@router.post("/cancel_publish/{post_session_id}")
async def cancel_publish(request: Request, post_session_id: str):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    session = POST_SESSIONS.get(post_session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    if session.get("user_id") != user["id"]:
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    del POST_SESSIONS[post_session_id]
    return JSONResponse({"success": True, "message": "Publishing cancelled"})
