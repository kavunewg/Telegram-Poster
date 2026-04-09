"""
API для переводов
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["translations"])


@router.get("/api/translations")
async def get_translations(request: Request):
    """Получение всех переводов для клиентской части"""
    return {
        "ru": {
            # Навигация
            "my_bots": "Мои боты",
            "my_channels": "Мои каналы",
            "dashboard": "Панель управления",
            "logout": "Выйти",
            "back": "Назад",
            "create_post": "Создать пост",
            "scheduled_posts": "Отложенные посты",
            "statistics": "Статистика",
            "queue": "Очередь",
            "settings": "Настройки",
            "profile": "Профиль",
            
            # Приветствие
            "welcome_back": "С возвращением, {name}",
            "dashboard_subtitle": "Управляйте постами и каналами",
            
            # Статистика
            "total_posts": "Всего постов",
            "successful": "Успешно",
            "failed": "Ошибок",
            "channels": "Каналов",
            "total": "Всего",
            "success_rate": "Успешность",
            "bots": "Ботов",
            
            # Действия
            "publish_now": "Опубликовать сейчас",
            "schedule": "Запланировать",
            "make_regular": "Сделать регулярным",
            
            # Таблица постов
            "recent_posts": "Последние посты",
            "date": "Дата",
            "channel": "Канал",
            "text": "Текст",
            "status": "Статус",
            "view_all": "Все записи →",
            "no_posts": "Нет постов. Создайте первый пост!",
            "all_posts": "Все записи",
            
            # Статусы
            "success": "Успешно",
            "error": "Ошибка",
            "pending": "Ожидает",
            "processing": "Обрабатывается",
            "failed": "Ошибка",
            "regular": "Регулярный",
            
            # Модальные окна
            "post_statistics": "Статистика постов",
            "my_profile": "Мой профиль",
            "username": "Логин",
            "full_name": "Полное имя",
            "new_password": "Новый пароль",
            "confirm_password": "Подтверждение пароля",
            "save_changes": "Сохранить изменения",
            "cancel": "Отмена",
            "close": "Закрыть",
            "delete_account": "Удалить аккаунт",
            "edit": "Редактировать",
            "delete": "Удалить",
            "save": "Сохранить",
            
            # Сообщения
            "profile_updated": "Профиль обновлен",
            "error_updating_profile": "Ошибка обновления профиля",
            "passwords_do_not_match": "Пароли не совпадают",
            "username_already_taken": "Логин уже занят",
            "email_already_used": "Email уже используется",
            
            # Тема
            "theme": "Тема",
            "dark_theme": "Темная тема",
            "light_theme": "Светлая тема",
            "theme_toggle": "Тема",
            
            # Кнопки
            "retry": "Повторить",
            
            # Очередь
            "in_queue": "В очереди",
            "sending": "Отправляется",
            "error_status": "Ошибка",
            
            # VK
            "vk_channels": "VK Каналы",
            "add_vk_channel": "Добавить VK группу",
            "vk_group_id": "ID группы",
            "vk_access_token": "Ключ доступа",
            
            # Редактирование поста
            "edit_post": "Редактирование поста",
            "post_text": "Текст поста",
            "button_settings": "Настройки кнопки",
            "button_text": "Текст кнопки",
            "button_url": "Ссылка кнопки",
            "media_file": "Медиафайл",
            "select_file": "Выбрать файл",
            "remove": "Удалить",
            "regular_post": "Регулярный пост",
            "interval_hours": "Интервал (часы)",
            "interval_hint": "Как часто повторять пост (1-168 часов)",
            "end_date": "Дата окончания (опционально)",
            "end_time": "Время окончания (опционально)",
            "green": "Зеленая",
            "red": "Красная",
            "blue": "Синяя",
            "gray": "Серая",
            
            # Цвета кнопок
            "green": "Зеленая",
            "red": "Красная",
            "blue": "Синяя",
            "gray": "Серая",
            
            # Дополнительно
            "create_post_desc": "Создать новый пост",
            "statistics_desc": "Детальная статистика",
            "scheduled_desc": "Запланированные посты",
            "selected": "Выбрано",
            "no_scheduled_posts": "Нет запланированных постов"
        },
        "en": {
            # Navigation
            "my_bots": "My Bots",
            "my_channels": "My Channels",
            "dashboard": "Dashboard",
            "logout": "Logout",
            "back": "Back",
            "create_post": "Create Post",
            "scheduled_posts": "Scheduled Posts",
            "statistics": "Statistics",
            "queue": "Queue",
            "settings": "Settings",
            "profile": "Profile",
            
            # Welcome
            "welcome_back": "Welcome back, {name}",
            "dashboard_subtitle": "Manage your posts and channels",
            
            # Statistics
            "total_posts": "Total Posts",
            "successful": "Successful",
            "failed": "Failed",
            "channels": "Channels",
            "total": "Total",
            "success_rate": "Success Rate",
            "bots": "Bots",
            
            # Actions
            "publish_now": "Publish Now",
            "schedule": "Schedule",
            "make_regular": "Make Regular",
            
            # Posts table
            "recent_posts": "Recent Posts",
            "date": "Date",
            "channel": "Channel",
            "text": "Text",
            "status": "Status",
            "view_all": "View all →",
            "no_posts": "No posts yet. Create your first post!",
            "all_posts": "All Posts",
            
            # Statuses
            "success": "Success",
            "error": "Error",
            "pending": "Pending",
            "processing": "Processing",
            "failed": "Failed",
            "regular": "Regular",
            
            # Modals
            "post_statistics": "Post Statistics",
            "my_profile": "My Profile",
            "username": "Username",
            "full_name": "Full Name",
            "new_password": "New Password",
            "confirm_password": "Confirm Password",
            "save_changes": "Save Changes",
            "cancel": "Cancel",
            "close": "Close",
            "delete_account": "Delete Account",
            "edit": "Edit",
            "delete": "Delete",
            "save": "Save",
            
            # Messages
            "profile_updated": "Profile updated",
            "error_updating_profile": "Error updating profile",
            "passwords_do_not_match": "Passwords do not match",
            "username_already_taken": "Username already taken",
            "email_already_used": "Email already used",
            
            # Theme
            "theme": "Theme",
            "dark_theme": "Dark Theme",
            "light_theme": "Light Theme",
            "theme_toggle": "Theme",
            
            # Buttons
            "retry": "Retry",
            
            # Queue
            "in_queue": "In queue",
            "sending": "Sending",
            "error_status": "Error",
            
            # VK
            "vk_channels": "VK Channels",
            "add_vk_channel": "Add VK Group",
            "vk_group_id": "Group ID",
            "vk_access_token": "Access Token",
            
            # Edit post
            "edit_post": "Edit Post",
            "post_text": "Post Text",
            "button_settings": "Button Settings",
            "button_text": "Button Text",
            "button_url": "Button URL",
            "media_file": "Media File",
            "select_file": "Select File",
            "remove": "Remove",
            "regular_post": "Regular Post",
            "interval_hours": "Interval (hours)",
            "interval_hint": "How often to repeat the post (1-168 hours)",
            "end_date": "End Date (optional)",
            "end_time": "End Time (optional)",
            
            # Button colors
            "green": "Green",
            "red": "Red",
            "blue": "Blue",
            "gray": "Gray",
            
            # Additional
            "create_post_desc": "Create new post",
            "statistics_desc": "Detailed statistics",
            "scheduled_desc": "Scheduled posts",
            "selected": "Selected",
            "no_scheduled_posts": "No scheduled posts"
        }
    }