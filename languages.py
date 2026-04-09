"""
Модуль локализации приложения
Поддерживает русский и английский языки
"""
import json
import os
from typing import Dict, Any, Optional
from functools import lru_cache


class Localization:
    """Модуль локализации приложения"""

    def __init__(self):
        self.current_language = 'ru'
        self.translations = {
            'ru': self._get_ru_translations(),
            'en': self._get_en_translations()
        }

    def _get_ru_translations(self) -> Dict[str, Any]:
        """Русские переводы"""
        return {
            # ========== ОБЩИЕ ==========
            'app_name': 'Telegram Постер',
            'back': '← Назад',
            'dashboard_link': '📊 Панель управления',
            'save': '💾 Сохранить',
            'cancel': 'Отмена',
            'delete': '🗑️ Удалить',
            'edit': '✏️ Редактировать',
            'create': '➕ Создать',
            'add': '➕ Добавить',
            'search': '🔍 Поиск',
            'loading': 'Загрузка...',
            'error': 'Ошибка',
            'success': 'Успешно',
            'warning': 'Внимание',
            'info': 'Информация',
            'close': 'Закрыть',
            'confirm': 'Подтвердить',
            'yes': 'Да',
            'no': 'Нет',
            'optional': 'опционально',
            'required': 'обязательно',
            'all': 'Все',
            'none': 'Нет',
            'actions': 'Действия',
            'status': 'Статус',
            'created': 'Создано',
            'updated': 'Обновлено',

            # ========== НАВИГАЦИЯ ==========
            'home': 'Главная',
            'my_bots': 'Мои боты',
            'my_channels': 'Мои каналы',
            'create_post': 'Создать пост',
            'scheduled_posts': 'Отложенные посты',
            'statistics': 'Статистика',
            'queue': 'Очередь',
            'settings': 'Настройки',
            'profile': 'Профиль',
            'admin_panel': 'Админ-панель',
            'logout': 'Выйти',
            'login': 'Вход',
            'register': 'Регистрация',

            # ========== АУТЕНТИФИКАЦИЯ ==========
            'username': 'Логин',
            'password': 'Пароль',
            'confirm_password': 'Подтверждение пароля',
            'full_name': 'Полное имя',
            'email': 'Email',
            'project_name': 'Название проекта',
            'remember_me': 'Запомнить меня',
            'forgot_password': 'Забыли пароль?',
            'login_button': 'Войти',
            'register_button': 'Зарегистрироваться',
            'no_account': 'Нет аккаунта?',
            'have_account': 'Уже есть аккаунт?',
            'current_password': 'Текущий пароль',
            'new_password': 'Новый пароль',
            'change_password': 'Сменить пароль',

            # Ошибки аутентификации
            'invalid_credentials': 'Неверный логин или пароль',
            'user_exists': 'Пользователь с таким логином уже существует',
            'email_exists': 'Пользователь с таким email уже существует',
            'passwords_not_match': 'Пароли не совпадают',
            'weak_password': 'Пароль должен содержать минимум 6 символов',
            'invalid_username': 'Логин должен содержать 3-20 символов (буквы, цифры, _, -)',
            'session_expired': 'Сессия истекла, войдите заново',

            # ========== ДАШБОРД ==========
            'welcome_back': 'С возвращением, {name}',
            'dashboard_subtitle': 'Управляйте постами, каналами и ботами',
            'total_users': 'Всего пользователей',
            'total_channels': 'Всего каналов',
            'total_posts': 'Всего постов',
            'success_posts': 'Успешных отправок',
            'failed_posts': 'Ошибок',
            'success_rate': 'Успешность',
            'stats': 'Статистика',
            'recent_activity': 'Последняя активность',
            'recent_posts': 'Последние посты',
            'today': 'Сегодня',
            'week': 'За неделю',
            'month': 'За месяц',
            'year': 'За год',
            'registrations': 'Регистраций',
            'no_recent_posts': 'Нет недавних постов',
            'view_all': 'Все записи →',

            # ========== КАНАЛЫ ==========
            'channels': 'Каналы',
            'add_channel': 'Добавить канал',
            'edit_channel': 'Редактировать канал',
            'channel_name': 'Название канала',
            'channel_id': 'ID канала',
            'channel_url': 'Ссылка на канал',
            'platform': 'Платформа',
            'telegram': 'Telegram',
            'max': 'MAX',
            'youtube': 'YouTube',
            'main_channel': 'Основной канал',
            'channel_added': 'Канал успешно добавлен',
            'channel_updated': 'Канал обновлен',
            'channel_deleted': 'Канал удален',
            'no_channels': 'Нет добавленных каналов',
            'no_telegram_channels': 'Нет Telegram каналов',
            'no_max_channels': 'Нет MAX каналов',
            'select_bot': 'Выберите бота',
            'no_bot': 'Нет бота',
            'channel_icon': 'Иконка канала',
            'target_channels': 'Целевые каналы',

            # ========== БОТЫ ==========
            'bots': 'Боты',
            'add_bot': 'Добавить бота',
            'edit_bot': 'Редактировать бота',
            'bot_name': 'Название бота',
            'bot_token': 'Токен бота',
            'bot_platform': 'Платформа бота',
            'bot_added': 'Бот успешно добавлен',
            'bot_updated': 'Бот обновлен',
            'bot_deleted': 'Бот удален',
            'no_bots': 'Нет добавленных ботов',
            'no_telegram_bots': 'Нет Telegram ботов',
            'no_max_bots': 'Нет MAX ботов',
            'no_youtube_bots': 'Нет YouTube ботов',
            'inn': 'ИНН',
            'youtube_api_key': 'YouTube API Key',
            'check_interval': 'Частота проверки (минуты)',
            'connected_channels': 'Привязанные каналы',
            'no_connected_channels': 'Нет привязанных каналов',
            'select_channel': 'Выберите канал',

            # ========== ПОСТЫ ==========
            'posts': 'Посты',
            'create_new_post': 'Создать новый пост',
            'edit_post': 'Редактировать пост',
            'post_text': 'Текст поста',
            'post_text_placeholder': 'Введите текст вашего сообщения... Поддерживается HTML разметка',
            'select_channels_first': 'Выберите каналы для публикации',
            'selected_channels': 'Выбрано каналов',
            'add_media': 'Добавить медиафайл',
            'media_file': 'Медиафайл',
            'drag_drop': 'Перетащите файл или нажмите для выбора',
            'photo_hint': 'Фото: JPG, PNG, GIF, WebP (до 10 МБ)',
            'video_hint': 'Видео: MP4, MOV, AVI (до 50 МБ)',
            'select_file': 'Выбрать файл',
            'remove_media': 'Удалить',
            
            # Кнопка в посте
            'button_settings': 'Настройки кнопки',
            'button_color': 'Цвет кнопки',
            'button_text_label': 'Текст кнопки',
            'button_url_label': 'Ссылка кнопки',
            'button_style_green': 'Зеленая',
            'button_style_red': 'Красная',
            'button_style_blue': 'Синяя',
            'button_style_gray': 'Серая',
            'button_required_warning': 'Текст и ссылка обязательны при выборе цвета кнопки',
            'button_text_placeholder': 'Например: Перейти на сайт',
            'button_url_placeholder': 'https://...',
            
            # Предпросмотр
            'preview': 'Предпросмотр',
            'preview_channel': 'Выберите каналы',
            'preview_text_placeholder': 'Введите текст...',
            
            # Действия с постами
            'publish_now': 'Опубликовать сейчас',
            'schedule': 'Запланировать',
            'make_regular': 'Сделать регулярным',
            'publishing_post': 'Публикация...',
            'scheduling_post': 'Планирование...',
            'post_published': 'Пост успешно опубликован!',
            'post_scheduled': 'Пост успешно запланирован!',
            'post_deleted': 'Пост удален',
            'regular_post_created': 'Регулярный пост создан',
            'publish_error': 'Ошибка публикации',
            'schedule_error': 'Ошибка планирования',
            
            # ========== ОТЛОЖЕННЫЕ ПОСТЫ ==========
            'scheduled_posts_title': 'Отложенные посты',
            'scheduled_for': 'Запланировано на',
            'date': 'Дата',
            'time': 'Время',
            'select_date': 'Выберите дату',
            'select_time': 'Выберите время',
            'start_date': 'Дата начала',
            'start_time': 'Время начала',
            'end_date': 'Дата окончания',
            'end_time': 'Время окончания',
            'interval_hours': 'Интервал (часы)',
            'interval_hint': 'Как часто повторять пост (1-168 часов)',
            'end_date_hint': 'Оставьте пустым для бесконечного повторения',
            'end_time_hint': 'Последний пост будет отправлен в это время',
            'no_scheduled_posts': 'Нет отложенных постов',
            'create_first_scheduled': 'Создайте первый отложенный пост',
            'time_minimum_warning': 'Время должно быть не ранее чем через 5 минут от текущего момента',
            'schedule_modal_title': 'Запланировать пост',
            'regular_modal_title': 'Настройки регулярного поста',

            # ========== СТАТИСТИКА ==========
            'detailed_stats': 'Детальная статистика',
            'by_channel': 'По каналам',
            'total_sent': 'Всего отправлено',
            'success_count': 'Успешно',
            'failed_count': 'Ошибок',
            'post_stats': 'Статистика постов',
            'channel_stats': 'Статистика по каналам',
            'no_stats': 'Нет данных для отображения',
            'last_30_days': 'Последние 30 дней',

            # ========== ОЧЕРЕДЬ ==========
            'queue_title': 'Очередь отправки',
            'queue_empty': 'Очередь пуста',
            'queue_refresh': 'Обновить',
            'task_id': 'ID задачи',
            'task_status': 'Статус',
            'task_attempts': 'Попыток',
            'task_error': 'Ошибка',
            'task_created': 'Создана',
            'retry_task': 'Повторить',
            'delete_task': 'Удалить',
            'status_pending': 'В очереди',
            'status_processing': 'Отправляется',
            'status_retry': 'Ошибка (повтор)',
            'status_success': 'Отправлено',
            'status_failed': 'Ошибка',

            # ========== ПРОФИЛЬ ==========
            'my_profile': 'Мой профиль',
            'profile_settings': 'Настройки профиля',
            'profile_updated': 'Профиль обновлен',
            'profile_update_error': 'Ошибка обновления профиля',
            'delete_account': 'Удалить аккаунт',
            'delete_account_confirm': 'Вы уверены, что хотите удалить аккаунт? Это действие необратимо!',
            'account_deleted': 'Аккаунт удален',
            'youtube_api_key_label': 'YouTube API Key (для мониторинга)',
            'youtube_api_key_hint': 'Нужен для отслеживания новых видео на YouTube',

            # ========== ТЕМА ==========
            'theme_settings': 'Тема оформления',
            'dark_theme': 'Темная тема',
            'light_theme': 'Светлая тема',
            'theme_toggle': 'Сменить тему',

            # ========== ЯЗЫК ==========
            'language_settings': 'Язык',
            'russian': 'Русский',
            'english': 'English',
            'language_switched': 'Язык изменен',

            # ========== АДМИН-ПАНЕЛЬ ==========
            'user_management': 'Управление пользователями',
            'add_user': 'Добавить пользователя',
            'edit_user': 'Редактировать пользователя',
            'user_id': 'ID пользователя',
            'user_role': 'Роль',
            'admin': 'Администратор',
            'user': 'Пользователь',
            'reset_user_password': 'Сбросить пароль пользователя',
            'delete_user_confirm': 'Удалить пользователя?',
            'user_deleted': 'Пользователь удален',
            'password_reset': 'Пароль сброшен',
            'user_added': 'Пользователь добавлен',

            # ========== YOUTUBE МОНИТОРИНГ ==========
            'youtube_monitoring': 'YouTube мониторинг',
            'add_youtube_channel': 'Добавить YouTube канал',
            'edit_youtube_channel': 'Редактировать YouTube канал',
            'youtube_channel_url': 'YouTube URL или ID',
            'youtube_channel_name': 'Название канала',
            'post_template': 'Шаблон поста',
            'post_template_hint': 'Переменные: {video_title}, {video_url}, {channel_name}, {views}, {video_description}',
            'include_description': 'Включать описание видео',
            'active': 'Активен',
            'inactive': 'Неактивен',
            'enable': 'Включить',
            'disable': 'Отключить',
            'last_video': 'Последнее видео',
            'last_checked': 'Последняя проверка',
            'force_check': 'Проверить сейчас',
            'edit_youtube_channel': 'Редактировать YouTube канал',
            'post_template': 'Шаблон поста',
            'template_vars': 'Переменные: {video_title}, {video_url}, {channel_name}, {views}, {video_description}',
            'include_description': 'Включать описание видео',

            # ========== ОБРАБОТКА ==========
            'processing': 'Обработка',
            'preparing_post': 'Подготовка поста...',
            'uploading_media': 'Загрузка медиафайла...',
            'sending_to_telegram': 'Отправка в Telegram...',
            'sending_to_max': 'Отправка в MAX...',
            'completing': 'Завершение...',
            'processing_complete': 'Публикация завершена!',
            'processing_error': 'Ошибка!',

            # ========== СООБЩЕНИЯ ОБ ОШИБКАХ ==========
            'no_channels_selected': 'Выберите хотя бы один канал',
            'no_post_text': 'Введите текст поста',
            'no_bot_for_channel': 'Для канала {channel} не найден бот',
            'no_bot_token': 'Отсутствует токен бота',
            'no_channel_id': 'Отсутствует ID канала',
            'invalid_channel_id': 'Неверный ID канала',
            'network_error': 'Ошибка сети',
            'server_error': 'Ошибка сервера',
            'access_denied': 'Доступ запрещен',
            'not_found': 'Не найдено',
        }

    def _get_en_translations(self) -> Dict[str, Any]:
        """Английские переводы"""
        return {
            # ========== COMMON ==========
            'app_name': 'Telegram Poster',
            'back': '← Back',
            'dashboard_link': '📊 Dashboard',
            'save': '💾 Save',
            'cancel': 'Cancel',
            'delete': '🗑️ Delete',
            'edit': '✏️ Edit',
            'create': '➕ Create',
            'add': '➕ Add',
            'search': '🔍 Search',
            'loading': 'Loading...',
            'error': 'Error',
            'success': 'Success',
            'warning': 'Warning',
            'info': 'Info',
            'close': 'Close',
            'confirm': 'Confirm',
            'yes': 'Yes',
            'no': 'No',
            'optional': 'optional',
            'required': 'required',
            'all': 'All',
            'none': 'None',
            'actions': 'Actions',
            'status': 'Status',
            'created': 'Created',
            'updated': 'Updated',

            # ========== NAVIGATION ==========
            'home': 'Home',
            'my_bots': 'My Bots',
            'my_channels': 'My Channels',
            'create_post': 'Create Post',
            'scheduled_posts': 'Scheduled Posts',
            'statistics': 'Statistics',
            'queue': 'Queue',
            'settings': 'Settings',
            'profile': 'Profile',
            'admin_panel': 'Admin Panel',
            'logout': 'Logout',
            'login': 'Login',
            'register': 'Register',

            # ========== AUTHENTICATION ==========
            'username': 'Username',
            'password': 'Password',
            'confirm_password': 'Confirm Password',
            'full_name': 'Full Name',
            'email': 'Email',
            'project_name': 'Project Name',
            'remember_me': 'Remember me',
            'forgot_password': 'Forgot password?',
            'login_button': 'Log in',
            'register_button': 'Sign up',
            'no_account': "Don't have an account?",
            'have_account': 'Already have an account?',
            'current_password': 'Current Password',
            'new_password': 'New Password',
            'change_password': 'Change Password',

            # Authentication errors
            'invalid_credentials': 'Invalid username or password',
            'user_exists': 'User with this username already exists',
            'email_exists': 'User with this email already exists',
            'passwords_not_match': 'Passwords do not match',
            'weak_password': 'Password must be at least 6 characters',
            'invalid_username': 'Username must be 3-20 characters (letters, numbers, _, -)',
            'session_expired': 'Session expired, please login again',

            # ========== DASHBOARD ==========
            'welcome_back': 'Welcome back, {name}',
            'dashboard_subtitle': 'Manage your posts, channels and bots',
            'total_users': 'Total Users',
            'total_channels': 'Total Channels',
            'total_posts': 'Total Posts',
            'success_posts': 'Successful Posts',
            'failed_posts': 'Failed',
            'success_rate': 'Success Rate',
            'stats': 'Statistics',
            'recent_activity': 'Recent Activity',
            'recent_posts': 'Recent Posts',
            'today': 'Today',
            'week': 'This Week',
            'month': 'This Month',
            'year': 'This Year',
            'registrations': 'Registrations',
            'no_recent_posts': 'No recent posts',
            'view_all': 'View all →',

            # ========== CHANNELS ==========
            'channels': 'Channels',
            'add_channel': 'Add Channel',
            'edit_channel': 'Edit Channel',
            'channel_name': 'Channel Name',
            'channel_id': 'Channel ID',
            'channel_url': 'Channel URL',
            'platform': 'Platform',
            'telegram': 'Telegram',
            'max': 'MAX',
            'youtube': 'YouTube',
            'main_channel': 'Main Channel',
            'channel_added': 'Channel added successfully',
            'channel_updated': 'Channel updated',
            'channel_deleted': 'Channel deleted',
            'no_channels': 'No channels added',
            'no_telegram_channels': 'No Telegram channels',
            'no_max_channels': 'No MAX channels',
            'select_bot': 'Select bot',
            'no_bot': 'No bot',
            'channel_icon': 'Channel icon',
            'target_channels': 'Target channels',

            # ========== BOTS ==========
            'bots': 'Bots',
            'add_bot': 'Add Bot',
            'edit_bot': 'Edit Bot',
            'bot_name': 'Bot Name',
            'bot_token': 'Bot Token',
            'bot_platform': 'Bot Platform',
            'bot_added': 'Bot added successfully',
            'bot_updated': 'Bot updated',
            'bot_deleted': 'Bot deleted',
            'no_bots': 'No bots added',
            'no_telegram_bots': 'No Telegram bots',
            'no_max_bots': 'No MAX bots',
            'no_youtube_bots': 'No YouTube bots',
            'inn': 'INN',
            'youtube_api_key': 'YouTube API Key',
            'check_interval': 'Check interval (minutes)',
            'connected_channels': 'Connected Channels',
            'no_connected_channels': 'No connected channels',
            'select_channel': 'Select channel',

            # ========== POSTS ==========
            'posts': 'Posts',
            'create_new_post': 'Create New Post',
            'edit_post': 'Edit Post',
            'post_text': 'Post Text',
            'post_text_placeholder': 'Enter your message... HTML formatting supported',
            'select_channels_first': 'Select channels for publishing',
            'selected_channels': 'Selected channels',
            'add_media': 'Add Media',
            'media_file': 'Media File',
            'drag_drop': 'Drag & drop or click to select',
            'photo_hint': 'Photo: JPG, PNG, GIF, WebP (up to 10 MB)',
            'video_hint': 'Video: MP4, MOV, AVI (up to 50 MB)',
            'select_file': 'Select File',
            'remove_media': 'Remove',
            
            # Post button
            'button_settings': 'Button Settings',
            'button_color': 'Button Color',
            'button_text_label': 'Button Text',
            'button_url_label': 'Button URL',
            'button_style_green': 'Green',
            'button_style_red': 'Red',
            'button_style_blue': 'Blue',
            'button_style_gray': 'Gray',
            'button_required_warning': 'Text and URL are required when button color is selected',
            'button_text_placeholder': 'e.g., Visit website',
            'button_url_placeholder': 'https://...',
            
            # Preview
            'preview': 'Preview',
            'preview_channel': 'Select channels',
            'preview_text_placeholder': 'Enter text...',
            
            # Post actions
            'publish_now': 'Publish Now',
            'schedule': 'Schedule',
            'make_regular': 'Make Regular',
            'publishing_post': 'Publishing...',
            'scheduling_post': 'Scheduling...',
            'post_published': 'Post published successfully!',
            'post_scheduled': 'Post scheduled successfully!',
            'post_deleted': 'Post deleted',
            'regular_post_created': 'Regular post created',
            'publish_error': 'Publishing error',
            'schedule_error': 'Scheduling error',

            # ========== SCHEDULED POSTS ==========
            'scheduled_posts_title': 'Scheduled Posts',
            'scheduled_for': 'Scheduled for',
            'date': 'Date',
            'time': 'Time',
            'select_date': 'Select date',
            'select_time': 'Select time',
            'start_date': 'Start Date',
            'start_time': 'Start Time',
            'end_date': 'End Date',
            'end_time': 'End Time',
            'interval_hours': 'Interval (hours)',
            'interval_hint': 'How often to repeat the post (1-168 hours)',
            'end_date_hint': 'Leave empty for infinite repetition',
            'end_time_hint': 'The last post will be sent at this time',
            'no_scheduled_posts': 'No scheduled posts',
            'create_first_scheduled': 'Create your first scheduled post',
            'time_minimum_warning': 'Scheduled time must be at least 5 minutes from now',
            'schedule_modal_title': 'Schedule Post',
            'regular_modal_title': 'Regular Post Settings',

            # ========== STATISTICS ==========
            'detailed_stats': 'Detailed Statistics',
            'by_channel': 'By Channel',
            'total_sent': 'Total Sent',
            'success_count': 'Success',
            'failed_count': 'Failed',
            'post_stats': 'Post Statistics',
            'channel_stats': 'Channel Statistics',
            'no_stats': 'No data to display',
            'last_30_days': 'Last 30 days',

            # ========== QUEUE ==========
            'queue_title': 'Send Queue',
            'queue_empty': 'Queue is empty',
            'queue_refresh': 'Refresh',
            'task_id': 'Task ID',
            'task_status': 'Status',
            'task_attempts': 'Attempts',
            'task_error': 'Error',
            'task_created': 'Created',
            'retry_task': 'Retry',
            'delete_task': 'Delete',
            'status_pending': 'In queue',
            'status_processing': 'Sending',
            'status_retry': 'Error (retry)',
            'status_success': 'Sent',
            'status_failed': 'Failed',

            # ========== PROFILE ==========
            'my_profile': 'My Profile',
            'profile_settings': 'Profile Settings',
            'profile_updated': 'Profile updated',
            'profile_update_error': 'Profile update error',
            'delete_account': 'Delete Account',
            'delete_account_confirm': 'Are you sure you want to delete your account? This action is irreversible!',
            'account_deleted': 'Account deleted',
            'youtube_api_key_label': 'YouTube API Key (for monitoring)',
            'youtube_api_key_hint': 'Required for tracking new videos on YouTube',

            # ========== THEME ==========
            'theme_settings': 'Theme',
            'dark_theme': 'Dark Theme',
            'light_theme': 'Light Theme',
            'theme_toggle': 'Switch theme',
            # В словаре переводов добавьте:
            'theme_toggle': '🌙 Тема',
            'theme_toggle': '🌙 Theme',

            # ========== LANGUAGE ==========
            'language_settings': 'Language',
            'russian': 'Русский',
            'english': 'English',
            'language_switched': 'Language changed',

            # ========== ADMIN PANEL ==========
            'user_management': 'User Management',
            'add_user': 'Add User',
            'edit_user': 'Edit User',
            'user_id': 'User ID',
            'user_role': 'Role',
            'admin': 'Administrator',
            'user': 'User',
            'reset_user_password': 'Reset User Password',
            'delete_user_confirm': 'Delete user?',
            'user_deleted': 'User deleted',
            'password_reset': 'Password reset',
            'user_added': 'User added',

            # ========== YOUTUBE MONITORING ==========
            'youtube_monitoring': 'YouTube Monitoring',
            'add_youtube_channel': 'Add YouTube Channel',
            'edit_youtube_channel': 'Edit YouTube Channel',
            'youtube_channel_url': 'YouTube URL or ID',
            'youtube_channel_name': 'Channel Name',
            'post_template': 'Post Template',
            'post_template_hint': 'Variables: {video_title}, {video_url}, {channel_name}, {views}, {video_description}',
            'include_description': 'Include video description',
            'active': 'Active',
            'inactive': 'Inactive',
            'enable': 'Enable',
            'disable': 'Disable',
            'last_video': 'Last video',
            'last_checked': 'Last checked',
            'force_check': 'Check now',
            'edit_youtube_channel': 'Edit YouTube Channel',
            'post_template': 'Post Template',
            'template_vars': 'Variables: {video_title}, {video_url}, {channel_name}, {views}, {video_description}',
            'include_description': 'Include video description',

            # ========== PROCESSING ==========
            'processing': 'Processing',
            'preparing_post': 'Preparing post...',
            'uploading_media': 'Uploading media...',
            'sending_to_telegram': 'Sending to Telegram...',
            'sending_to_max': 'Sending to MAX...',
            'completing': 'Completing...',
            'processing_complete': 'Publishing completed!',
            'processing_error': 'Error!',

            # ========== ERROR MESSAGES ==========
            'no_channels_selected': 'Select at least one channel',
            'no_post_text': 'Enter post text',
            'no_bot_for_channel': 'No bot found for channel {channel}',
            'no_bot_token': 'Bot token missing',
            'no_channel_id': 'Channel ID missing',
            'invalid_channel_id': 'Invalid channel ID',
            'network_error': 'Network error',
            'server_error': 'Server error',
            'access_denied': 'Access denied',
            'not_found': 'Not found',
        }

    def get(self, key: str, lang: str = None, **kwargs) -> str:
        """Получить перевод по ключу с подстановкой параметров"""
        lang = lang or self.current_language
        text = self.translations.get(lang, {}).get(key, key)
        
        # Подставляем параметры {name}
        if kwargs:
            for param, value in kwargs.items():
                text = text.replace(f'{{{param}}}', str(value))
        
        return text

    def set_language(self, lang: str) -> bool:
        """Установить текущий язык"""
        if lang in self.translations:
            self.current_language = lang
            return True
        return False

    def get_language(self) -> str:
        """Получить текущий язык"""
        return self.current_language

    def get_all_languages(self) -> list:
        """Получить список доступных языков"""
        return list(self.translations.keys())


# Глобальный экземпляр
loc = Localization()


# Функции для использования в коде и шаблонах
def t(key: str, lang: str = None, **kwargs) -> str:
    """Функция перевода для использования в коде"""
    return loc.get(key, lang, **kwargs)


def get_lang_from_request(request) -> str:
    """Получить язык из cookie или заголовков"""
    # Проверяем cookie
    lang = request.cookies.get('language') or request.cookies.get('lang')
    if lang and lang in loc.get_all_languages():
        return lang
    
    # Проверяем заголовок Accept-Language
    accept_lang = request.headers.get('Accept-Language', '')
    if accept_lang:
        for lang_code in ['ru', 'en']:
            if lang_code in accept_lang:
                return lang_code
    
    # По умолчанию русский
    return 'ru'


def get_lang(request):
    """Алиас для get_lang_from_request"""
    return get_lang_from_request(request)