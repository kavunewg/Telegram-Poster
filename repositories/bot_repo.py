from datetime import datetime
from typing import Dict, List, Optional

from core.database import get_db_connection


class BotRepository:
    def get_user_bots(self, user_id: int) -> List[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, name, token, platform, inn, youtube_api_key, check_interval, created_at
                FROM user_bots
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_user_youtube_api_key(self, user_id: int) -> Optional[str]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT youtube_api_key
                FROM user_bots
                WHERE user_id = ?
                  AND LOWER(COALESCE(platform, '')) = 'youtube'
                  AND youtube_api_key IS NOT NULL
                  AND TRIM(youtube_api_key) <> ''
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            return row["youtube_api_key"] if row else None

    def get_user_bot_by_platform(self, user_id: int, platform: str) -> Optional[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, name, token, platform, inn, youtube_api_key, check_interval, created_at
                FROM user_bots
                WHERE user_id = ? AND LOWER(COALESCE(platform, '')) = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id, (platform or "").lower()),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_platform_token(self, user_id: int, platform: str) -> Optional[str]:
        bot = self.get_user_bot_by_platform(user_id, platform)
        token = (bot or {}).get("token")
        return token if token and str(token).strip() else None

    def update_bot(
        self,
        bot_id: int,
        user_id: int,
        name: str,
        token: str,
        platform: str = "telegram",
        inn: str = None,
        youtube_api_key: str = None,
        check_interval: int = None,
    ) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE user_bots
                SET name = ?, token = ?, platform = ?, inn = ?, youtube_api_key = ?,
                    check_interval = COALESCE(?, check_interval)
                WHERE id = ? AND user_id = ?
                """,
                (name, token, platform, inn, youtube_api_key, check_interval, bot_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def add_bot(
        self,
        user_id: int,
        name: str,
        token: str,
        platform: str = "telegram",
        inn: str = None,
        youtube_api_key: str = None,
        check_interval: int = 15,
    ) -> Optional[int]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_bots (
                    user_id, name, token, platform, inn, youtube_api_key, check_interval, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    name,
                    token,
                    (platform or "telegram").lower(),
                    inn,
                    youtube_api_key,
                    check_interval,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def delete_bot(self, bot_id: int, user_id: int = None) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bot_channels WHERE bot_id = ?", (bot_id,))
            if user_id is None:
                cursor.execute("DELETE FROM user_bots WHERE id = ?", (bot_id,))
            else:
                cursor.execute("DELETE FROM user_bots WHERE id = ? AND user_id = ?", (bot_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_by_id(self, bot_id: int, user_id: int = None) -> Optional[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if user_id is None:
                cursor.execute(
                    """
                    SELECT id, user_id, name, token, platform, inn, youtube_api_key, check_interval, created_at
                    FROM user_bots
                    WHERE id = ?
                    """,
                    (bot_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, user_id, name, token, platform, inn, youtube_api_key, check_interval, created_at
                    FROM user_bots
                    WHERE id = ? AND user_id = ?
                    """,
                    (bot_id, user_id),
                )

            row = cursor.fetchone()
            return dict(row) if row else None

    def add_bot_channel(self, bot_id: int, channel_id: int) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO bot_channels (bot_id, channel_id)
                VALUES (?, ?)
                """,
                (bot_id, channel_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_bot_channels(self, bot_id: int) -> List[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT bc.id, bc.bot_id, bc.channel_id, uc.channel_name
                FROM bot_channels bc
                JOIN user_channels uc ON bc.channel_id = uc.id
                WHERE bc.bot_id = ?
                """,
                (bot_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_bot_for_channel(self, channel_id: int, user_id: int) -> Optional[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT b.id, b.user_id, b.name, b.token, b.platform, b.inn, b.youtube_api_key, b.check_interval, b.created_at
                FROM user_bots b
                JOIN bot_channels bc ON bc.bot_id = b.id
                WHERE bc.channel_id = ? AND b.user_id = ?
                LIMIT 1
                """,
                (channel_id, user_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None


bot_repo = BotRepository()
