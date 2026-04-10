"""
Repository for YouTube monitored channels.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from core.database import get_db_connection
from repositories.base_repo import BaseRepository

logger = logging.getLogger(__name__)


class YouTubeRepository(BaseRepository):
    def __init__(self):
        super().__init__("youtube_channels")

    def _deserialize(self, row) -> Optional[Dict]:
        if not row:
            return None

        channel = dict(row)
        raw_targets = channel.get("target_channels")
        if raw_targets:
            try:
                channel["target_channels"] = json.loads(raw_targets) if isinstance(raw_targets, str) else raw_targets
            except Exception:
                channel["target_channels"] = []
        else:
            channel["target_channels"] = []

        channel["include_description"] = bool(channel.get("include_description", 0))
        channel["is_active"] = bool(channel.get("is_active", 0))
        return channel

    def add_channel(
        self,
        user_id: int,
        youtube_channel_id: str,
        youtube_channel_name: str,
        youtube_channel_url: str,
        target_channels: List[Dict],
        post_template: str = None,
        include_description: int = 0,
        button_url: str = None,
        button_style: str = "success",
    ) -> Optional[int]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO youtube_channels (
                        user_id, youtube_channel_id, youtube_channel_name, youtube_channel_url,
                        target_channels, post_template, include_description, button_url, button_style,
                        created_at, is_active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        youtube_channel_id,
                        youtube_channel_name,
                        youtube_channel_url,
                        json.dumps(target_channels, ensure_ascii=False),
                        post_template,
                        1 if include_description else 0,
                        button_url,
                        button_style or "success",
                        datetime.now().isoformat(),
                        1,
                    ),
                )
                conn.commit()
                return cursor.lastrowid
            except Exception as exc:
                logger.error("Failed to add YouTube channel: %s", exc)
                return None

    def get_user_channels(self, user_id: int) -> List[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, youtube_channel_id, youtube_channel_name,
                       youtube_channel_url, target_channels, post_template,
                       include_description, last_video_id, last_checked,
                       is_active, created_at, button_url, button_style
                FROM youtube_channels
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            )
            return [self._deserialize(row) for row in cursor.fetchall()]

    def get_channel_by_id(self, channel_id: int, user_id: int) -> Optional[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, youtube_channel_id, youtube_channel_name, youtube_channel_url,
                       target_channels, post_template, include_description,
                       last_video_id, last_checked, is_active, created_at,
                       button_url, button_style
                FROM youtube_channels
                WHERE id = ? AND user_id = ?
                """,
                (channel_id, user_id),
            )
            return self._deserialize(cursor.fetchone())

    def get_active_channels(self) -> List[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT yc.id, yc.user_id, yc.youtube_channel_id, yc.youtube_channel_name,
                       yc.youtube_channel_url, yc.target_channels, yc.post_template,
                       yc.include_description, yc.last_video_id, yc.last_checked,
                       yc.button_url, yc.button_style,
                       COALESCE(
                           NULLIF(TRIM(u.youtube_api_key), ''),
                           (
                               SELECT ub.youtube_api_key
                               FROM user_bots ub
                               WHERE ub.user_id = yc.user_id
                                 AND LOWER(COALESCE(ub.platform, '')) = 'youtube'
                                 AND ub.youtube_api_key IS NOT NULL
                                 AND TRIM(ub.youtube_api_key) <> ''
                               ORDER BY ub.created_at DESC
                               LIMIT 1
                           )
                       ) AS youtube_api_key
                FROM youtube_channels yc
                JOIN users u ON yc.user_id = u.id
                WHERE yc.is_active = 1
                """
            )
            rows = []
            for row in cursor.fetchall():
                item = dict(row)
                raw_targets = item.get("target_channels")
                if raw_targets:
                    try:
                        item["target_channels"] = json.loads(raw_targets) if isinstance(raw_targets, str) else raw_targets
                    except Exception:
                        item["target_channels"] = []
                else:
                    item["target_channels"] = []
                item["include_description"] = bool(item.get("include_description", 0))
                rows.append(item)
            return rows

    def update_last_video(self, channel_id: int, video_id: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE youtube_channels
                SET last_video_id = ?, last_checked = ?
                WHERE id = ?
                """,
                (video_id, datetime.now().isoformat(), channel_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def toggle_active(self, channel_id: int, user_id: int, is_active: bool) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE youtube_channels
                SET is_active = ?
                WHERE id = ? AND user_id = ?
                """,
                (1 if is_active else 0, channel_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_channel(
        self,
        channel_id: int,
        user_id: int,
        target_channels: List[Dict],
        post_template: str = None,
        include_description: int = 0,
        button_url: str = None,
        button_style: str = "success",
    ) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE youtube_channels
                SET target_channels = ?, post_template = ?, include_description = ?,
                    button_url = ?, button_style = ?
                WHERE id = ? AND user_id = ?
                """,
                (
                    json.dumps(target_channels, ensure_ascii=False),
                    post_template,
                    1 if include_description else 0,
                    button_url,
                    button_style or "success",
                    channel_id,
                    user_id,
                ),
            )
            conn.commit()
            return cursor.rowcount > 0

    def has_recent_analytics_snapshot(self, channel_id: int, minutes: int = 60) -> bool:
        threshold = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 1
                FROM youtube_channel_analytics
                WHERE youtube_channel_db_id = ? AND recorded_at >= ?
                LIMIT 1
                """,
                (channel_id, threshold),
            )
            return cursor.fetchone() is not None

    def add_analytics_snapshot(
        self,
        user_id: int,
        youtube_channel_db_id: int,
        youtube_channel_id: str,
        subscriber_count: int,
        view_count: int,
        video_count: int,
    ) -> Optional[int]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO youtube_channel_analytics (
                    user_id,
                    youtube_channel_db_id,
                    youtube_channel_id,
                    subscriber_count,
                    view_count,
                    video_count,
                    recorded_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    youtube_channel_db_id,
                    youtube_channel_id,
                    int(subscriber_count or 0),
                    int(view_count or 0),
                    int(video_count or 0),
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_analytics_history(self, channel_id: int, user_id: int, days: int = 30) -> List[Dict]:
        threshold = (datetime.now() - timedelta(days=max(days, 1))).isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    subscriber_count,
                    view_count,
                    video_count,
                    recorded_at
                FROM youtube_channel_analytics
                WHERE youtube_channel_db_id = ? AND user_id = ? AND recorded_at >= ?
                ORDER BY recorded_at ASC
                """,
                (channel_id, user_id, threshold),
            )
            return [dict(row) for row in cursor.fetchall()]


youtube_repo = YouTubeRepository()
