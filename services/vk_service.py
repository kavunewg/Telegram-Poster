"""
Сервис для работы с VK API
"""
import aiohttp
import asyncio
import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class VKAPIError(Exception):
    """Исключение для ошибок VK API"""
    def __init__(self, error_code: int, error_msg: str):
        self.error_code = error_code
        self.error_msg = error_msg
        super().__init__(f"VK API Error {error_code}: {error_msg}")


class VKService:
    """Сервис для работы с VK API"""
    
    API_VERSION = "5.199"
    API_URL = "https://api.vk.com/method/"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
    
    async def _request(self, method: str, params: Dict = None) -> Dict:
        """Выполнение запроса к VK API с обработкой ошибок"""
        url = f"{self.API_URL}{method}"
        params = params or {}
        params["access_token"] = self.access_token
        params["v"] = self.API_VERSION
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                
                if "error" in data:
                    error = data["error"]
                    raise VKAPIError(error.get("error_code", 0), error.get("error_msg", "Unknown error"))
                
                return data.get("response", {})
    
    # ========== РАБОТА С ФОТО ==========
    
    async def get_wall_upload_server(self, group_id: int) -> str:
        """Получение URL для загрузки фото на стену сообщества"""
        result = await self._request("photos.getWallUploadServer", {"group_id": group_id})
        return result["upload_url"]
    
    async def upload_photo(self, upload_url: str, photo_path: str) -> Dict:
        """Загрузка фото на полученный URL"""
        async with aiohttp.ClientSession() as session:
            with open(photo_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("photo", f, filename=os.path.basename(photo_path))
                
                async with session.post(upload_url, data=data) as resp:
                    return await resp.json()
    
    async def save_wall_photo(self, group_id: int, photo: str, server: int, hash_key: str) -> List[Dict]:
        """Сохранение загруженного фото на стене сообщества"""
        result = await self._request("photos.saveWallPhoto", {
            "group_id": group_id,
            "photo": photo,
            "server": server,
            "hash": hash_key
        })
        return result
    
    # ========== ПУБЛИКАЦИЯ ПОСТОВ ==========
    
    async def post_to_wall(
        self,
        owner_id: int,
        message: str,
        attachments: List[str] = None,
        from_group: bool = True,
        publish_date: int = None
    ) -> Dict:
        """Публикация поста на стену"""
        params = {
            "owner_id": owner_id,
            "from_group": 1 if from_group else 0,
            "message": message
        }
        
        if attachments:
            params["attachments"] = ",".join(attachments)
        
        if publish_date:
            params["publish_date"] = publish_date
        
        return await self._request("wall.post", params)
    
    # ========== РАБОТА С ГРУППАМИ ==========
    
    async def get_group_info(self, group_id: int) -> Dict:
        """Получение информации о группе"""
        result = await self._request("groups.getById", {
            "group_id": abs(group_id),
            "fields": "name,screen_name,photo_50"
        })
        
        if result and isinstance(result, list) and len(result) > 0:
            return result[0]
        return {}
    
    async def check_token(self) -> bool:
        """Проверка валидности токена"""
        try:
            await self._request("users.get")
            return True
        except VKAPIError:
            return False


class VKPostService:
    """Сервис для создания и отправки VK постов"""
    
    def __init__(self):
        self.vk_services = {}
    
    def get_service(self, access_token: str) -> VKService:
        """Получение сервиса VK по токену"""
        return VKService(access_token)
    
    async def send_post(
        self,
        access_token: str,
        group_id: int,
        message: str,
        media_path: str = None,
        publish_date: int = None,
        from_group: bool = True
    ) -> Dict:
        """Отправка поста в VK"""
        vk = VKService(access_token)
        attachments = []
        
        # Загрузка медиа если есть
        if media_path and os.path.exists(media_path):
            try:
                # Получаем сервер для загрузки
                upload_url = await vk.get_wall_upload_server(abs(group_id))
                
                # Загружаем фото
                uploaded = await vk.upload_photo(upload_url, media_path)
                
                # Сохраняем на стену
                saved = await vk.save_wall_photo(
                    abs(group_id),
                    uploaded.get("photo"),
                    uploaded.get("server"),
                    uploaded.get("hash")
                )
                
                if saved:
                    photo = saved[0]
                    attachments.append(f"photo{-group_id}_{photo['id']}")
                    
            except Exception as e:
                logger.error(f"Ошибка загрузки медиа в VK: {e}")
                # Продолжаем без медиа
        
        # Публикуем пост
        owner_id = -abs(group_id)  # Отрицательный ID для сообщества
        result = await vk.post_to_wall(
            owner_id=owner_id,
            message=message,
            attachments=attachments if attachments else None,
            from_group=from_group,
            publish_date=publish_date
        )
        
        return result


# Глобальный экземпляр
vk_post_service = VKPostService()