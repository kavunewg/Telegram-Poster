"""
Репозиторий для работы с очередью
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.config import DB_PATH


class QueueRepository:
    def __init__(self):
        self._init_table()
    
    def _init_table(self):
        """Инициализация таблицы очереди - проверяем структуру"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Проверяем существование таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='post_queue'")
            exists = cursor.fetchone()
            
            if not exists:
                # Создаём таблицу с нуля
                cursor.execute("""
                    CREATE TABLE post_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        channel_id INTEGER,
                        platform TEXT DEFAULT 'telegram',
                        action TEXT DEFAULT 'send_post',
                        payload TEXT,
                        status TEXT DEFAULT 'pending',
                        attempts INTEGER DEFAULT 0,
                        error TEXT,
                        created_at TEXT,
                        scheduled_at TEXT
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_queue_user_id ON post_queue(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_post_queue_status ON post_queue(status)")
                conn.commit()
                print("✓ Таблица post_queue создана")
    
    def create_task(
        self,
        user_id: int,
        channel_id: int,
        platform: str,
        action: str,
        payload: dict,
        scheduled_at: str = None
    ) -> int:
        """Создание задачи в очереди"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO post_queue (
                    user_id, channel_id, platform, action, payload,
                    status, attempts, created_at, scheduled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                channel_id,
                platform,
                action,
                json.dumps(payload, ensure_ascii=False),
                'pending',
                0,
                now,
                scheduled_at or now
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_pending_tasks(self, limit: int = 10) -> List[Dict]:
        """Получение ожидающих задач"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, channel_id, platform, action, payload,
                       status, attempts, error, created_at, scheduled_at
                FROM post_queue
                WHERE status IN ('pending', 'retry')
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            
            tasks = []
            for row in rows:
                try:
                    payload = json.loads(row[5]) if row[5] else {}
                except:
                    payload = {}
                
                tasks.append({
                    'id': row[0],
                    'user_id': row[1],
                    'channel_id': row[2],
                    'platform': row[3],
                    'action': row[4],
                    'payload': payload,
                    'status': row[6],
                    'attempts': row[7],
                    'error': row[8],
                    'created_at': row[9],
                    'scheduled_at': row[10]
                })
            return tasks
    
    def update_task_status(
        self,
        task_id: int,
        status: str,
        error: str = None,
        attempts: int = None
    ) -> bool:
        """Обновление статуса задачи"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            if attempts is not None:
                cursor.execute("""
                    UPDATE post_queue
                    SET status = ?, error = ?, attempts = ?
                    WHERE id = ?
                """, (status, error, attempts, task_id))
            else:
                cursor.execute("""
                    UPDATE post_queue
                    SET status = ?, error = ?
                    WHERE id = ?
                """, (status, error, task_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_user_queue(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Получение очереди пользователя"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, status, attempts, error, created_at,
                       json_extract(payload, '$.text') as text,
                       json_extract(payload, '$.channel.name') as channel_name
                FROM post_queue
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            rows = cursor.fetchall()
            
            tasks = []
            for row in rows:
                tasks.append({
                    'id': row[0],
                    'status': row[1],
                    'attempts': row[2],
                    'error': row[3],
                    'created_at': row[4],
                    'text': row[5] or '',
                    'channel': row[6] or 'Unknown'
                })
            return tasks
    
    def retry_task(self, task_id: int, user_id: int = None) -> bool:
        """Повторная отправка задачи"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("""
                    UPDATE post_queue
                    SET status = 'pending', attempts = 0, error = NULL
                    WHERE id = ? AND user_id = ?
                """, (task_id, user_id))
            else:
                cursor.execute("""
                    UPDATE post_queue
                    SET status = 'pending', attempts = 0, error = NULL
                    WHERE id = ?
                """, (task_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_task(self, task_id: int, user_id: int = None) -> bool:
        """Удаление задачи"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("DELETE FROM post_queue WHERE id = ? AND user_id = ?", (task_id, user_id))
            else:
                cursor.execute("DELETE FROM post_queue WHERE id = ?", (task_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_user_queue(self, user_id: int) -> int:
        """Очистка очереди пользователя"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM post_queue WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount


queue_repo = QueueRepository()