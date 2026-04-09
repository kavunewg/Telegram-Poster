"""
Конфигурация приложения
"""
import os
from pathlib import Path

# Пути
BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / "media"
REGULAR_MEDIA_DIR = MEDIA_DIR / "regular"
DB_PATH = BASE_DIR / "users.db"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Настройки администратора
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# YouTube API Key (по умолчанию из env)
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# Проверка доступности YouTube API
try:
    from googleapiclient.discovery import build
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False

# Настройки загрузки файлов
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB
ALLOWED_EXTENSIONS = {
    'photo': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
    'video': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
    'document': ['.pdf', '.doc', '.docx', '.txt', '.zip']
}
ALLOWED_EXTENSIONS_ALL = (
    ALLOWED_EXTENSIONS['photo'] +
    ALLOWED_EXTENSIONS['video'] +
    ALLOWED_EXTENSIONS['document']
)

# Настройки планировщика
TIMEZONE = "Europe/Moscow"

# Настройки запросов к Telegram
try:
    from telegram.request import HTTPXRequest
    REQUEST_CONFIG = HTTPXRequest(
        connect_timeout=600.0,
        read_timeout=900.0,
        write_timeout=900.0,
        pool_timeout=600.0
    )
except ImportError:
    REQUEST_CONFIG = None

# Хранилище сессий постов (in-memory)
POST_SESSIONS: dict = {}
