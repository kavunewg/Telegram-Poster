"""
Repository for scheduled posts.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

from core.database import get_db_connection, insert


class ScheduleRepository:
    def __init__(self):
        self._init_table()
        self._refresh_schema_flags()

    def _refresh_schema_flags(self) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(scheduled_posts)")
            rows = cursor.fetchall()
        self._columns = {row["name"] if hasattr(row, "keys") else row[1] for row in rows}
        self._has_scheduled_time = "scheduled_time" in self._columns
        self._scheduled_select_expr = (
            "COALESCE(scheduled_at, scheduled_time) AS scheduled_at"
            if self._has_scheduled_time
            else "scheduled_at"
        )
        self._scheduled_order_expr = "COALESCE(scheduled_at, scheduled_time)" if self._has_scheduled_time else "scheduled_at"

    def _init_table(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
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
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_posts_user_id ON scheduled_posts(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_posts_scheduled_at ON scheduled_posts(scheduled_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status ON scheduled_posts(status)")
            conn.commit()

    def save_post(
        self,
        user_id: int,
        channels: List,
        post_text: str,
        media_path: str,
        media_name: str,
        media_size: int,
        media_type: str,
        button: dict,
        scheduled_at: str,
        is_regular: bool = False,
        regular_settings: dict = None,
    ) -> int:
        now = datetime.now().isoformat()
        columns = [
            "user_id",
            "channels",
            "post_text",
            "media_path",
            "media_name",
            "media_size",
            "media_type",
            "button",
            "scheduled_at",
            "is_regular",
            "regular_settings",
            "status",
            "created_at",
            "updated_at",
        ]
        values = [
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
            "pending",
            now,
            now,
        ]
        if self._has_scheduled_time:
            columns.append("scheduled_time")
            values.append(scheduled_at)

        placeholders = ", ".join("?" for _ in columns)
        sql = f"""
            INSERT INTO scheduled_posts ({", ".join(columns)})
            VALUES ({placeholders})
        """
        return insert(sql, tuple(values))

    def _deserialize_post(self, row) -> Dict:
        post = dict(row)
        for key, default in (("channels", []), ("button", None), ("regular_settings", {})):
            if post.get(key):
                try:
                    post[key] = json.loads(post[key])
                except Exception:
                    post[key] = default
            else:
                post[key] = default

        if post.get("scheduled_at"):
            try:
                dt = datetime.fromisoformat(post["scheduled_at"])
                post["scheduled_time_formatted"] = dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                post["scheduled_time_formatted"] = post["scheduled_at"]
        return post

    def get_user_scheduled_posts(self, user_id: int) -> List[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT id, user_id, channels, post_text, media_path, media_name,
                       media_size, media_type, button, {self._scheduled_select_expr}, is_regular,
                       regular_settings, status, created_at, updated_at
                FROM scheduled_posts
                WHERE user_id = ?
                ORDER BY {self._scheduled_order_expr} ASC
                """,
                (user_id,),
            )
            return [self._deserialize_post(row) for row in cursor.fetchall()]

    def get_post_by_id(self, post_id: int, user_id: int = None) -> Optional[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if user_id is None:
                cursor.execute(
                    f"""
                    SELECT id, user_id, channels, post_text, media_path, media_name,
                           media_size, media_type, button, {self._scheduled_select_expr}, is_regular,
                           regular_settings, status, created_at, updated_at
                    FROM scheduled_posts
                    WHERE id = ?
                    """,
                    (post_id,),
                )
            else:
                cursor.execute(
                    f"""
                    SELECT id, user_id, channels, post_text, media_path, media_name,
                           media_size, media_type, button, {self._scheduled_select_expr}, is_regular,
                           regular_settings, status, created_at, updated_at
                    FROM scheduled_posts
                    WHERE id = ? AND user_id = ?
                    """,
                    (post_id, user_id),
                )
            row = cursor.fetchone()
            return self._deserialize_post(row) if row else None

    def get_pending_posts(self) -> List[Dict]:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT id, user_id, channels, post_text, media_path, media_name,
                       media_size, media_type, button, {self._scheduled_select_expr}, is_regular,
                       regular_settings, status, created_at, updated_at
                FROM scheduled_posts
                WHERE status = 'pending'
                ORDER BY {self._scheduled_order_expr} ASC
                """
            )
            return [self._deserialize_post(row) for row in cursor.fetchall()]

    def update_post(
        self,
        post_id: int,
        user_id: int,
        channels: List,
        post_text: str,
        media_path: str,
        media_name: str,
        media_size: int,
        media_type: str,
        button: dict,
        scheduled_at: str,
        is_regular: bool,
        regular_settings: dict,
    ) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            fields = [
                "channels = ?",
                "post_text = ?",
                "media_path = ?",
                "media_name = ?",
                "media_size = ?",
                "media_type = ?",
                "button = ?",
                "scheduled_at = ?",
                "is_regular = ?",
                "regular_settings = ?",
                "updated_at = ?",
            ]
            params = [
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
                datetime.now().isoformat(),
            ]
            if self._has_scheduled_time:
                fields.append("scheduled_time = ?")
                params.append(scheduled_at)
            params.extend([post_id, user_id])
            cursor.execute(
                f"""
                UPDATE scheduled_posts
                SET {", ".join(fields)}
                WHERE id = ? AND user_id = ?
                """,
                tuple(params),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_status(self, post_id: int, status: str, updated_at: str = None, error_message: str = None) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE scheduled_posts
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, updated_at or datetime.now().isoformat(), post_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def update_scheduled_time(self, post_id: int, scheduled_at: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            fields = ["scheduled_at = ?", "updated_at = ?"]
            params = [scheduled_at, datetime.now().isoformat()]
            if self._has_scheduled_time:
                fields.append("scheduled_time = ?")
                params.append(scheduled_at)
            params.append(post_id)
            cursor.execute(
                f"""
                UPDATE scheduled_posts
                SET {", ".join(fields)}
                WHERE id = ?
                """,
                tuple(params),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_post(self, post_id: int) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self, user_id: int) -> Dict:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM scheduled_posts WHERE user_id = ?", (user_id,))
            total = cursor.fetchone()[0]
            cursor.execute("SELECT status, COUNT(*) FROM scheduled_posts WHERE user_id = ? GROUP BY status", (user_id,))
            grouped = dict(cursor.fetchall())
            return {
                "total": total,
                "pending": grouped.get("pending", 0),
                "processing": grouped.get("processing", 0),
                "success": grouped.get("success", 0),
                "error": grouped.get("error", 0) + grouped.get("failed", 0),
            }


schedule_repo = ScheduleRepository()
