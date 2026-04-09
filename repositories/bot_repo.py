from typing import List, Optional, Dict
from datetime import datetime

from core.database import get_db_connection


class BotRepository:

    def get_user_bots(self, user_id: int) -> List[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_bots WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    "id": row[0],
                    "user_id": row[1],
                    "name": row[2],
                    "token": row[3],
                    "platform": row[4] if len(row) > 4 else "telegram",
                    "inn": row[5] if len(row) > 5 else None,
                    "created_at": row[6] if len(row) > 6 else None,
                    "youtube_api_key": row[7] if len(row) > 7 else None
                })

            return result

    def update_bot(self, bot_id: int, name: str, token: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE user_bots
                SET name = ?, token = ?
                WHERE id = ?
            """, (name, token, bot_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_bot(self, user_id: int, name: str, token: str) -> Optional[int]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_bots (user_id, name, token, created_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, name, token, datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid

    def delete_bot(self, bot_id: int) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_bots WHERE id = ?", (bot_id,))
            conn.commit()
            return cursor.rowcount > 0
        
    def get_by_id(self, bot_id: int, user_id: int = None):
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if user_id:
                cursor.execute(
                    "SELECT * FROM user_bots WHERE id = ? AND user_id = ?",
                    (bot_id, user_id)
                )
            else:
                cursor.execute(
                    "SELECT * FROM user_bots WHERE id = ?",
                    (bot_id,)
                )

            row = cursor.fetchone()

            if not row:
                return None

            return {
                "id": row[0],
                "user_id": row[1],
                "name": row[2],
                "token": row[3],
                "platform": row[4] if len(row) > 4 else "telegram",
                "inn": row[5] if len(row) > 5 else None,
                "created_at": row[6] if len(row) > 6 else None,
                "youtube_api_key": row[7] if len(row) > 7 else None
            }
        

    def add_bot_channel(self, bot_id: int, channel_id: int) -> bool:
        """Привязка бота к каналу"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO bot_channels (bot_id, channel_id)
                VALUES (?, ?)
            """, (bot_id, channel_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_bot_channels(self, bot_id: int):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT bc.id, bc.bot_id, bc.channel_id,
                    uc.channel_name
                FROM bot_channels bc
                JOIN user_channels uc ON bc.channel_id = uc.id
                WHERE bc.bot_id = ?
            """, (bot_id,))

            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "bot_id": row[1],
                    "channel_id": row[2],
                    "channel_name": row[3]
                }
                for row in rows
            ]
        
    def get_bot_for_channel(self, channel_id: int, user_id: int) -> Optional[Dict]:
        """Получение бота для канала"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.id, b.name, b.token, b.platform
                FROM user_bots b
                JOIN bot_channels bc ON bc.bot_id = b.id
                WHERE bc.channel_id = ? AND b.user_id = ?
                LIMIT 1
            """, (channel_id, user_id))
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'name': row[1],
                    'token': row[2],
                    'platform': row[3]
                }
            return None
        
    def get_by_id(self, bot_id: int, user_id: int) -> Optional[Dict]:
        """Получение бота по ID"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, name, token, platform, inn, youtube_api_key, check_interval, created_at
                FROM user_bots
                WHERE id = ? AND user_id = ?
            """, (bot_id, user_id))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None


bot_repo = BotRepository()