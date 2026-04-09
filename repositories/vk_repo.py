"""
Репозиторий для работы с VK каналами
"""
import json
from datetime import datetime
from typing import List, Dict, Optional

from core.database import get_db_connection, fetch_one, fetch_all, execute, insert


class VKRepository:
    """Репозиторий для работы с VK"""
    
    def __init__(self):
        self._init_table()
    
    def _init_table(self):
        """Инициализация таблиц VK"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица VK каналов (групп)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vk_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    group_id INTEGER NOT NULL,
                    group_name TEXT NOT NULL,
                    group_screen_name TEXT,
                    access_token TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Таблица VK постов
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vk_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channel_id INTEGER,
                    post_id INTEGER,
                    post_text TEXT,
                    media_path TEXT,
                    status TEXT DEFAULT 'pending',
                    error TEXT,
                    created_at TEXT,
                    published_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (channel_id) REFERENCES vk_channels(id) ON DELETE SET NULL
                )
            """)
            
            # Индексы
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vk_channels_user_id ON vk_channels(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vk_posts_user_id ON vk_posts(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vk_posts_status ON vk_posts(status)")
            
            conn.commit()
    
    def add_channel(self, user_id: int, group_id: int, group_name: str, 
                    group_screen_name: str, access_token: str) -> int:
        """Добавление VK канала"""
        now = datetime.now().isoformat()
        
        return insert("""
            INSERT INTO vk_channels (user_id, group_id, group_name, group_screen_name, 
                                      access_token, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, group_id, group_name, group_screen_name, access_token, now, now))
    
    def get_user_channels(self, user_id: int) -> List[Dict]:
        """Получение всех VK каналов пользователя"""
        return fetch_all("""
            SELECT id, group_id, group_name, group_screen_name, is_active, created_at
            FROM vk_channels
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
    
    def get_channel(self, channel_id: int, user_id: int) -> Optional[Dict]:
        """Получение VK канала по ID"""
        return fetch_one("""
            SELECT id, group_id, group_name, group_screen_name, access_token, is_active
            FROM vk_channels
            WHERE id = ? AND user_id = ?
        """, (channel_id, user_id))
    
    def delete_channel(self, channel_id: int, user_id: int) -> bool:
        """Удаление VK канала"""
        rows = execute("DELETE FROM vk_channels WHERE id = ? AND user_id = ?", (channel_id, user_id))
        return rows > 0
    
    def toggle_active(self, channel_id: int, user_id: int, is_active: bool) -> bool:
        """Включение/выключение канала"""
        rows = execute("""
            UPDATE vk_channels 
            SET is_active = ?, updated_at = ?
            WHERE id = ? AND user_id = ?
        """, (1 if is_active else 0, datetime.now().isoformat(), channel_id, user_id))
        return rows > 0
    
    def add_post(self, user_id: int, channel_id: int, post_text: str, 
                 media_path: str = None, publish_date: int = None) -> int:
        """Добавление поста в очередь VK"""
        now = datetime.now().isoformat()
        
        return insert("""
            INSERT INTO vk_posts (user_id, channel_id, post_text, media_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, channel_id, post_text, media_path, 'pending', now))
    
    def update_post_status(self, post_id: int, status: str, error: str = None, post_id_vk: int = None) -> bool:
        """Обновление статуса поста"""
        now = datetime.now().isoformat()
        
        if post_id_vk:
            rows = execute("""
                UPDATE vk_posts 
                SET status = ?, error = ?, post_id = ?, published_at = ?
                WHERE id = ?
            """, (status, error, post_id_vk, now, post_id))
        else:
            rows = execute("""
                UPDATE vk_posts 
                SET status = ?, error = ?
                WHERE id = ?
            """, (status, error, post_id))
        
        return rows > 0
    
    def get_pending_posts(self, limit: int = 10) -> List[Dict]:
        """Получение ожидающих постов"""
        return fetch_all("""
            SELECT vp.id, vp.user_id, vp.channel_id, vp.post_text, vp.media_path,
                   vc.access_token, vc.group_id, vc.group_name
            FROM vk_posts vp
            JOIN vk_channels vc ON vp.channel_id = vc.id
            WHERE vp.status = 'pending' AND vc.is_active = 1
            ORDER BY vp.created_at ASC
            LIMIT ?
        """, (limit,))
    
    def get_stats(self, user_id: int) -> Dict:
        """Получение статистики по VK постам"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM vk_posts WHERE user_id = ?", (user_id,))
            total = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vk_posts WHERE user_id = ? AND status = 'success'", (user_id,))
            success = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM vk_posts WHERE user_id = ? AND status = 'failed'", (user_id,))
            failed = cursor.fetchone()[0]
            
            return {
                'total': total,
                'success': success,
                'failed': failed
            }


vk_repo = VKRepository()