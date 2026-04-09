"""
UserRepository (clean, stable, production-ready)
"""
import secrets
import uuid
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from core.database import fetch_one, fetch_all, execute, insert, get_db_connection
from utils.helpers import hash_password, clean_email

logger = logging.getLogger(__name__)


class UserRepository:
    """Репозиторий для работы с пользователями и сессиями"""
    
    def __init__(self):
        self.table = "users"
        self.session_table = "sessions"

    # =========================
    # ПОЛУЧЕНИЕ ПОЛЬЗОВАТЕЛЕЙ
    # =========================
    
    def get_by_id(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        if not user_id:
            return None
        return fetch_one(
            f"SELECT * FROM {self.table} WHERE id = ?",
            (user_id,)
        )

    def get_by_username(self, username: str) -> Optional[Dict]:
        """Получение пользователя по логину"""
        if not username:
            return None
        
        print(f"🔍 Поиск пользователя: {username}")

        return fetch_one(
            f"SELECT id, username, password_hash, full_name, email, project_name, youtube_api_key, is_admin, created_at FROM {self.table} WHERE LOWER(username) = ?",
        (username.lower(),)
    )
        print(f"   Результат: {'найден' if result else 'не найден'}")
        if result:
            print(f"   id={result.get('id')}, username={result.get('username')}")
        
        return result


    def get_by_email(self, email: str) -> Optional[Dict]:
        """Получение пользователя по email"""
        if not email:
            return None
        return fetch_one(
            f"SELECT * FROM {self.table} WHERE LOWER(email) = ?",
            (email.lower(),)
        )

    def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей (для админа)"""
        return fetch_all(
            f"SELECT id, username, full_name, email, project_name, is_admin, created_at, created_by "
            f"FROM {self.table} ORDER BY created_at DESC"
        )

    def get_users_count(self) -> int:
        """Получение количества пользователей"""
        result = fetch_one(f"SELECT COUNT(*) as count FROM {self.table}")
        return result['count'] if result else 0

    # =========================
    # СЕССИИ
    # =========================
    
    def create_session(self, user_id: int) -> str:
        """Создание сессии для пользователя"""
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        expires_at = (datetime.now() + timedelta(days=7)).isoformat()
        
        insert(
            f"""
            INSERT INTO {self.session_table} (id, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, user_id, now, expires_at)
        )
        
        logger.debug(f"Сессия создана для user_id={user_id}")
        return session_id

    def get_by_session(self, session_id: str) -> Optional[Dict]:
        """Получение пользователя по ID сессии"""
        if not session_id:
            return None
        
        # Сначала проверяем сессию
        session = fetch_one(
            f"SELECT user_id FROM {self.session_table} WHERE id = ? AND (expires_at IS NULL OR expires_at > datetime('now'))",
            (session_id,)
        )
        
        if not session:
            return None
        
        # Получаем пользователя
        return self.get_by_id(session["user_id"])

    def delete_session(self, session_id: str) -> bool:
        """Удаление сессии (логаут)"""
        if not session_id:
            return False
        
        rows = execute(
            f"DELETE FROM {self.session_table} WHERE id = ?",
            (session_id,)
        )
        
        if rows:
            logger.debug(f"Сессия {session_id[:8]}... удалена")
        return rows > 0

    def cleanup_expired_sessions(self) -> int:
        """Очистка просроченных сессий"""
        rows = execute(
            f"DELETE FROM {self.session_table} WHERE expires_at <= datetime('now')"
        )
        if rows:
            logger.info(f"Очищено {rows} просроченных сессий")
        return rows

    def get_user_sessions(self, user_id: int) -> List[Dict]:
        """Получение всех сессий пользователя"""
        return fetch_all(
            f"SELECT id, created_at, expires_at FROM {self.session_table} WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )

    def revoke_all_user_sessions(self, user_id: int, except_session_id: str = None) -> int:
        """Отзыв всех сессий пользователя (кроме текущей)"""
        if except_session_id:
            rows = execute(
                f"DELETE FROM {self.session_table} WHERE user_id = ? AND id != ?",
                (user_id, except_session_id)
            )
        else:
            rows = execute(
                f"DELETE FROM {self.session_table} WHERE user_id = ?",
                (user_id,)
            )
        
        if rows:
            logger.info(f"Отозвано {rows} сессий для user_id={user_id}")
        return rows

    # =========================
    # СОЗДАНИЕ ПОЛЬЗОВАТЕЛЯ
    # =========================
    
    def create(
        self,
        username: str,
        password: str,
        full_name: str,
        email: str = None,
        project_name: str = None,
        created_by: int = None
    ) -> Optional[int]:
        """Создание нового пользователя"""
        
        # Нормализация данных
        username = username.lower().strip()
        email = clean_email(email)
        project_name = project_name or full_name or username
        
        # Проверки на существование
        if self.get_by_username(username):
            raise ValueError(f"Пользователь с логином '{username}' уже существует")
        
        if email and self.get_by_email(email):
            raise ValueError(f"Пользователь с email '{email}' уже существует")
        
        # Валидация пароля
        if len(password) < 6:
            raise ValueError("Пароль должен содержать минимум 6 символов")
        
        # Хеширование пароля
        password_hash = hash_password(password)
        now = datetime.now().isoformat()
        
        # Создание пользователя
        user_id = insert(
            f"""
            INSERT INTO {self.table} (
                username, password_hash, full_name, email, project_name,
                created_at, updated_at, created_by, is_admin
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                password_hash,
                full_name.strip(),
                email,
                project_name,
                now,
                now,
                created_by,
                0  # is_admin = False по умолчанию
            )
        )
        
        if user_id:
            logger.info(f"Создан пользователь: {username} (id={user_id})")
        
        return user_id

    def create_admin(
        self,
        username: str,
        password: str,
        full_name: str,
        email: str = None
    ) -> Optional[int]:
        """Создание администратора"""
        user_id = self.create(username, password, full_name, email)
        if user_id:
            execute(
                f"UPDATE {self.table} SET is_admin = 1 WHERE id = ?",
                (user_id,)
            )
            logger.info(f"Создан администратор: {username}")
        return user_id

    # =========================
    # ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
    # =========================
    
    def update_profile(
        self,
        user_id: int,
        username: str = None,
        full_name: str = None,
        email: str = None,
        project_name: str = None,
        youtube_api_key: str = None
    ) -> bool:
        """Обновление профиля пользователя"""
        
        # Получаем текущие данные
        current = self.get_by_id(user_id)
        if not current:
            raise ValueError(f"Пользователь с id={user_id} не найден")
        
        # Подготавливаем новые значения
        new_username = (username or current['username']).lower().strip()
        new_full_name = full_name or current['full_name']
        new_email = clean_email(email) if email is not None else current.get('email')
        new_project_name = project_name or current.get('project_name') or new_full_name
        new_youtube_key = youtube_api_key if youtube_api_key is not None else current.get('youtube_api_key')
        
        # Проверка уникальности username
        if new_username != current['username']:
            existing = self.get_by_username(new_username)
            if existing and existing['id'] != user_id:
                raise ValueError(f"Логин '{new_username}' уже занят")
        
        # Проверка уникальности email
        if new_email and new_email != current.get('email'):
            existing = self.get_by_email(new_email)
            if existing and existing['id'] != user_id:
                raise ValueError(f"Email '{new_email}' уже используется")
        
        # Обновление
        rows = execute(
            f"""
            UPDATE {self.table}
            SET username = ?, full_name = ?, email = ?, project_name = ?,
                youtube_api_key = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                new_username,
                new_full_name,
                new_email,
                new_project_name,
                new_youtube_key,
                datetime.now().isoformat(),
                user_id
            )
        )
        
        if rows:
            logger.info(f"Обновлён профиль пользователя {new_username} (id={user_id})")
        
        return rows > 0

    def update_password(self, user_id: int, new_password: str) -> bool:
        """Обновление пароля пользователя"""
        
        if len(new_password) < 6:
            raise ValueError("Пароль должен содержать минимум 6 символов")
        
        password_hash = hash_password(new_password)
        
        rows = execute(
            f"""
            UPDATE {self.table}
            SET password_hash = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                password_hash,
                datetime.now().isoformat(),
                user_id
            )
        )
        
        if rows:
            # При смене пароля отзываем все сессии кроме текущей
            # (текущую нужно обработать отдельно)
            logger.info(f"Пароль обновлён для user_id={user_id}")
        
        return rows > 0

    def update_youtube_api_key(self, user_id: int, youtube_api_key: str) -> bool:
        """Обновление YouTube API ключа"""
        rows = execute(
            f"""
            UPDATE {self.table}
            SET youtube_api_key = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                youtube_api_key,
                datetime.now().isoformat(),
                user_id
            )
        )
        return rows > 0

    def toggle_admin(self, user_id: int, is_admin: bool) -> bool:
        """Изменение прав администратора"""
        rows = execute(
            f"UPDATE {self.table} SET is_admin = ? WHERE id = ?",
            (1 if is_admin else 0, user_id)
        )
        return rows > 0

    # =========================
    # УДАЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
    # =========================
    
    def delete_user(self, user_id: int) -> bool:
        """Полное удаление пользователя и всех связанных данных"""
        try:
            # Удаляем связанные данные
            execute("DELETE FROM posts_stats WHERE user_id = ?", (user_id,))
            execute("DELETE FROM user_channels WHERE user_id = ?", (user_id,))
            execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            execute("DELETE FROM user_bots WHERE user_id = ?", (user_id,))
            execute("DELETE FROM scheduled_posts WHERE user_id = ?", (user_id,))
            execute("DELETE FROM post_queue WHERE user_id = ?", (user_id,))
            execute("DELETE FROM youtube_channels WHERE user_id = ?", (user_id,))
            
            # Удаляем пользователя
            rows = execute(f"DELETE FROM {self.table} WHERE id = ?", (user_id,))
            
            if rows:
                logger.info(f"Пользователь id={user_id} удалён")
            
            return rows > 0
            
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя {user_id}: {e}")
            return False

    def delete_user_by_username(self, username: str) -> bool:
        """Удаление пользователя по логину"""
        user = self.get_by_username(username)
        if not user:
            return False
        return self.delete_user(user['id'])

    # =========================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # =========================
    
    def verify_password(self, user_id: int, password: str) -> bool:
        """Проверка пароля пользователя"""
        from utils.helpers import verify_password
        
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        return verify_password(password, user.get('password_hash', ''))

    def change_password_with_verify(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Смена пароля с проверкой старого"""
        if not self.verify_password(user_id, old_password):
            raise ValueError("Неверный текущий пароль")
        
        return self.update_password(user_id, new_password)

    def search_users(self, query: str, limit: int = 20) -> List[Dict]:
        """Поиск пользователей по имени или логину"""
        search_pattern = f"%{query.lower()}%"
        return fetch_all(
            f"""
            SELECT id, username, full_name, email, is_admin, created_at
            FROM {self.table}
            WHERE LOWER(username) LIKE ? OR LOWER(full_name) LIKE ? OR LOWER(email) LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (search_pattern, search_pattern, search_pattern, limit)
        )


# =========================
# ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР
# =========================
user_repo = UserRepository()