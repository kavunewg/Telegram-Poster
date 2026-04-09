"""
Repository for user channels.
"""

import logging
from typing import Any, Dict, List, Optional

from core.database import get_db_connection
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class ChannelRepository(BaseRepository):
    def __init__(self):
        super().__init__("user_channels")

    def get_user_channels(self, user_id: int) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    uc.id,
                    uc.user_id,
                    uc.channel_name,
                    uc.channel_id,
                    uc.channel_url,
                    uc.platform,
                    uc.api_key,
                    uc.is_main,
                    b.id AS bot_id,
                    b.name AS bot_name,
                    b.token AS bot_token
                FROM user_channels uc
                LEFT JOIN bot_channels bc ON bc.channel_id = uc.id
                LEFT JOIN user_bots b ON bc.bot_id = b.id
                WHERE uc.user_id = ?
                ORDER BY uc.id DESC
                """,
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_channel_by_id(self, channel_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    uc.*,
                    b.id AS bot_id,
                    b.name AS bot_name,
                    b.token AS bot_token
                FROM user_channels uc
                LEFT JOIN bot_channels bc ON bc.channel_id = uc.id
                LEFT JOIN user_bots b ON bc.bot_id = b.id
                WHERE uc.id = ? AND uc.user_id = ?
                LIMIT 1
                """,
                (channel_id, user_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_channels_by_platform(self, user_id: int, platform: str) -> List[Dict[str, Any]]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM user_channels
                WHERE user_id = ? AND platform = ?
                ORDER BY channel_name
                """,
                (user_id, platform),
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_channel(
        self,
        user_id: int,
        channel_name: str,
        channel_id: str,
        channel_url: str = None,
        platform: str = "telegram",
        api_key: str = None,
        is_main: int = 0,
    ) -> Optional[int]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_channels (
                    user_id, channel_name, channel_id, channel_url,
                    platform, api_key, is_main
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    channel_name,
                    channel_id,
                    channel_url,
                    (platform or "telegram").lower(),
                    api_key,
                    is_main,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def update_channel(
        self,
        channel_id: int,
        user_id: int,
        channel_name: str,
        channel_id_value: str,
        channel_url: str = None,
        platform: str = "telegram",
        api_key: str = None,
    ) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE user_channels
                SET channel_name = ?, channel_id = ?, channel_url = ?, platform = ?, api_key = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    channel_name,
                    channel_id_value,
                    channel_url,
                    (platform or "telegram").lower(),
                    api_key,
                    channel_id,
                    user_id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_channel(self, channel_id: int, user_id: int) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Keep compatibility with old DB snapshots where bot_channels may be absent.
            try:
                cursor.execute("DELETE FROM bot_channels WHERE channel_id = ?", (channel_id,))
            except Exception as exc:
                logger.warning("Could not cleanup bot_channels for channel %s: %s", channel_id, exc)
            cursor.execute(
                "DELETE FROM user_channels WHERE id = ? AND user_id = ?",
                (channel_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0


channel_repo = ChannelRepository()
