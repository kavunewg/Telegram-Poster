"""
Сервис для работы с медиафайлами
"""
import os
import uuid
import shutil
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from fastapi import HTTPException

from core.config import MEDIA_DIR, REGULAR_MEDIA_DIR, ALLOWED_EXTENSIONS_ALL, MAX_FILE_SIZE
from repositories.post_stats_repo import post_stats_repo
from core.database import get_db_connection


def save_media_file(user_id: int, file_data: bytes, file_name: str,
                    post_type: str, post_id: int = None) -> Dict[str, Any]:
    """Сохранение медиафайла на диск и запись в лог"""
    
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS_ALL:
        raise HTTPException(status_code=400, detail=f"Недопустимый формат файла: {ext}")
    
    file_size = len(file_data) / (1024 * 1024)
    if file_size > MAX_FILE_SIZE / (1024 * 1024):
        raise HTTPException(status_code=400, detail=f"Файл слишком большой: {file_size:.1f} МБ")
    
    # Определяем тип медиа
    from core.config import ALLOWED_EXTENSIONS
    if ext in ALLOWED_EXTENSIONS['photo']:
        media_type = "photo"
    elif ext in ALLOWED_EXTENSIONS['video']:
        media_type = "video"
    else:
        media_type = "document"
    
    # Выбираем директорию для сохранения
    save_dir = REGULAR_MEDIA_DIR if post_type == "regular" else MEDIA_DIR
    os.makedirs(save_dir, exist_ok=True)
    
    # Генерируем уникальное имя файла
    unique_name = f"{post_type}_{user_id}_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(save_dir, unique_name)
    
    # Сохраняем файл
    with open(file_path, "wb") as f:
        f.write(file_data)
    
    # Логируем загрузку
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO uploads_log (user_id, file_name, file_path, file_size, file_type, post_type, post_id, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, file_name, file_path, file_size, media_type, post_type, post_id, datetime.now().isoformat()))
        conn.commit()
    
    return {
        "path": file_path,
        "name": file_name,
        "size": file_size,
        "type": media_type
    }


def delete_media_file(file_path: str) -> bool:
    """Удаление медиафайла с диска"""
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
            return True
        except Exception as e:
            print(f"Ошибка удаления файла {file_path}: {e}")
            return False
    return False


def cleanup_old_files(max_age_days: int = 7) -> None:
    """Очистка старых файлов (старше указанного количества дней)"""
    import time
    try:
        now = time.time()
        max_age_seconds = max_age_days * 86400
        
        for root, dirs, files in os.walk(MEDIA_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if os.path.getmtime(file_path) < (now - max_age_seconds):
                        os.unlink(file_path)
                        print(f"Удалён старый файл: {file_path}")
                except Exception as e:
                    print(f"Ошибка удаления {file_path}: {e}")
    except Exception as e:
        print(f"Ошибка очистки файлов: {e}")


def cleanup_orphan_regular_files() -> None:
    """Очистка медиафайлов регулярных постов, которые больше не используются"""
    if not os.path.exists(REGULAR_MEDIA_DIR):
        return
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT media_path FROM scheduled_posts WHERE is_regular = 1 AND status = 'pending'")
        active_media_paths = [row[0] for row in cursor.fetchall() if row[0]]
    
    for file in os.listdir(REGULAR_MEDIA_DIR):
        file_path = os.path.join(REGULAR_MEDIA_DIR, file)
        if file_path not in active_media_paths:
            try:
                os.unlink(file_path)
                print(f"Удалён orphan файл: {file_path}")
            except Exception as e:
                print(f"Ошибка удаления {file_path}: {e}")


def get_file_info(file_path: str) -> Optional[Dict[str, Any]]:
    """Получение информации о файле"""
    if not file_path or not os.path.exists(file_path):
        return None
    
    stat = os.stat(file_path)
    return {
        "path": file_path,
        "name": os.path.basename(file_path),
        "size": stat.st_size / (1024 * 1024),  # в МБ
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
    }