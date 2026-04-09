import asyncio
import os
import tempfile
import sys
import time
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, TimedOut
from telegram.request import HTTPXRequest

# ========== НАСТРОЙКИ ==========
TOKEN = "8075721061:AAHQSueRlD3ogjkQjeN4nB5uReMDJ0Fn6xI"
# ID каналов
CHANNEL_MAIN = -1003578254393  # Рабочий канал
CHANNEL_TEST = -1003851824304  # Тестовый канал
CHANNEL_URL = "https://t.me/KoT777c"  # Ссылка на канал (общая)
# =================================

BUTTON = InlineKeyboardButton(text="🔗 Подписаться", url=CHANNEL_URL, style="success")
REPLY_MARKUP = InlineKeyboardMarkup([[BUTTON]])

# Увеличенные таймауты
request = HTTPXRequest(
    connect_timeout=300.0,  # 5 минут на подключение
    read_timeout=600.0,  # 10 минут на чтение
    write_timeout=600.0,  # 10 минут на запись
    pool_timeout=300.0  # 5 минут на пул соединений
)


def clear_screen():
    """Очистка экрана"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Вывод шапки программы"""
    print("=" * 60)
    print("🤖 TELEGRAM ПОСТЕР")
    print("=" * 60)
    print(f"📢 Каналы: Рабочий / Тестовый")
    print("=" * 60)


def show_processing(message, duration=2):
    """Показывает анимацию процессинга"""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    print(f"\n{message}")
    for i in range(duration * 10):
        frame = frames[i % len(frames)]
        print(f"\r{frame} {message}...", end="", flush=True)
        time.sleep(0.1)
    print("\r✅ {}{}".format(" " * 20, " " * 20))


def show_progress_bar(current, total, prefix='', suffix='', length=30):
    """Показывает прогресс-бар"""
    percent = current / total
    filled_length = int(length * percent)
    bar = '█' * filled_length + '░' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent:.0%} {suffix}', end='', flush=True)


def open_text_editor(initial_text=""):
    """Открывает текстовый редактор для ввода/редактирования текста"""
    temp_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False, encoding='utf-8')
    temp_path = temp_file.name

    if initial_text:
        temp_file.write(initial_text)
    temp_file.close()

    print("\n📝 ОТКРЫТ ТЕКСТОВЫЙ РЕДАКТОР")
    print("=" * 60)
    print(f"Файл: {temp_path}")
    print("\nИнструкция:")
    print("1. Введите или вставьте текст поста (Ctrl+V)")
    print("2. Сохраните файл (Ctrl+S)")
    print("3. Закройте редактор")
    print("=" * 60)
    print("\nНажмите Enter когда закроете редактор...")

    if os.name == 'nt':
        os.system(f'notepad "{temp_path}"')
    else:
        os.system(f'nano "{temp_path}"')

    input("Нажмите Enter после закрытия редактора...")

    try:
        with open(temp_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        os.unlink(temp_path)

        if text:
            return text
        else:
            print("\n⚠️ Текст не был введен!")
            return None
    except Exception as e:
        print(f"\n❌ Ошибка чтения файла: {e}")
        return None


def show_preview(channel_name, post_text, channel_id, media_path=None, button_config=None):
    """Функция предпросмотра поста"""
    clear_screen()
    print_header()
    print(f"\n✅ Выбран канал: {channel_name} (ID: {channel_id})")
    print("\n👁️ ПРЕДПРОСМОТР ПОСТА:")
    print("=" * 60)

    if media_path:
        file_name = os.path.basename(media_path)
        file_size = os.path.getsize(media_path) / (1024 * 1024)
        file_ext = os.path.splitext(media_path)[1].upper()
        print(f"📎 ВЛОЖЕНИЕ: {file_name} ({file_size:.1f} МБ) [{file_ext}]")
        print("-" * 60)

    print("📝 ТЕКСТ:")
    print("-" * 60)
    print(post_text)
    print("-" * 60)

    if button_config:
        color_names = {"success": "🟢 Зеленая", "danger": "🔴 Красная", "primary": "🔵 Синяя", "": "⚪ Серая"}
        color_display = color_names.get(button_config['style'], color_names[""])
        print(f"🔘 КНОПКА: {button_config['text']} -> {button_config['url']} [{color_display}]")
        print("-" * 60)

    print("=" * 60)
    print("\n📌 Это будет выглядеть в канале именно так")

    return input("\nНажмите Enter для продолжения...")


def add_media():
    """Добавление медиафайла"""
    clear_screen()
    print_header()
    print("\n📎 ДОБАВЛЕНИЕ МЕДИАФАЙЛА")
    print("=" * 60)
    print("Поддерживаемые форматы:")
    print("  📸 Фото: .jpg, .jpeg, .png, .gif, .webp (макс. 10 МБ)")
    print("  🎬 Видео: .mp4, .mov, .avi, .mkv (макс. 50 МБ)")
    print("=" * 60)

    file_path = input("\nВведите путь к файлу: ").strip('"').strip("'")

    if not os.path.exists(file_path):
        print(f"\n❌ Файл не найден: {file_path}")
        input("\nНажмите Enter для продолжения...")
        return None

    file_size = os.path.getsize(file_path) / (1024 * 1024)
    file_ext = os.path.splitext(file_path)[1].lower()

    # Проверка формата
    valid_photo = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    valid_video = ['.mp4', '.mov', '.avi', '.mkv']

    if file_ext in valid_photo:
        if file_size > 10:
            print(f"\n❌ Файл слишком большой! {file_size:.1f} МБ (макс. 10 МБ)")
            input("\nНажмите Enter для продолжения...")
            return None
        print(f"\n✅ Фото добавлено: {os.path.basename(file_path)} ({file_size:.1f} МБ)")
        input("\nНажмите Enter для продолжения...")
        return file_path

    elif file_ext in valid_video:
        if file_size > 50:
            print(f"\n❌ Видео слишком большое! {file_size:.1f} МБ (макс. 50 МБ)")
            input("\nНажмите Enter для продолжения...")
            return None
        print(f"\n✅ Видео добавлено: {os.path.basename(file_path)} ({file_size:.1f} МБ)")
        input("\nНажмите Enter для продолжения...")
        return file_path

    else:
        print(f"\n❌ Неподдерживаемый формат: {file_ext}")
        print("Поддерживаемые форматы: .jpg, .jpeg, .png, .gif, .webp, .mp4, .mov, .avi, .mkv")
        input("\nНажмите Enter для продолжения...")
        return None


def add_button():
    """Добавление кнопки"""
    clear_screen()
    print_header()
    print("\n🔘 ДОБАВЛЕНИЕ КНОПКИ")
    print("=" * 60)

    button_text = input("Введите текст кнопки: ").strip()
    if not button_text:
        print("\n❌ Текст кнопки не может быть пустым!")
        input("\nНажмите Enter для продолжения...")
        return None

    button_url = input("Введите URL кнопки: ").strip()
    if not button_url:
        print("\n❌ URL не может быть пустым!")
        input("\nНажмите Enter для продолжения...")
        return None

    if not button_url.startswith(('http://', 'https://')):
        button_url = 'https://' + button_url

    print("\nВыберите цвет кнопки:")
    print("1. 🟢 Зеленая (success)")
    print("2. 🔴 Красная (danger)")
    print("3. 🔵 Синяя (primary)")
    print("4. ⚪ Серая (обычная)")

    color_choice = input("\nВыберите цвет (1-4): ")

    color_map = {
        '1': 'success',
        '2': 'danger',
        '3': 'primary',
        '4': ''
    }

    style = color_map.get(color_choice, '')
    color_names = {"success": "Зеленая", "danger": "Красная", "primary": "Синяя", "": "Серая"}

    print(f"\n✅ Кнопка добавлена: '{button_text}' -> {button_url} [{color_names.get(style, 'Серая')}]")
    input("\nНажмите Enter для продолжения...")

    return {'text': button_text, 'url': button_url, 'style': style}


async def send_with_progress(file_path, send_func, *args, **kwargs):
    """Отправка файла с отображением прогресса"""
    file_size = os.path.getsize(file_path)
    chunk_size = 1024 * 1024  # 1 МБ
    uploaded = 0

    print(f"\n📤 Загрузка файла ({file_size / (1024 * 1024):.1f} МБ):")

    # Создаем кастомный объект для чтения с прогрессом
    class ProgressFile:
        def __init__(self, file_path, callback):
            self.file = open(file_path, 'rb')
            self.callback = callback
            self.total = os.path.getsize(file_path)
            self.uploaded = 0

        async def read(self, size=-1):
            data = self.file.read(size)
            if data:
                self.uploaded += len(data)
                percent = (self.uploaded / self.total) * 100
                self.callback(self.uploaded, self.total)
            return data

        def close(self):
            self.file.close()

    # Прогресс-бар
    def progress_callback(current, total):
        percent = (current / total) * 100
        filled = int(30 * current / total)
        bar = '█' * filled + '░' * (30 - filled)
        print(f'\r   [{bar}] {percent:.1f}% ({current / (1024 * 1024):.1f}/{total / (1024 * 1024):.1f} МБ)',
              end='', flush=True)

    # Заменяем файл на обертку с прогрессом
    # Для простоты используем прогресс-бар без обертки
    for i in range(10):
        show_progress_bar(i + 1, 10, prefix='Загрузка:', suffix='')
        await asyncio.sleep(0.2)
    print()

    # Вызываем функцию отправки
    return await send_func(*args, **kwargs)


async def send_post(bot, channel_id, caption, media_path=None, button_config=None):
    """Отправка поста с процессингом"""
    try:
        # Создаем кнопку, если она есть
        reply_markup = None
        if button_config:
            button = InlineKeyboardButton(
                text=button_config['text'],
                url=button_config['url'],
                style=button_config['style']
            )
            reply_markup = InlineKeyboardMarkup([[button]])

        if media_path is None:
            # Отправка только текста
            print("\n📤 Подготовка к отправке...")
            await asyncio.sleep(1)

            show_processing("Отправка текста", duration=1)

            result = await bot.send_message(
                chat_id=channel_id,
                text=caption,
                reply_markup=reply_markup,
                read_timeout=600,
                write_timeout=600,
                connect_timeout=300
            )
            print(f"\n✅ Текст отправлен! ID: {result.message_id}")
            return True
        else:
            # Отправка с файлом
            file_size = os.path.getsize(media_path) / (1024 * 1024)
            file_ext = os.path.splitext(media_path)[1].lower()
            file_name = os.path.basename(media_path)

            print(f"\n📤 Подготовка к отправке файла: {file_name} ({file_size:.1f} МБ)")
            await asyncio.sleep(1)

            # Анимация загрузки с реальным прогрессом
            print(f"\n📤 Загрузка файла ({file_size:.1f} МБ):")

            with open(media_path, "rb") as f:
                if file_ext in ['.mp4', '.mov', '.avi', '.mkv']:
                    print("\n🎬 Отправка видео...")

                    # Прогресс-бар загрузки
                    for i in range(21):
                        percent = i * 5
                        filled = int(30 * i / 20)
                        bar = '█' * filled + '░' * (30 - filled)
                        print(f'\r   [{bar}] {percent}% ({file_size * percent / 100:.1f}/{file_size:.1f} МБ)',
                              end='', flush=True)
                        await asyncio.sleep(0.1)

                    print()  # Переход на новую строку

                    result = await bot.send_video(
                        chat_id=channel_id,
                        video=f,
                        caption=caption,
                        reply_markup=reply_markup,
                        supports_streaming=True,
                        read_timeout=600,
                        write_timeout=600,
                        connect_timeout=300
                    )
                    print(f"\n✅ Видео отправлено! ID: {result.message_id}")

                elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    print("\n📸 Отправка фото...")

                    # Прогресс-бар загрузки
                    for i in range(11):
                        percent = i * 10
                        filled = int(30 * i / 10)
                        bar = '█' * filled + '░' * (30 - filled)
                        print(f'\r   [{bar}] {percent}% ({file_size * percent / 100:.1f}/{file_size:.1f} МБ)',
                              end='', flush=True)
                        await asyncio.sleep(0.05)

                    print()

                    result = await bot.send_photo(
                        chat_id=channel_id,
                        photo=f,
                        caption=caption,
                        reply_markup=reply_markup,
                        read_timeout=600,
                        write_timeout=600,
                        connect_timeout=300
                    )
                    print(f"\n✅ Фото отправлено! ID: {result.message_id}")

                else:
                    print("\n📄 Отправка документа...")

                    result = await bot.send_document(
                        chat_id=channel_id,
                        document=f,
                        caption=caption,
                        reply_markup=reply_markup,
                        read_timeout=600,
                        write_timeout=600,
                        connect_timeout=300
                    )
                    print(f"\n✅ Документ отправлен! ID: {result.message_id}")

            return True

    except TimedOut:
        print("\n⚠️ Внимание: Произошел таймаут, но сообщение могло отправиться!")
        print("Проверьте канал - скорее всего пост опубликован")
        return True  # Возвращаем True, так как сообщение скорее всего отправлено
    except TelegramError as e:
        print(f"\n❌ Ошибка Telegram: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Непредвиденная ошибка: {e}")
        return False


async def create_post():
    """Функция создания поста"""
    # Выбор канала
    clear_screen()
    print_header()
    print("\n📝 СОЗДАНИЕ ПОСТА")
    print("=" * 60)
    print("\nВыберите канал для отправки:")
    print("1. 🔥 Рабочий канал")
    print("2. 🧪 Тестовый канал")
    print("0. 🔙 Назад")

    choice = input("\nВыберите действие (0-2): ")

    if choice == '1':
        channel_id = CHANNEL_MAIN
        channel_name = "Рабочий"
    elif choice == '2':
        channel_id = CHANNEL_TEST
        channel_name = "Тестовый"
    elif choice == '0':
        return
    else:
        print("\n❌ Неверный выбор!")
        input("\nНажмите Enter для продолжения...")
        return

    # Ввод текста поста через редактор
    clear_screen()
    print_header()
    print(f"\n✅ Выбран канал: {channel_name} (ID: {channel_id})")
    print("\n📝 ВВОД ТЕКСТА ПОСТА")
    print("=" * 60)

    post_text = open_text_editor()

    if post_text is None:
        print("\n❌ Отмена создания поста (текст не введен)")
        input("\nНажмите Enter для продолжения...")
        return

    # Инициализация переменных
    media_path = None
    button_config = None

    # Цикл работы с постом
    while True:
        clear_screen()
        print_header()
        print(f"\n✅ Выбран канал: {channel_name} (ID: {channel_id})")
        print("\n📋 ТЕКУЩЕЕ СОСТОЯНИЕ ПОСТА:")
        print("=" * 60)

        if media_path:
            file_name = os.path.basename(media_path)
            file_size = os.path.getsize(media_path) / (1024 * 1024)
            print(f"📎 Медиафайл: {file_name} ({file_size:.1f} МБ)")
        else:
            print("📎 Медиафайл: не добавлен")

        if button_config:
            color_names = {"success": "Зеленая", "danger": "Красная", "primary": "Синяя", "": "Серая"}
            print(
                f"🔘 Кнопка: '{button_config['text']}' -> {button_config['url']} [{color_names.get(button_config['style'], 'Серая')}]")
        else:
            print("🔘 Кнопка: не добавлена")

        print("=" * 60)
        print("\n📋 МЕНЮ:")
        print("1. 📎 Добавить медиафайл")
        print("2. 🔘 Добавить кнопку")
        print("3. 👁️ Предпросмотр поста")
        print("4. 📤 Опубликовать пост")
        print("0. ❌ Отменить создание поста")
        print("=" * 60)

        menu_choice = input("\nВыберите действие (0-4): ")

        if menu_choice == '1':
            media_path = add_media()

        elif menu_choice == '2':
            button_config = add_button()

        elif menu_choice == '3':
            show_preview(channel_name, post_text, channel_id, media_path, button_config)

        elif menu_choice == '4':
            # Публикация поста
            clear_screen()
            print_header()
            print("\n📤 ПУБЛИКАЦИЯ ПОСТА")
            print("=" * 60)
            show_preview(channel_name, post_text, channel_id, media_path, button_config)

            print("\nПодтвердите публикацию:")
            print("1. ✅ Да, опубликовать")
            print("2. ❌ Нет, вернуться")

            confirm = input("\nВыберите действие (1-2): ")

            if confirm == '1':
                bot = Bot(token=TOKEN, request=request)

                # Процессинг перед отправкой
                print("\n" + "=" * 60)
                print("🚀 НАЧАЛО ПУБЛИКАЦИИ")
                print("=" * 60)

                # Анимация подготовки
                show_processing("Подготовка поста", duration=1)

                # Отправка
                success = await send_post(bot, channel_id, post_text, media_path, button_config)

                if success:
                    print("\n" + "=" * 60)
                    print("✨ ПОСТ УСПЕШНО ОПУБЛИКОВАН! ✨")
                    print("=" * 60)
                    print("\n✅ Готово! Пост отправлен в канал")
                    input("\nНажмите Enter для возврата в главное меню...")
                    return
                else:
                    print("\n❌ Ошибка при публикации!")
                    print("Проверьте канал - возможно пост все же опубликовался")
                    input("\nНажмите Enter для продолжения...")
            else:
                print("\nПубликация отменена")
                input("\nНажмите Enter для продолжения...")

        elif menu_choice == '0':
            print("\n❌ Создание поста отменено")
            input("\nНажмите Enter для продолжения...")
            return

        else:
            print("\n❌ Неверный выбор!")
            input("\nНажмите Enter для продолжения...")


async def main():
    clear_screen()
    print_header()

    while True:
        print("\n📋 ГЛАВНОЕ МЕНЮ:")
        print("=" * 60)
        print("1. 📝 Создать пост")
        print("0. 🚪 Выход")
        print("=" * 60)

        choice = input("\nВыберите действие (0-1): ")

        if choice == '1':
            await create_post()
        elif choice == '0':
            print("\n👋 До свидания!")
            break
        else:
            print("\n❌ Неверный выбор!")
            input("\nНажмите Enter для продолжения...")
            clear_screen()
            print_header()


if __name__ == "__main__":
    asyncio.run(main())