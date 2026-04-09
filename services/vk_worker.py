"""
Воркер для обработки VK постов
"""
import asyncio
import logging
from typing import Dict, Any

from repositories.vk_repo import vk_repo
from services.vk_service import vk_post_service, VKAPIError

logger = logging.getLogger(__name__)


class VKWorker:
    """Воркер для отправки постов в VK"""
    
    def __init__(self, interval: int = 5):
        self.interval = interval
        self.running = False
        self.repo = vk_repo
    
    async def start(self):
        """Запуск воркера"""
        self.running = True
        logger.info("🚀 VKWorker запущен")
        
        while self.running:
            try:
                await self._process_batch()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ VKWorker error: {e}")
                await asyncio.sleep(5)
    
    async def stop(self):
        """Остановка воркера"""
        self.running = False
        logger.info("🛑 VKWorker остановлен")
    
    async def _process_batch(self):
        """Обработка пакета постов"""
        posts = self.repo.get_pending_posts(limit=5)
        
        if not posts:
            return
        
        logger.info(f"📋 Найдено VK постов: {len(posts)}")
        
        for post in posts:
            await self._process_post(post)
    
    async def _process_post(self, post: Dict[str, Any]):
        """Обработка одного поста"""
        post_id = post["id"]
        access_token = post["access_token"]
        group_id = post["group_id"]
        message = post["post_text"]
        media_path = post.get("media_path")
        
        logger.info(f"📤 Отправка поста {post_id} в VK группу {post['group_name']}")
        
        try:
            result = await vk_post_service.send_post(
                access_token=access_token,
                group_id=group_id,
                message=message,
                media_path=media_path
            )
            
            vk_post_id = result.get("post_id")
            self.repo.update_post_status(post_id, "success", post_id_vk=vk_post_id)
            logger.info(f"✅ Пост {post_id} успешно отправлен в VK (ID: {vk_post_id})")
            
        except VKAPIError as e:
            error_msg = f"VK API Error {e.error_code}: {e.error_msg}"
            logger.error(f"❌ Ошибка VK API для поста {post_id}: {error_msg}")
            self.repo.update_post_status(post_id, "failed", error=error_msg)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Ошибка отправки поста {post_id}: {error_msg}")
            self.repo.update_post_status(post_id, "failed", error=error_msg)


# Глобальный экземпляр
vk_worker = VKWorker()


async def start_vk_worker():
    """Запуск воркера"""
    asyncio.create_task(vk_worker.start())


async def stop_vk_worker():
    """Остановка воркера"""
    await vk_worker.stop()