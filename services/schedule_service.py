"""
Scheduler service for delayed posts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core.config import TIMEZONE, YOUTUBE_AVAILABLE, POST_SESSIONS
from repositories.schedule_repo import schedule_repo
from services.media_service import delete_media_file
from services.post_service import send_post_async

logger = logging.getLogger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None
_scheduler_shutdown = False


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=pytz.UTC)
    return _scheduler


async def init_scheduler() -> None:
    global _scheduler_shutdown
    _scheduler_shutdown = False

    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()

    await restore_pending_posts()

    # YouTube monitoring uses per-user API keys from DB, global key is optional.
    if YOUTUBE_AVAILABLE:
        from services.youtube_service import check_youtube_channels

        scheduler.add_job(
            check_youtube_channels,
            trigger=IntervalTrigger(minutes=15),
            id="youtube_monitor",
            replace_existing=True,
        )


async def shutdown_scheduler() -> None:
    global _scheduler, _scheduler_shutdown
    _scheduler_shutdown = True
    if _scheduler:
        _scheduler.remove_all_jobs()
        _scheduler.shutdown(wait=False)
        _scheduler = None


async def restore_pending_posts() -> None:
    pending_posts = schedule_repo.get_pending_posts()
    now = datetime.now(pytz.UTC)

    for post in pending_posts:
        try:
            scheduled_time = datetime.fromisoformat(post["scheduled_at"])
            if scheduled_time.tzinfo is None:
                scheduled_time = pytz.timezone(TIMEZONE).localize(scheduled_time).astimezone(pytz.UTC)

            if scheduled_time < now:
                scheduled_time = now + timedelta(minutes=5)
                schedule_repo.update_scheduled_time(post["id"], scheduled_time.isoformat())

            schedule_post(post["id"], scheduled_time)
        except Exception as exc:
            logger.error("Failed to restore post %s: %s", post.get("id"), exc)


def schedule_post(post_id: int, scheduled_time: datetime) -> None:
    if _scheduler_shutdown:
        return

    if scheduled_time.tzinfo is None:
        scheduled_time = pytz.timezone(TIMEZONE).localize(scheduled_time).astimezone(pytz.UTC)

    scheduler = get_scheduler()
    scheduler.add_job(
        execute_scheduled_post,
        trigger=DateTrigger(run_date=scheduled_time),
        args=[post_id],
        id=f"post_{post_id}",
        replace_existing=True,
        misfire_grace_time=60,
    )


def cancel_scheduled_post(post_id: int) -> None:
    scheduler = get_scheduler()
    job = scheduler.get_job(f"post_{post_id}")
    if job:
        job.remove()


def reschedule_post(post_id: int, scheduled_time: datetime) -> None:
    cancel_scheduled_post(post_id)
    schedule_post(post_id, scheduled_time)


async def execute_scheduled_post(post_id: int) -> None:
    if _scheduler_shutdown:
        return

    post = schedule_repo.get_post_by_id(post_id)
    if not post or post["status"] != "pending":
        return

    schedule_repo.update_status(post_id, "processing")

    session = {
        "user_id": post["user_id"],
        "channels": post.get("channels", []),
        "post_text": post["post_text"],
        "media_path": post["media_path"],
        "media_name": post["media_name"],
        "media_size": post["media_size"],
        "media_type": post["media_type"],
        "button": post.get("button"),
        "publishing": True,
    }

    temp_session_id = f"scheduled-{post_id}"
    POST_SESSIONS[temp_session_id] = session

    try:
        results = await asyncio.wait_for(send_post_async(temp_session_id, session), timeout=300)

        if post.get("is_regular"):
            await handle_regular_post_result(
                post_id,
                results,
                post["user_id"],
                post.get("channels", []),
                post["post_text"],
                post["media_path"],
                post["media_name"],
                post["media_size"],
                post["media_type"],
                post.get("button"),
                post.get("regular_settings"),
            )
        else:
            if results.get("failed", 0) == 0:
                schedule_repo.update_status(post_id, "success")
            else:
                schedule_repo.update_status(post_id, "partial")
                if post["media_path"]:
                    delete_media_file(post["media_path"])
    except asyncio.TimeoutError:
        schedule_repo.update_status(post_id, "error")
        if post["media_path"] and not post.get("is_regular"):
            delete_media_file(post["media_path"])
    except Exception as exc:
        logger.error("Scheduled post %s failed: %s", post_id, exc)
        schedule_repo.update_status(post_id, "error")
        if post["media_path"] and not post.get("is_regular"):
            delete_media_file(post["media_path"])
    finally:
        POST_SESSIONS.pop(temp_session_id, None)


async def handle_regular_post_result(
    post_id: int,
    results: Dict,
    user_id: int,
    channels_list: list,
    post_text: str,
    media_path: str,
    media_name: str,
    media_size: float,
    media_type: str,
    button_dict: Dict,
    regular_settings: Dict,
) -> None:
    if results.get("failed", 0) != 0:
        schedule_repo.update_status(post_id, "error")
        return

    interval_hours = regular_settings.get("interval_hours", 24) if regular_settings else 24
    end_date = regular_settings.get("end_date") if regular_settings else None
    end_time = regular_settings.get("end_time") if regular_settings else None
    post = schedule_repo.get_post_by_id(post_id)
    if not post:
        return

    current_time = datetime.fromisoformat(post["scheduled_at"])
    next_time = current_time + timedelta(hours=interval_hours)

    should_continue = True
    if end_date:
        local_tz = pytz.timezone(TIMEZONE)
        if end_time:
            end_datetime = local_tz.localize(datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M"))
        else:
            end_datetime = local_tz.localize(datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59))

        if next_time.tzinfo is None:
            next_time = local_tz.localize(next_time)
        if next_time > end_datetime:
            should_continue = False

    if should_continue:
        new_post_id = schedule_repo.save_post(
            user_id,
            channels_list,
            post_text,
            media_path,
            media_name,
            media_size,
            media_type,
            button_dict,
            next_time.isoformat(),
            is_regular=True,
            regular_settings=regular_settings,
        )
        schedule_post(new_post_id, next_time)

    schedule_repo.update_status(post_id, "success")


async def check_youtube_channels_wrapper():
    from services.youtube_service import check_youtube_channels

    await check_youtube_channels()
