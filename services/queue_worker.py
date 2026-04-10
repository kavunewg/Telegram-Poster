"""
Воркер для обработки очереди
"""
import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List

from repositories.queue_repo import queue_repo
from core.config import POST_SESSIONS
from services.media_service import delete_media_file

logger = logging.getLogger(__name__)


class QueueWorker:
    """Воркер для обработки очереди"""
    
    def __init__(self, interval: int = 3, max_retries: int = 3, batch_size: int = 5):
        self.interval = interval
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.running = False
        self.repo = queue_repo
        self._task: Optional[asyncio.Task] = None
        self.stats = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'errors': 0
        }
    
    async def start(self):
        """Запуск воркера"""
        self.running = True
        logger.info("🚀 QueueWorker запущен")
        logger.info(f"   Интервал: {self.interval}с, Максимум попыток: {self.max_retries}, Размер пакета: {self.batch_size}")
        
        while self.running:
            try:
                await self._process_batch()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                logger.info("QueueWorker получил сигнал остановки")
                break
            except Exception as e:
                logger.error(f"❌ Worker error: {e}")
                traceback.print_exc()
                await asyncio.sleep(5)
        
        # Выводим финальную статистику
        logger.info(f"📊 Финальная статистика: обработано {self.stats['processed']}, "
                   f"успешно {self.stats['success']}, ошибок {self.stats['failed']}")
        logger.info("🛑 QueueWorker остановлен")
    
    async def stop(self):
        """Остановка воркера"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _process_batch(self):
        """Обработка пакета задач"""
        try:
            tasks = self.repo.get_pending_tasks(limit=self.batch_size)
            
            if not tasks:
                return
            
            logger.info(f"📋 Найдено задач: {len(tasks)}")
            
            # Обрабатываем задачи параллельно с ограничением
            semaphore = asyncio.Semaphore(3)  # Не более 3 задач одновременно
            
            async def process_with_limit(task):
                async with semaphore:
                    await self._handle_task(task)
            
            await asyncio.gather(*[process_with_limit(task) for task in tasks])
                
        except Exception as e:
            logger.error(f"Ошибка обработки пакета: {e}")
            traceback.print_exc()
    
    async def _handle_task(self, task: Dict[str, Any]):
        """Обработка одной задачи"""
        task_id = task['id']
        user_id = task['user_id']
        platform = task['platform']
        action = task['action']
        payload = task['payload']
        attempts = task.get('attempts', 0)
        
        logger.info(f"=" * 50)
        logger.info(f"📤 Обработка задачи {task_id}")
        logger.info(f"   Платформа: {platform}")
        logger.info(f"   Действие: {action}")
        logger.info(f"   Попытка: {attempts + 1}/{self.max_retries}")
        logger.info(f"=" * 50)
        
        start_time = datetime.now()
        
        try:
            # Обновляем статус на processing
            self.repo.update_task_status(task_id, 'processing')
            
            # Обработка в зависимости от платформы и действия
            if action == 'send_post':
                if platform == 'telegram':
                    result = await self._send_telegram(payload)
                elif platform == 'max':
                    result = await self._send_max(payload)
                elif platform == 'vk':
                    result = await self._send_vk(payload)
                else:
                    result = {'success': False, 'error': f'Unknown platform: {platform}'}
            else:
                result = {'success': False, 'error': f'Unknown action: {action}'}
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if result.get('success'):
                # Успешно
                self.repo.update_task_status(task_id, 'success')
                self.stats['success'] += 1
                logger.info(f"✅ Задача {task_id} выполнена успешно за {elapsed:.2f}с")
                self._update_progress(user_id, task_id, True, payload.get('post_session_id'))
            else:
                # Ошибка
                error_msg = result.get('error', 'Unknown error')
                await self._handle_error(task_id, attempts, error_msg, user_id, payload.get('post_session_id'))
                
        except asyncio.CancelledError:
            logger.warning(f"⚠️ Задача {task_id} отменена при остановке")
            raise
        except Exception as e:
            logger.error(f"❌ Критическая ошибка при обработке задачи {task_id}: {e}")
            traceback.print_exc()
            await self._handle_error(task_id, attempts, str(e), user_id, payload.get('post_session_id'))
        finally:
            self.stats['processed'] += 1


    async def _send_vk(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Отправка в VK"""
        try:
            from services.post_service import send_to_vk as send_vk
            
            # Извлекаем данные из payload
            bot_token = payload.get('bot_token') or payload.get('channel', {}).get('bot_token')
            channel_id = payload.get('channel_id') or payload.get('channel', {}).get('channel_id')
            text = payload.get('text', '')
            button = payload.get('button')
            media_path = payload.get('media_path')
            media_name = payload.get('media_name')
            media_size = payload.get('media_size')
            media_type = payload.get('media_type', 'text')
            
            logger.info(f"🔍 Отправка в VK:")
            logger.info(f"   bot_token: {bot_token[:20] if bot_token else 'None'}...")
            logger.info(f"   channel_id: {channel_id}")
            logger.info(f"   text length: {len(text) if text else 0}")
            
            # Если нет токена, ищем в БД
            if not bot_token:
                from repositories.bot_repo import bot_repo
                user_id = payload.get('user_id')
                if user_id:
                    bots = bot_repo.get_user_bots(user_id)
                    for bot in bots:
                        if bot.get('platform') == 'vk':
                            bot_token = bot.get('token')
                            logger.info(f"🔍 Найден VK бот в БД: {bot_token[:20] if bot_token else 'None'}...")
                            break
            
            if not bot_token:
                error_msg = 'VK token not found. Please add a VK bot in "My Bots" page.'
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            if not channel_id:
                error_msg = 'VK group ID not found'
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            if not text:
                error_msg = 'Post text is empty'
                logger.error(error_msg)
                return {'success': False, 'error': error_msg}
            
            # Создаём сессию для отправки
            session = {
                'user_id': payload.get('user_id'),
                'channel_db_id': payload.get('channel_db_id'),
                'channel_id': channel_id,
                'channel_name': payload.get('channel', {}).get('name', 'Unknown'),
                'platform': 'vk',
                'post_text': text,
                'media_path': media_path,
                'media_name': media_name,
                'media_size': media_size,
                'media_type': media_type,
                'button': button,
                'bot_token': bot_token
            }
            
            # Отправляем с таймаутом
            result = await asyncio.wait_for(
                send_vk(session, str(payload.get('channel_db_id', 'unknown'))),
                timeout=60
            )
            
            if result and result.get('success'):
                logger.info(f"✅ Пост успешно отправлен в VK")
                return {'success': True, 'result': result}
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ Ошибка VK: {error_msg}")
                return {'success': False, 'error': error_msg}
            
        except asyncio.TimeoutError:
            logger.error(f"VK send timeout (60s)")
            return {'success': False, 'error': 'Request timeout (60s)'}
        except Exception as e:
            logger.error(f"VK send error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    async def _handle_error(self, task_id: int, attempts: int, error_msg: str, user_id: int, post_session_id: str = None):
        """Обработка ошибки задачи"""
        new_attempts = attempts + 1
        logger.error(f"❌ Ошибка задачи {task_id}: {error_msg}")
        
        if new_attempts >= self.max_retries:
            # Превышено количество попыток
            self.repo.update_task_status(task_id, 'failed', error_msg, new_attempts)
            self.stats['failed'] += 1
            logger.error(f"❌ Задача {task_id} окончательно провалена после {new_attempts} попыток")
            self._update_progress(user_id, task_id, False, post_session_id)
            
            # Отправляем уведомление об ошибке (опционально)
            await self._notify_error(user_id, task_id, error_msg)
        else:
            # Повторная попытка с задержкой (экспоненциальная)
            delay = 2 ** new_attempts  # 2, 4, 8 секунд
            self.repo.update_task_status(task_id, 'retry', error_msg, new_attempts)
            logger.warning(f"⚠️ Задача {task_id} будет повторена через {delay}с (попытка {new_attempts + 1}/{self.max_retries})")
            
            # Откладываем повторную обработку
            asyncio.create_task(self._delayed_retry(task_id, delay))
    
    async def _delayed_retry(self, task_id: int, delay: int):
        """Отложенный повтор задачи"""
        await asyncio.sleep(delay)
        # Статус уже 'retry', воркер подхватит при следующем цикле
        logger.info(f"🔄 Задача {task_id} готова к повтору")
    
    async def _send_telegram(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Отправка в Telegram"""
        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            from services.post_service import send_to_telegram as send_tg
            
            # Извлекаем данные из payload
            bot_token = payload.get('bot_token') or payload.get('channel', {}).get('bot_token')
            channel_id = payload.get('channel_id') or payload.get('channel', {}).get('channel_id')
            text = payload.get('text', '')
            button = payload.get('button')
            media_path = payload.get('media_path')
            
            logger.info(f"🔍 Отправка в Telegram:")
            logger.info(f"   bot_token: {bot_token[:20] if bot_token else 'None'}...")
            logger.info(f"   channel_id: {channel_id}")
            logger.info(f"   text length: {len(text) if text else 0}")
            if button:
                logger.info(f"   button: {button.get('text', 'No text')} (style: {button.get('style', 'default')})")
            
            if not bot_token:
                # Пытаемся найти бота в базе данных
                from repositories.bot_repo import bot_repo
                user_id = payload.get('user_id')
                
                if user_id:
                    bots = bot_repo.get_user_bots(user_id)
                    for bot in bots:
                        if bot.get('platform') == 'telegram':
                            bot_token = bot.get('token')
                            logger.info(f"🔍 Найден бот в БД: {bot_token[:20] if bot_token else 'None'}...")
                            break
                
                if not bot_token:
                    return {'success': False, 'error': 'Bot token not found. Please add a Telegram bot in "My Bots" page.'}
            
            if not channel_id:
                return {'success': False, 'error': 'Channel ID not found'}
            
            if not text:
                return {'success': False, 'error': 'Post text is empty'}
            
            # Создаём сессию для отправки
            session = {
                'user_id': payload.get('user_id'),
                'channel_db_id': payload.get('channel_db_id'),
                'channel_id': channel_id,
                'channel_name': payload.get('channel', {}).get('name', 'Unknown'),
                'platform': 'telegram',
                'post_text': text,
                'media_path': media_path,
                'media_name': payload.get('media_name'),
                'media_size': payload.get('media_size'),
                'media_type': payload.get('media_type', 'text'),
                'button': button,
                'bot_token': bot_token
            }
            
            # Добавляем таймаут
            result = await asyncio.wait_for(
                send_tg(session, str(payload.get('channel_db_id', 'unknown'))),
                timeout=60
            )
            
            if result and result.get('success'):
                return {'success': True, 'result': result}
            else:
                return {'success': False, 'error': result.get('error', 'Unknown error')}
            
        except asyncio.TimeoutError:
            logger.error(f"Telegram send timeout (60s)")
            return {'success': False, 'error': 'Request timeout (60s)'}
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}
    
    async def _send_max(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Отправка в MAX"""
        try:
            from services.post_service import send_to_max as send_max
            
            result = await asyncio.wait_for(
                send_max(payload, "queue"),
                timeout=30
            )
            return {'success': True, 'result': result}
        except asyncio.TimeoutError:
            logger.error(f"MAX send timeout (30s)")
            return {'success': False, 'error': 'Request timeout (30s)'}
        except Exception as e:
            logger.error(f"MAX send error: {e}")
            return {'success': False, 'error': str(e)}    def _update_progress(self, user_id: int, task_id: int, success: bool, post_session_id: str = None):
        """Обновление прогресса в сессии"""
        target_session_id = post_session_id
        target_session = POST_SESSIONS.get(target_session_id) if target_session_id else None

        if target_session is None:
            for session_id, session in POST_SESSIONS.items():
                if session.get('user_id') == user_id and session.get('publishing'):
                    target_session_id = session_id
                    target_session = session
                    break

        if target_session is None:
            return

        if success:
            target_session['results']['success'] = target_session['results'].get('success', 0) + 1
        else:
            target_session['results']['failed'] = target_session['results'].get('failed', 0) + 1

        target_session['completed_count'] = target_session.get('completed_count', 0) + 1
        total = len(target_session.get('channels', []))
        completed = target_session.get('completed_count', 0)
        target_session['progress'] = int((completed / total) * 100) if total > 0 else 0

        if completed >= total:
            target_session['publishing'] = False
            media_path = target_session.get('media_path')
            if media_path:
                try:
                    delete_media_file(media_path)
                except Exception as exc:
                    logger.warning(f"Не удалось удалить media после завершения сессии {target_session_id}: {exc}")
            logger.info(
                f"📊 Сессия {target_session_id} завершена: "
                f"успешно {target_session['results']['success']}, "
                f"ошибок {target_session['results']['failed']}"
            )

    async def _notify_error(self, user_id: int, task_id: int, error_msg: str):
        """Уведомление об ошибке (можно расширить)"""
        logger.warning(f"📧 Уведомление об ошибке для пользователя {user_id}, задача {task_id}: {error_msg[:100]}")
        # TODO: Отправить уведомление пользователю (email, telegram, etc.)
    
    async def get_stats(self) -> Dict[str, int]:
        """Получить статистику работы воркера"""
        return {
            'processed': self.stats['processed'],
            'success': self.stats['success'],
            'failed': self.stats['failed'],
            'errors': self.stats['errors'],
            'is_running': self.running
        }
    
    async def reset_stats(self):
        """Сбросить статистику"""
        self.stats = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'errors': 0
        }
        logger.info("📊 Статистика воркера сброшена")


# Глобальный экземпляр воркера
queue_worker = QueueWorker(interval=3, max_retries=3, batch_size=5)


# Функции для управления воркером
async def start_queue_worker():
    """Запуск воркера"""
    asyncio.create_task(queue_worker.start())


async def stop_queue_worker():
    """Остановка воркера"""
    await queue_worker.stop()


async def get_worker_stats():
    """Получить статистику воркера"""
    return await queue_worker.get_stats()

