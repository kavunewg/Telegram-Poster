"""
Репозиторий для работы с каналами (production-ready)
"""

from typing import List, Optional, Dict, Any

from core.database import get_db_connection
from repositories.base_repo import BaseRepository


class ChannelRepository(BaseRepository):
    def __init__(self):
        super().__init__("user_channels")

    # =========================
    # HELPERS
    # =========================
    def _row_to_dict(self, row) -> Dict[str, Any]:
        if not row:
            return None
        return dict(row)

    def _rows_to_dicts(self, rows) -> List[Dict[str, Any]]:
        return [dict(row) for row in rows]

    # =========================
    # GET CHANNELS
    # =========================
    def get_user_channels(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение всех каналов пользователя с ботами"""

        with get_db_connection() as conn:
            conn.row_factory = None
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    uc.id,
                    uc.user_id,
                    uc.channel_name,
                    uc.channel_id,
                    uc.channel_url,
                    uc.platform,
                    uc.api_key,
                    uc.is_main,
                    b.id as bot_id,
                    b.name as bot_name
                FROM user_channels uc
                LEFT JOIN bot_channels bc ON bc.channel_id = uc.id
                LEFT JOIN user_bots b ON bc.bot_id = b.id
                WHERE uc.user_id = ?
            """, (user_id,))

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "channel_name": row[2],
                    "channel_id": row[3],
                    "channel_url": row[4],
                    "platform": row[5],
                    "api_key": row[6],
                    "is_main": row[7],
                    "bot_id": row[8],
                    "bot_name": row[9],
                }
                for row in rows
            ]

    def get_channel_by_id(self, channel_id: int, user_id: int) -> Optional[Dict]:
        """Получение канала по ID (с защитой user_id)"""

        with get_db_connection() as conn:
            conn.row_factory = None
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM user_channels
                WHERE id = ? AND user_id = ?
            """, (channel_id, user_id))

            row = cursor.fetchone()
            return dict(row) if row else None

    def get_channels_by_platform(self, user_id: int, platform: str) -> List[Dict]:
        """Получение каналов по платформе"""

        with get_db_connection() as conn:
            conn.row_factory = None
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM user_channels
                WHERE user_id = ? AND platform = ?
                ORDER BY channel_name
            """, (user_id, platform))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    # =========================
    # CREATE
    # =========================
    def add_channel(
        self,
        user_id: int,
        channel_name: str,
        channel_id: str,
        channel_url: str = None,
        platform: str = "telegram",
        api_key: str = None,
        is_main: int = 0
    ) -> Optional[int]:
        """Добавление канала"""

        platform = (platform or "telegram").lower()

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO user_channels (
                    user_id,
                    channel_name,
                    channel_id,
                    channel_url,
                    platform,
                    api_key,
                    is_main
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                channel_name,
                channel_id,
                channel_url,
                platform,
                api_key,
                is_main
            ))

            conn.commit()
            return cursor.lastrowid

    # =========================
    # UPDATE
    # =========================
    def update_channel(
        self,
        channel_id: int,
        user_id: int,
        channel_name: str,
        channel_id_value: str,
        channel_url: str = None,
        platform: str = "telegram",
        api_key: str = None
    ) -> bool:
        """Обновление канала (с защитой user_id)"""

        platform = (platform or "telegram").lower()

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE user_channels
                SET 
                    channel_name = ?,
                    channel_id = ?,
                    channel_url = ?,
                    platform = ?,
                    api_key = ?
                WHERE id = ? AND user_id = ?
            """, (
                channel_name,
                channel_id_value,
                channel_url,
                platform,
                api_key,
                channel_id,
                user_id
            ))

            conn.commit()
            return cursor.rowcount > 0

    # =========================
    # DELETE
    # =========================
    def delete_channel(self, channel_id: int, user_id: int) -> bool:
        """Удаление канала (только если принадлежит пользователю)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Сначала удаляем связи с ботами
            cursor.execute("DELETE FROM bot_channels WHERE channel_id = ?", (channel_id,))
            # Затем удаляем канал
            cursor.execute(
                "DELETE FROM user_channels WHERE id = ? AND user_id = ?", 
                (channel_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0


# Глобальный экземпляр
channel_repo = ChannelRepository()