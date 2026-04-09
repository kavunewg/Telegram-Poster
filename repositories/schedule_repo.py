"""
Репозиторий для работы с отложенными постами
"""
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any

from core.database import get_db_connection, fetch_one, fetch_all, execute, insert


class ScheduleRepository:
    def __init__(self):
        self._init_table()
    
    def _init_table(self):
        """Инициализация таблицы отложенных постов"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Создаём таблицу если её нет
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    channels TEXT,
                    post_text TEXT,
                    media_path TEXT,
                    media_name TEXT,
                    media_size INTEGER,
                    media_type TEXT,
                    button TEXT,
                    scheduled_at TEXT,
                    is_regular INTEGER DEFAULT 0,
                    regular_settings TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Проверяем и добавляем недостающие колонки
            cursor.execute("PRAGMA table_info(scheduled_posts)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'scheduled_at' not in columns:
                cursor.execute("ALTER TABLE scheduled_posts ADD COLUMN scheduled_at TEXT")
                print("✓ Добавлена колонка scheduled_at в scheduled_posts")
            
            if 'updated_at' not in columns:
                cursor.execute("ALTER TABLE scheduled_posts ADD COLUMN updated_at TEXT")
                print("✓ Добавлена колонка updated_at в scheduled_posts")
            
            # Создаём индексы
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_posts_user_id ON scheduled_posts(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_posts_scheduled_at ON scheduled_posts(scheduled_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status ON scheduled_posts(status)")
            
            conn.commit()
    
    def save_post(self, user_id: int, channels: List, post_text: str, 
                  media_path: str, media_name: str, media_size: int, 
                  media_type: str, button: dict, scheduled_at: str,
                  is_regular: bool = False, regular_settings: dict = None) -> int:
        """Сохранение отложенного поста"""
        now = datetime.now().isoformat()
        
        return insert("""
            INSERT INTO scheduled_posts (
                user_id, channels, post_text, media_path, media_name,
                media_size, media_type, button, scheduled_at, is_regular,
                regular_settings, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            json.dumps(channels, ensure_ascii=False),
            post_text,
            media_path,
            media_name,
            media_size,
            media_type,
            json.dumps(button, ensure_ascii=False) if button else None,
            scheduled_at,
            1 if is_regular else 0,
            json.dumps(regular_settings, ensure_ascii=False) if regular_settings else None,
            'pending',
            now
        ))
    
    def get_user_scheduled_posts(self, user_id: int) -> List[Dict]:
        """Получение всех отложенных постов пользователя"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, channels, post_text, media_path, media_name,
                       media_size, media_type, button, scheduled_at, is_regular,
                       regular_settings, status, created_at
                FROM scheduled_posts
                WHERE user_id = ?
                ORDER BY scheduled_at ASC
            """, (user_id,))
            rows = cursor.fetchall()
            
            posts = []
            for row in rows:
                post = dict(row)
                # Парсим JSON поля
                if post.get('channels'):
                    try:
                        post['channels'] = json.loads(post['channels'])
                    except:
                        post['channels'] = []
                
                if post.get('button'):
                    try:
                        post['button'] = json.loads(post['button'])
                    except:
                        post['button'] = None
                
                if post.get('regular_settings'):
                    try:
                        post['regular_settings'] = json.loads(post['regular_settings'])
                    except:
                        post['regular_settings'] = {}
                
                # Форматируем дату для отображения
                if post.get('scheduled_at'):
                    try:
                        dt = datetime.fromisoformat(post['scheduled_at'])
                        post['scheduled_time_formatted'] = dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        post['scheduled_time_formatted'] = post['scheduled_at']
                
                posts.append(post)
            
            return posts
    
    def get_post_by_id(self, post_id: int, user_id: int) -> Optional[Dict]:
        """Получение поста по ID"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, channels, post_text, media_path, media_name,
                       media_size, media_type, button, scheduled_at, is_regular,
                       regular_settings, status, created_at
                FROM scheduled_posts
                WHERE id = ? AND user_id = ?
            """, (post_id, user_id))
            row = cursor.fetchone()
            
            if row:
                post = dict(row)
                # Парсим JSON поля
                if post.get('channels'):
                    try:
                        post['channels'] = json.loads(post['channels'])
                    except:
                        post['channels'] = []
                
                if post.get('button'):
                    try:
                        post['button'] = json.loads(post['button'])
                    except:
                        post['button'] = None
                
                if post.get('regular_settings'):
                    try:
                        post['regular_settings'] = json.loads(post['regular_settings'])
                    except:
                        post['regular_settings'] = {}
                
                return post
            
            return None
    
    def update_post(self, post_id: int, user_id: int, channels: List, post_text: str,
                    media_path: str, media_name: str, media_size: int, media_type: str,
                    button: dict, scheduled_at: str, is_regular: bool, regular_settings: dict) -> bool:
        """Обновление поста"""
        now = datetime.now().isoformat()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE scheduled_posts 
                SET channels = ?, post_text = ?, media_path = ?, media_name = ?,
                    media_size = ?, media_type = ?, button = ?, scheduled_at = ?,
                    is_regular = ?, regular_settings = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
            """, (
                json.dumps(channels, ensure_ascii=False),
                post_text,
                media_path,
                media_name,
                media_size,
                media_type,
                json.dumps(button, ensure_ascii=False) if button else None,
                scheduled_at,
                1 if is_regular else 0,
                json.dumps(regular_settings, ensure_ascii=False) if regular_settings else None,
                now,
                post_id,
                user_id
            ))
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_post(self, post_id: int) -> bool:
        """Удаление поста"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_stats(self, user_id: int) -> Dict:
        """Получение статистики по отложенным постам"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Всего постов
            cursor.execute("SELECT COUNT(*) FROM scheduled_posts WHERE user_id = ?", (user_id,))
            total = cursor.fetchone()[0]
            
            # По статусам
            cursor.execute("SELECT status, COUNT(*) FROM scheduled_posts WHERE user_id = ? GROUP BY status", (user_id,))
            status_stats = cursor.fetchall()
            
            pending = 0
            processing = 0
            success = 0
            error = 0
            
            for status, count in status_stats:
                if status == 'pending':
                    pending = count
                elif status == 'processing':
                    processing = count
                elif status == 'success':
                    success = count
                elif status == 'error' or status == 'failed':
                    error = count
            
            return {
                'total': total,
                'pending': pending,
                'processing': processing,
                'success': success,
                'error': error
            }


schedule_repo = ScheduleRepository()