"""
Модуль для работы с базой данных
Production-ready, type-hinted, fully featured
"""
import sqlite3
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Generator
from contextlib import contextmanager
from datetime import datetime

from core.config import DB_PATH

logger = logging.getLogger(__name__)


# =========================
# CONNECTION MANAGERS
# =========================

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Получение соединения с БД (контекстный менеджер)"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def get_connection() -> sqlite3.Connection:
    """Получение прямого соединения с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction() -> Generator[sqlite3.Connection, None, None]:
    """Контекстный менеджер для транзакций"""
    with get_db_connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


# =========================
# CORE QUERY FUNCTIONS
# =========================

def fetch_one(sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
    """Выполнить запрос и вернуть одну строку как словарь"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params or ())
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"fetch_one error: {e}\nSQL: {sql}")
            raise


def fetch_all(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    """Выполнить запрос и вернуть все строки как список словарей"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"fetch_all error: {e}\nSQL: {sql}")
            raise


def fetch_value(sql: str, params: tuple = None, default: Any = None) -> Any:
    """Выполнить запрос и вернуть первое значение первой строки"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params or ())
            row = cursor.fetchone()
            return row[0] if row else default
        except sqlite3.Error as e:
            logger.error(f"fetch_value error: {e}\nSQL: {sql}")
            raise


def execute(sql: str, params: tuple = None) -> int:
    """Выполнить запрос и вернуть количество изменённых строк"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params or ())
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"execute error: {e}\nSQL: {sql}")
            raise


def insert(sql: str, params: tuple = None) -> int:
    """Выполнить INSERT и вернуть ID последней вставленной записи"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params or ())
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"insert error: {e}\nSQL: {sql}")
            raise


def insert_many(sql: str, params_list: List[tuple]) -> int:
    """Выполнить множество INSERT запросов"""
    if not params_list:
        return 0
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.executemany(sql, params_list)
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"insert_many error: {e}\nSQL: {sql}")
            raise


def execute_many(sql: str, params_list: List[tuple]) -> int:
    """Алиас для insert_many"""
    return insert_many(sql, params_list)


# =========================
# ALIASES FOR COMPATIBILITY
# =========================

def execute_query(sql: str, params: tuple = None) -> List[Dict[str, Any]]:
    """Алиас для fetch_all"""
    return fetch_all(sql, params)


def execute_insert(sql: str, params: tuple = None) -> int:
    """Алиас для insert"""
    return insert(sql, params)


def execute_update(sql: str, params: tuple = None) -> int:
    """Алиас для execute"""
    return execute(sql, params)


def execute_sql(sql: str, params: tuple = None) -> int:
    """Выполнить произвольный SQL"""
    return execute(sql, params)


# =========================
# SCHEMA UTILITIES
# =========================

def table_exists(table_name: str) -> bool:
    """Проверить существование таблицы"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return cursor.fetchone() is not None


def get_table_columns(table_name: str) -> List[str]:
    """Получить список колонок таблицы (только если таблица существует)"""
    if not table_exists(table_name):
        return []
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]


def get_table_info(table_name: str) -> List[Dict[str, Any]]:
    """Получить детальную информацию о таблице"""
    if not table_exists(table_name):
        return []
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return [
            {
                'name': col[1],
                'type': col[2],
                'notnull': bool(col[3]),
                'default': col[4],
                'pk': bool(col[5])
            }
            for col in columns
        ]


def get_table_count(table_name: str) -> int:
    """Получить количество записей в таблице"""
    if not table_exists(table_name):
        return 0
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]


def add_column_if_not_exists(table_name: str, column_name: str, column_type: str, default_value: Any = None) -> bool:
    """Добавить колонку если она не существует"""
    if not table_exists(table_name):
        return False
    
    if column_name not in get_table_columns(table_name):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default_value is not None:
                sql += f" DEFAULT {default_value}"
            cursor.execute(sql)
            conn.commit()
            logger.info(f"Added column {column_name} to {table_name}")
            return True
    return False


def drop_table_if_exists(table_name: str) -> bool:
    """Удалить таблицу если она существует"""
    if table_exists(table_name):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE {table_name}")
            conn.commit()
            logger.info(f"Dropped table {table_name}")
            return True
    return False


def vacuum() -> None:
    """Оптимизация базы данных"""
    with get_db_connection() as conn:
        conn.execute("VACUUM")
        logger.info("Database vacuum completed")


# =========================
# DATABASE INITIALIZATION
# =========================

def init_db():
    """Инициализация базы данных - создание всех таблиц"""
    logger.info("Initializing database...")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # ========== USERS TABLE ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE,
                project_name TEXT DEFAULT 'Мой проект',
                youtube_api_key TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        
        # ========== SESSIONS TABLE ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT,
                expires_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # ========== USER BOTS TABLE ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                token TEXT NOT NULL,
                platform TEXT DEFAULT 'telegram',
                inn TEXT,
                youtube_api_key TEXT,
                check_interval INTEGER DEFAULT 15,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # ========== USER CHANNELS TABLE ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_name TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                channel_url TEXT,
                platform TEXT DEFAULT 'telegram',
                api_key TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # ========== BOT CHANNELS (MANY-TO-MANY) ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                created_at TEXT,
                FOREIGN KEY (bot_id) REFERENCES user_bots(id) ON DELETE CASCADE,
                FOREIGN KEY (channel_id) REFERENCES user_channels(id) ON DELETE CASCADE,
                UNIQUE(bot_id, channel_id)
            )
        """)
        
        # ========== POSTS STATISTICS ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_id INTEGER,
                platform TEXT,
                post_text TEXT,
                media_type TEXT,
                status TEXT,
                sent_at TEXT,
                error TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # ========== SCHEDULED POSTS ==========
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
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # ========== POST QUEUE ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_queue (
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
                scheduled_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # ========== YOUTUBE CHANNELS ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS youtube_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                youtube_channel_id TEXT NOT NULL,
                youtube_channel_name TEXT NOT NULL,
                youtube_channel_url TEXT,
                target_channels TEXT,
                post_template TEXT,
                include_description INTEGER DEFAULT 0,
                last_video_id TEXT,
                last_checked TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                button_url TEXT,
                button_style TEXT DEFAULT 'success',
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # ========== UPLOADS LOG ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploads_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                file_name TEXT,
                file_path TEXT,
                file_size INTEGER,
                file_type TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # ========== CREATE INDEXES ==========
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_post_queue_user_id ON post_queue(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_post_queue_status ON post_queue(status)",
            "CREATE INDEX IF NOT EXISTS idx_post_queue_created_at ON post_queue(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_posts_stats_user_id ON posts_stats(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_posts_stats_sent_at ON posts_stats(sent_at)",
            "CREATE INDEX IF NOT EXISTS idx_scheduled_posts_user_id ON scheduled_posts(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_scheduled_posts_scheduled_at ON scheduled_posts(scheduled_at)",
            "CREATE INDEX IF NOT EXISTS idx_youtube_channels_user_id ON youtube_channels(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_youtube_channels_last_checked ON youtube_channels(last_checked)",
            "CREATE INDEX IF NOT EXISTS idx_user_bots_user_id ON user_bots(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_channels_user_id ON user_channels(user_id)",
        ]
        
        for idx in indexes:
            try:
                cursor.execute(idx)
            except sqlite3.Error as e:
                logger.warning(f"Index creation failed: {e}")
        
        conn.commit()
        
        # ========== RUN MIGRATIONS (after tables exist) ==========
        _run_migrations(conn)
        
        # ========== CREATE DEFAULT ADMIN ==========
        _create_default_admin(conn)
        
        logger.info("✅ Database initialized successfully")


def _run_migrations(conn: sqlite3.Connection):
    """Выполнение миграций для существующих таблиц (после их создания)"""
    cursor = conn.cursor()
    
    # Миграция для таблицы users
    if table_exists('users'):
        columns = get_table_columns('users')
        
        if 'updated_at' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN updated_at TEXT")
            cursor.execute("UPDATE users SET updated_at = created_at WHERE updated_at IS NULL")
            logger.info("  ✓ Added updated_at column to users")
        
        if 'password_hash' not in columns and 'password' in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            cursor.execute("UPDATE users SET password_hash = password WHERE password_hash IS NULL")
            logger.info("  ✓ Migrated password to password_hash")
    
    # Миграция для таблицы sessions
    if table_exists('sessions'):
        columns = get_table_columns('sessions')
        
        if 'expires_at' not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN expires_at TEXT")
            logger.info("  ✓ Added expires_at column to sessions")
        
        if 'created_at' not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN created_at TEXT")
            cursor.execute("UPDATE sessions SET created_at = datetime('now') WHERE created_at IS NULL")
            logger.info("  ✓ Added created_at column to sessions")
    
    conn.commit()


def _create_default_admin(conn: sqlite3.Connection):
    """Создание администратора по умолчанию"""
    from utils.helpers import hash_password
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            hashed_pw = hash_password("admin123")
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, is_admin, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("admin", hashed_pw, "Administrator", 1, now, now))
            conn.commit()
            logger.info("  ✓ Created default admin (login: admin, password: admin123)")
    except Exception as e:
        logger.warning(f"Could not create default admin: {e}")


# =========================
# UTILITY FUNCTIONS
# =========================

def check_db_connection() -> bool:
    """Проверка подключения к БД"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_db_version() -> str:
    """Получение версии SQLite"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sqlite_version()")
        return cursor.fetchone()[0]


def get_db_size() -> int:
    """Получение размера базы данных в байтах"""
    try:
        return os.path.getsize(DB_PATH)
    except OSError:
        return 0


def get_db_size_mb() -> float:
    """Получение размера базы данных в МБ"""
    return round(get_db_size() / (1024 * 1024), 2)


def backup_database(backup_path: str = None) -> str:
    """Создание резервной копии базы данных"""
    if not backup_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(DB_PATH).parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"backup_{timestamp}.db"
    
    import shutil
    shutil.copy2(DB_PATH, backup_path)
    logger.info(f"Database backup created: {backup_path}")
    return str(backup_path)


# =========================
# EXPORTS
# =========================

__all__ = [
    'get_db_connection',
    'get_connection',
    'transaction',
    'fetch_one',
    'fetch_all',
    'fetch_value',
    'execute',
    'insert',
    'insert_many',
    'execute_many',
    'execute_query',
    'execute_insert',
    'execute_update',
    'execute_sql',
    'table_exists',
    'get_table_columns',
    'get_table_info',
    'get_table_count',
    'add_column_if_not_exists',
    'drop_table_if_exists',
    'vacuum',
    'init_db',
    'check_db_connection',
    'get_db_version',
    'get_db_size',
    'get_db_size_mb',
    'backup_database',
]