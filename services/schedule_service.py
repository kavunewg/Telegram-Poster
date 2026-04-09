"""
Сервис для управления планировщиком отложенных постов
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core.config import TIMEZONE, POST_SESSIONS
from repositories.schedule_repo import schedule_repo
from repositories.post_stats_repo import post_stats_repo
from services.post_service import send_post_async
from services.media_service import delete_media_file

logger = logging.getLogger(__name__)

# Глобальный планировщик
_scheduler: Optional[AsyncIOScheduler] = None
_scheduler_shutdown: bool = False


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Получение экземпляра планировщика"""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=pytz.UTC)
    return _scheduler


async def init_scheduler() -> None:
    """Инициализация планировщика и восстановление постов"""
    global _scheduler_shutdown
    _scheduler_shutdown = False
    
    try:
        logger.info("Инициализация планировщика...")
        
        sched = get_scheduler()
        if sched and not sched.running:
            sched.start()
            logger.info("✅ Планировщик запущен")
        
        # Восстанавливаем отложенные посты
        await restore_pending_posts()
        
        # Запускаем YouTube мониторинг если доступен
        from core.config import YOUTUBE_AVAILABLE, YOUTUBE_API_KEY
        if YOUTUBE_AVAILABLE and YOUTUBE_API_KEY:
            from services.youtube_service import check_youtube_channels
            sched.add_job(
                check_youtube_channels, 
                trigger=IntervalTrigger(minutes=15),
                id="youtube_monitor", 
                replace_existing=True
            )
            logger.info("✅ Задача мониторинга YouTube добавлена (интервал: 15 минут)")
        
    except Exception as e:
        logger.error(f"Ошибка инициализации планировщика: {e}")


async def shutdown_scheduler() -> None:
    """Остановка планировщика"""
    global _scheduler, _scheduler_shutdown
    _scheduler_shutdown = True
    
    if _scheduler:
        _scheduler.remove_all_jobs()
        _scheduler = None
        logger.info("⏹️ Планировщик остановлен")


async def restore_pending_posts() -> None:
    """Восстановление отложенных постов после перезапуска"""
    pending_posts = schedule_repo.get_pending_posts()
    logger.info(f"📋 Найдено ожидающих постов: {len(pending_posts)}")
    
    now = datetime.now(pytz.UTC)
    restored_count = 0
    
    for post in pending_posts:
        post_id = post[0]
        scheduled_time_str = post[9]  # scheduled_time
        is_regular = bool(post[14]) if len(post) > 14 else False
        
        try:
            scheduled_time = datetime.fromisoformat(scheduled_time_str)
            
            # Если время уже прошло, переносим на +5 минут
            if scheduled_time < now:
                new_time = now + timedelta(minutes=5)
                schedule_repo.update_scheduled_time(post_id, new_time.isoformat())
                scheduled_time = new_time
                logger.info(f"⏰ Перенесён пост #{post_id} на {new_time}")
            
            schedule_post(post_id, scheduled_time)
            restored_count += 1
            logger.info(f"📅 Восстановлен пост #{post_id} на {scheduled_time}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка восстановления поста #{post_id}: {e}")
    
    logger.info(f"🔄 Восстановлено постов: {restored_count}")


def schedule_post(post_id: int, scheduled_time: datetime) -> None:
    """Добавление поста в планировщик"""
    global _scheduler_shutdown
    
    if _scheduler_shutdown:
        logger.warning(f"⚠️ Планировщик выключен, пост #{post_id} не добавлен")
        return
    
    trigger = DateTrigger(run_date=scheduled_time)
    sched = get_scheduler()
    
    if sched:
        sched.add_job(
            execute_scheduled_post, 
            trigger=trigger, 
            args=[post_id],
            id=f"post_{post_id}", 
            replace_existing=True, 
            misfire_grace_time=60
        )
        logger.info(f"📅 Пост #{post_id} запланирован на {scheduled_time}")


async def execute_scheduled_post(post_id: int) -> None:
    """Выполнение отложенного поста"""
    global _scheduler_shutdown
    
    if _scheduler_shutdown:
        logger.warning(f"⚠️ Планировщик выключен, пост #{post_id} пропущен")
        return
    
    logger.info(f"🚀 НАЧАЛО ВЫПОЛНЕНИЯ ПОСТА #{post_id}")
    
    # Получаем данные поста
    post = schedule_repo.get_post_by_id(post_id)
    
    if not post:
        logger.warning(f"⚠️ Пост #{post_id} не найден")
        return
    
    current_status = post[10]  # status
    if current_status != 'pending':
        logger.info(f"⏭️ Пост #{post_id} имеет статус '{current_status}', пропускаем")
        return
    
    user_id = post[1]
    channels = post[2]  # JSON строка
    post_text = post[3]
    media_path = post[4]
    media_name = post[5]
    media_size = post[6]
    media_type = post[7]
    button = post[8]  # JSON строка
    is_regular = bool(post[14]) if len(post) > 14 and post[14] is not None else 0
    regular_settings = post[15] if len(post) > 15 else None
    
    # Парсим JSON
    import json
    channels_list = json.loads(channels) if channels else []
    button_dict = json.loads(button) if button else None
    regular_settings_dict = json.loads(regular_settings) if regular_settings else None
    
    try:
        # Обновляем статус на "processing"
        schedule_repo.update_status(post_id, 'processing')
        
        # Создаём сессию для отправки
        session = {
            "user_id": user_id,
            "channels": channels_list,
            "post_text": post_text,
            "media_path": media_path,
            "media_name": media_name,
            "media_size": media_size,
            "media_type": media_type,
            "button": button_dict,
            "publishing": True
        }
        
        import uuid
        temp_session_id = str(uuid.uuid4())
        POST_SESSIONS[temp_session_id] = session
        
        # Отправляем пост
        results = await asyncio.wait_for(
            send_post_async(temp_session_id, session), 
            timeout=300
        )
        
        # Обрабатываем результат
        if is_regular:
            await handle_regular_post_result(
                post_id, results, user_id, channels_list, post_text,
                media_path, media_name, media_size, media_type,
                button_dict, regular_settings_dict
            )
        else:
            if results.get("failed", 0) == 0:
                schedule_repo.update_status(post_id, 'success', datetime.now().isoformat())
            else:
                schedule_repo.update_status(
                    post_id, 'partial', datetime.now().isoformat(),
                    f"Успешно: {results['success']}, Ошибок: {results['failed']}"
                )
            
            # Удаляем медиафайл для обычного поста
            if media_path:
                delete_media_file(media_path)
        
        # Очищаем сессию
        if temp_session_id in POST_SESSIONS:
            del POST_SESSIONS[temp_session_id]
        
    except asyncio.TimeoutError:
        logger.error(f"⏰ ТАЙМАУТ при выполнении поста #{post_id}")
        schedule_repo.update_status(post_id, 'error', datetime.now().isoformat(), "Timeout при отправке")
        
        if not is_regular and media_path:
            delete_media_file(media_path)
            
    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА выполнения поста #{post_id}: {e}")
        schedule_repo.update_status(post_id, 'error', datetime.now().isoformat(), str(e))
        
        if not is_regular and media_path:
            delete_media_file(media_path)


async def handle_regular_post_result(post_id: int, results: Dict, user_id: int,
                                      channels_list: list, post_text: str,
                                      media_path: str, media_name: str,
                                      media_size: float, media_type: str,
                                      button_dict: Dict, regular_settings: Dict) -> None:
    """Обработка результата регулярного поста и создание следующего"""
    import json
    
    if results.get("failed", 0) == 0:
        interval_hours = regular_settings.get("interval_hours", 24) if regular_settings else 24
        end_date = regular_settings.get("end_date") if regular_settings else None
        end_time = regular_settings.get("end_time") if regular_settings else None
        
        # Получаем текущее время поста
        post = schedule_repo.get_post_by_id(post_id)
        if not post:
            return
        
        current_time = datetime.fromisoformat(post[9])  # scheduled_time
        next_time = current_time + timedelta(hours=interval_hours)
        
        # Проверяем, нужно ли продолжать
        should_continue = True
        if end_date:
            local_tz = pytz.timezone(TIMEZONE)
            if end_time:
                end_datetime_str = f"{end_date} {end_time}"
                end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
                end_datetime = local_tz.localize(end_datetime)
            else:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
                end_datetime = local_tz.localize(end_datetime.replace(hour=23, minute=59))
            
            if next_time.tzinfo is None:
                next_time = local_tz.localize(next_time)
            
            if next_time > end_datetime:
                should_continue = False
        
        if should_continue:
            # Создаём следующий пост
            new_post_id = schedule_repo.save_post(
                user_id, channels_list, post_text,
                media_path, media_name, media_size, media_type,
                button_dict, next_time.isoformat(),
                is_regular=True, regular_settings=regular_settings
            )
            
            if new_post_id:
                schedule_post(new_post_id, next_time)
                logger.info(f"🔄 Создан следующий регулярный пост #{new_post_id} на {next_time}")
        
        schedule_repo.update_status(post_id, 'success', datetime.now().isoformat())
    else:
        schedule_repo.update_status(
            post_id, 'error', datetime.now().isoformat(),
            f"Ошибка: {results.get('failed')} каналов не отвечают"
        )


async def check_youtube_channels_wrapper():
    """Обёртка для проверки YouTube каналов (импортируется из youtube_service)"""
    from services.youtube_service import check_youtube_channels
    await check_youtube_channels()