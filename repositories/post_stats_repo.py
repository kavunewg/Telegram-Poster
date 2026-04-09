"""
Репозиторий для работы со статистикой постов
"""
from typing import List, Dict, Optional
from datetime import datetime

from core.database import get_db_connection
from repositories.base_repo import BaseRepository


class PostStatsRepository(BaseRepository):
    def __init__(self):
        super().__init__("posts_stats")

    # =========================
    # CREATE
    # =========================
    def add_stat(
        self,
        user_id: int,
        channel_db_id: Optional[int],
        platform: str,
        post_text: str,
        media_type: str,
        status: str,
        error: str = None
    ) -> Optional[int]:
        """Добавление записи статистики"""

        with get_db_connection() as conn:
            conn.row_factory = None
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO posts_stats (
                    user_id,
                    channel_id,
                    platform,
                    post_text,
                    media_type,
                    status,
                    sent_at,
                    error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                channel_db_id if channel_db_id else None,
                platform,
                (post_text or "")[:500],
                media_type,
                status,
                datetime.now().isoformat(),
                error
            ))

            conn.commit()
            return cursor.lastrowid

    # =========================
    # STATS SUMMARY
    # =========================
    def get_user_stats(self, user_id: int) -> Dict:
        """Общая статистика пользователя"""

        with get_db_connection() as conn:
            conn.row_factory = None
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END)
                FROM posts_stats
                WHERE user_id = ?
            ''', (user_id,))

            row = cursor.fetchone()

            return {
                "total": row[0] if row else 0,
                "success": row[1] or 0 if row else 0,
                "error": row[2] or 0 if row else 0,
                "failed": row[2] or 0 if row else 0,
            }

    # =========================
    # USER POSTS
    # =========================
    def get_user_posts(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Получение постов пользователя"""

        with get_db_connection() as conn:
            conn.row_factory = None
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 
                    ps.id,
                    ps.channel_id,
                    ps.platform,
                    ps.post_text,
                    ps.media_type,
                    ps.status,
                    ps.sent_at,
                    ps.error,
                    COALESCE(uc.channel_name, 'Неизвестный канал')
                FROM posts_stats ps
                LEFT JOIN user_channels uc ON ps.channel_id = uc.id
                WHERE ps.user_id = ?
                ORDER BY ps.sent_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))

            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "channel_id": row[1],
                    "platform": row[2],
                    "post_text": row[3],
                    "media_type": row[4],
                    "status": row[5],
                    "sent_at": row[6],
                    "error": row[7],
                    "channel_name": row[8]
                })

            return result

    # =========================
    # ADMIN POSTS
    # =========================
    def get_posts(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Получение постов (для админа, с фильтром)"""

        with get_db_connection() as conn:
            conn.row_factory = None
            cursor = conn.cursor()

            query = '''
                SELECT 
                    ps.id,
                    ps.user_id,
                    ps.channel_id,
                    ps.platform,
                    ps.post_text,
                    ps.media_type,
                    ps.status,
                    ps.sent_at,
                    ps.error,
                    u.username,
                    u.full_name,
                    COALESCE(uc.channel_name, 'Неизвестный канал')
                FROM posts_stats ps
                LEFT JOIN users u ON ps.user_id = u.id
                LEFT JOIN user_channels uc ON ps.channel_id = uc.id
            '''

            params = []

            if status:
                query += " WHERE ps.status = ?"
                params.append(status)

            query += " ORDER BY ps.sent_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "user_id": row[1],
                    "channel_id": row[2],
                    "platform": row[3],
                    "post_text": row[4],
                    "media_type": row[5],
                    "status": row[6],
                    "sent_at": row[7],
                    "error": row[8],
                    "username": row[9],
                    "full_name": row[10],
                    "channel_name": row[11]
                })

            return result

    # =========================
    # CHANNEL STATS
    # =========================
    def get_channel_stats(self, user_id: int) -> Dict[int, Dict]:
        """Статистика по каналам"""

        posts = self.get_user_posts(user_id, limit=1000)

        stats = {}

        for post in posts:
            channel_id = post["channel_id"] or 0

            if channel_id not in stats:
                stats[channel_id] = {
                    "name": post["channel_name"],
                    "total": 0,
                    "success": 0,
                    "error": 0
                }

            stats[channel_id]["total"] += 1

            if post["status"] == "success":
                stats[channel_id]["success"] += 1
            else:
                stats[channel_id]["error"] += 1

        return stats


# Глобальный экземпляр
post_stats_repo = PostStatsRepository()

post_repo = post_stats_repo
