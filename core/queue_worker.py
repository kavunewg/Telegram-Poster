"""
Модуль для управления воркером очереди
"""
import asyncio
from services.queue_worker import queue_worker

_worker_task = None


async def start_queue_worker():
    """Запуск воркера очереди"""
    global _worker_task
    if _worker_task is None:
        _worker_task = asyncio.create_task(queue_worker.start())


async def stop_queue_worker():
    """Остановка воркера очереди"""
    global _worker_task
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None