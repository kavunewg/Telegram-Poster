"""
Репозиторий для работы с YouTube каналами
"""
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from core.database import get_db_connection
from repositories.base_repo import BaseRepository


class YouTubeRepository(BaseRepository):
    def __init__(self):
        super().__init__("youtube_channels")
    
    def add_channel(self, user_id: int, youtube_channel_id: str, youtube_channel_name: str,
                    youtube_channel_url: str, target_channels: List[Dict],
                    post_template: str = None, include_description: int = 0,
                    button_url: str = None, button_style: str = 'success') -> Optional[int]:
        """Добавление YouTube канала для мониторинга"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO youtube_channels 
                    (user_id, youtube_channel_id, youtube_channel_name, youtube_channel_url, 
                     target_channels, post_template, include_description, button_url, button_style, created_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    youtube_channel_id,
                    youtube_channel_name,
                    youtube_channel_url,
                    json.dumps(target_channels, ensure_ascii=False),
                    post_template,
                    include_description,
                    button_url,
                    button_style,
                    datetime.now().isoformat(),
                    1
                ))
                conn.commit()
                return cursor.lastrowid
            except Exception as e:
                print(f"Ошибка добавления YouTube канала: {e}")
                return None
    
    def get_user_channels(self, user_id: int) -> List[Dict]:
        """Получение всех YouTube каналов пользователя"""
        from core.database import get_db_connection
        import json
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, youtube_channel_id, youtube_channel_name, 
                    youtube_channel_url, target_channels, post_template,
                    include_description, last_video_id, last_checked, 
                    is_active, created_at, button_url, button_style
                FROM youtube_channels
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            
            channels = []
            for row in rows:
                channel = dict(row)
                
                # Парсим target_channels (может быть строкой JSON или уже списком)
                target_data = channel.get('target_channels')
                if target_data:
                    try:
                        if isinstance(target_data, str):
                            channel['target_channels'] = json.loads(target_data)
                        # Если уже список или словарь, оставляем как есть
                    except:
                        channel['target_channels'] = []
                else:
                    channel['target_channels'] = []
                
                channels.append(channel)
            
            return channels
    
    def update_last_video(self, channel_id: int, video_id: str) -> bool:
        """Обновление ID последнего видео"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE youtube_channels 
                SET last_video_id = ?, last_checked = ?
                WHERE id = ?
            ''', (video_id, datetime.now().isoformat(), channel_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def toggle_active(self, channel_id: int, user_id: int, is_active: bool) -> bool:
        """Включение/выключение мониторинга"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE youtube_channels 
                SET is_active = ?
                WHERE id = ? AND user_id = ?
            ''', (1 if is_active else 0, channel_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def update_channel(self, channel_id: int, user_id: int, target_channels: List[Dict],
                       post_template: str = None, include_description: int = 0,
                       button_url: str = None, button_style: str = 'success') -> bool:
        """Обновление настроек YouTube канала"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE youtube_channels 
                SET target_channels = ?, post_template = ?, include_description = ?,
                    button_url = ?, button_style = ?
                WHERE id = ? AND user_id = ?
            ''', (
                json.dumps(target_channels, ensure_ascii=False),
                post_template,
                include_description,
                button_url,
                button_style,
                channel_id,
                user_id
            ))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_active_channels(self) -> List[Tuple]:
        """Получение всех активных YouTube каналов для мониторинга"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT yc.id, yc.user_id, yc.youtube_channel_id, yc.youtube_channel_name, 
                       yc.target_channels, yc.post_template, yc.include_description, yc.last_video_id,
                       u.youtube_api_key, yc.button_url, yc.button_style
                FROM youtube_channels yc
                JOIN users u ON yc.user_id = u.id
                WHERE yc.is_active = 1
            ''')
            return cursor.fetchall()
    
    def get_channel_by_id(self, channel_id: int, user_id: int):
        """Получение YouTube канала по ID"""
        from core.database import get_db_connection
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, youtube_channel_id, youtube_channel_name, youtube_channel_url,
                    target_channels, post_template, include_description,
                    last_video_id, last_checked, is_active, created_at,
                    button_url, button_style
                FROM youtube_channels
                WHERE id = ? AND user_id = ?
            """, (channel_id, user_id))
            row = cursor.fetchone()
            if row:
                return dict(row)  # Сразу возвращаем словарь
            return None


# Глобальный экземпляр
youtube_repo = YouTubeRepository()

def get_active_channels(self) -> List[Tuple]:
    """Получение всех активных YouTube каналов для мониторинга"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT yc.id, yc.user_id, yc.youtube_channel_id, yc.youtube_channel_name, 
                   yc.target_channels, yc.post_template, yc.include_description, yc.last_video_id,
                   u.youtube_api_key, yc.button_url, yc.button_style
            FROM youtube_channels yc
            JOIN users u ON yc.user_id = u.id
            WHERE yc.is_active = 1
        ''')
        return cursor.fetchall()