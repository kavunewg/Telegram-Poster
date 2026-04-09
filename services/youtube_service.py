"""
Сервис для работы с YouTube API
"""
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Проверяем доступность YouTube API
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False
    print("⚠️ google-api-python-client не установлен. YouTube мониторинг будет недоступен.")


async def get_youtube_channel_info(url_or_id: str, api_key: str = None) -> Dict:
    """Получение информации о YouTube канале по URL или ID"""
    if not YOUTUBE_AVAILABLE:
        return {"error": "YouTube API не установлен. Установите google-api-python-client"}
    
    if not api_key:
        from core.config import YOUTUBE_API_KEY
        api_key = YOUTUBE_API_KEY
    
    if not api_key:
        return {"error": "Не указан YouTube API ключ"}
    
    try:
        # Извлекаем ID канала из URL
        channel_id = _extract_channel_id(url_or_id)
        
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Пробуем найти канал по ID
        if channel_id:
            request = youtube.channels().list(
                part="snippet,statistics",
                id=channel_id
            )
        else:
            # Пробуем найти по имени пользователя
            request = youtube.channels().list(
                part="snippet,statistics",
                forUsername=url_or_id
            )
        
        response = request.execute()
        
        if not response.get('items'):
            return {"error": "Канал не найден"}
        
        channel = response['items'][0]
        
        return {
            'id': channel['id'],
            'name': channel['snippet']['title'],
            'description': channel['snippet'].get('description', ''),
            'url': f"https://youtube.com/channel/{channel['id']}",
            'subscriber_count': channel['statistics'].get('subscriberCount', 0),
            'video_count': channel['statistics'].get('videoCount', 0),
            'view_count': channel['statistics'].get('viewCount', 0),
            'thumbnail': channel['snippet']['thumbnails']['default']['url']
        }
        
    except HttpError as e:
        error_msg = f"YouTube API ошибка: {e}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Ошибка получения информации о канале: {e}"
        logger.error(error_msg)
        return {"error": error_msg}


def _extract_channel_id(url_or_id: str) -> Optional[str]:
    """Извлечение ID канала из URL"""
    import re
    
    # Если это уже ID канала (начинается с UC)
    if url_or_id.startswith('UC') and len(url_or_id) == 24:
        return url_or_id
    
    # Шаблоны URL
    patterns = [
        r'youtube\.com/channel/([^/?]+)',
        r'youtube\.com/c/([^/?]+)',
        r'youtube\.com/@([^/?]+)',
        r'youtu\.be/([^/?]+)',
        r'youtube\.com/watch\?v=([^&]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None


async def get_latest_video(channel_id: str, api_key: str) -> Optional[Dict]:
    """Получение последнего видео с YouTube канала"""
    if not YOUTUBE_AVAILABLE or not api_key:
        return None
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Получаем последние видео канала
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=1,
            order="date",
            type="video"
        )
        response = request.execute()
        
        if not response['items']:
            return None
        
        video = response['items'][0]
        video_id = video['id']['videoId']
        
        # Получаем детальную информацию о видео
        video_request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id
        )
        video_response = video_request.execute()
        
        if video_response['items']:
            video_info = video_response['items'][0]
            return {
                'id': video_id,
                'title': video_info['snippet']['title'],
                'description': video_info['snippet']['description'][:500] if video_info['snippet']['description'] else '',
                'thumbnail': video_info['snippet']['thumbnails']['high']['url'],
                'url': f"https://youtu.be/{video_id}",
                'published_at': video_info['snippet']['publishedAt'],
                'duration': video_info['contentDetails'].get('duration', ''),
                'views': video_info['statistics'].get('viewCount', 0)
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Ошибка получения видео: {e}")
        return None


def format_youtube_post(video_info: Dict, channel_name: str, template: str = None,
                        include_description: bool = False, button_url: str = None,
                        button_style: str = 'success') -> Tuple[str, Optional[Dict]]:
    """Форматирование поста для YouTube видео с кнопкой"""
    
    # Декодируем шаблон если содержит Unicode escape
    if template and '\\u' in template:
        try:
            template = template.encode('utf-8').decode('unicode-escape')
        except:
            pass
    
    if button_url and '\\u' in button_url:
        try:
            button_url = button_url.encode('utf-8').decode('unicode-escape')
        except:
            pass
    
    if template:
        post = template
        post = post.replace('{video_title}', video_info.get('title', ''))
        post = post.replace('{video_url}', video_info.get('url', ''))
        post = post.replace('{channel_name}', channel_name)
        post = post.replace('{views}', str(video_info.get('views', '0')))
        
        if include_description and video_info.get('description'):
            post = post.replace('{video_description}', video_info.get('description', '')[:300])
        else:
            post = post.replace('{video_description}', '')
    else:
        post = f"🎬 НОВОЕ ВИДЕО!\n\n"
        post += f"📹 {video_info.get('title', '')}\n\n"
        if include_description and video_info.get('description'):
            desc = video_info['description'][:200]
            post += f"📝 {desc}...\n\n"
        post += f"🔗 {video_info.get('url', '')}"
    
    # Создаём кнопку
    button = None
    if button_url:
        button = {
            "text": "🔔 Подписаться",
            "url": button_url,
            "style": button_style or "success"
        }
    
    return post, button


async def check_youtube_channels():
    """Фоновая задача для проверки YouTube каналов"""
    if not YOUTUBE_AVAILABLE:
        print("YouTube API не доступен, проверка пропущена")
        return
    
    from repositories.youtube_repo import youtube_repo
    from services.post_service import send_to_telegram
    from core.config import TELEGRAM_TOKEN
    import uuid
    import json
    
    print("=" * 60)
    print("🔍 ЗАПУСК ПРОВЕРКИ YOUTUBE КАНАЛОВ")
    print("=" * 60)
    
    # Получаем все активные YouTube каналы
    active_channels = youtube_repo.get_active_channels()
    
    print(f"📊 Найдено активных YouTube каналов: {len(active_channels)}")
    
    for channel in active_channels:
        channel_id = channel[0]
        user_id = channel[1]
        youtube_channel_id = channel[2]
        youtube_channel_name = channel[3]
        target_channels = json.loads(channel[4]) if channel[4] else []
        post_template = channel[5]
        include_description = bool(channel[6])
        last_video_id = channel[7]
        user_api_key = channel[8]
        button_url = channel[9] if len(channel) > 9 else None
        button_style = channel[10] if len(channel) > 10 else 'success'
        
        print(f"\n--- Канал: {youtube_channel_name} ---")
        
        if not user_api_key:
            print(f"  ❌ Нет API ключа у пользователя {user_id}")
            continue
        
        try:
            video_info = await get_latest_video(youtube_channel_id, user_api_key)
            
            if video_info and video_info['id'] != last_video_id:
                print(f"  ✅ НОВОЕ ВИДЕО! Отправляем уведомление...")
                
                post_text, button = format_youtube_post(
                    video_info, youtube_channel_name, post_template,
                    include_description, button_url, button_style
                )
                
                for target_channel in target_channels:
                    try:
                        # Получаем токен бота
                        from repositories.bot_repo import bot_repo
                        with bot_repo._get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                SELECT b.token FROM user_channels uc
                                JOIN bot_channels bc ON bc.channel_id = uc.id
                                JOIN user_bots b ON bc.bot_id = b.id
                                WHERE uc.id = ?
                            ''', (target_channel.get('id'),))
                            bot_row = cursor.fetchone()
                            bot_token = bot_row[0] if bot_row else TELEGRAM_TOKEN
                        
                        channel_session = {
                            "user_id": user_id,
                            "channel_db_id": target_channel.get('id'),
                            "channel_id": target_channel.get('channel_id'),
                            "channel_name": target_channel.get('name'),
                            "platform": "telegram",
                            "post_text": post_text,
                            "media_path": None,
                            "media_name": None,
                            "media_size": None,
                            "media_type": "text",
                            "button": button,
                            "bot_token": bot_token
                        }
                        
                        temp_session_id = str(uuid.uuid4())
                        await send_to_telegram(channel_session, temp_session_id)
                        print(f"    ✅ Уведомление отправлено в {target_channel.get('name')}")
                        
                    except Exception as e:
                        print(f"    ❌ Ошибка отправки в {target_channel.get('name')}: {e}")
                
                youtube_repo.update_last_video(channel_id, video_info['id'])
                print(f"  💾 Обновлен last_video_id: {video_info['id']}")
            else:
                print(f"  ⏭️ Нет новых видео")
                
        except Exception as e:
            print(f"  ❌ Ошибка проверки канала: {e}")
            import traceback
            traceback.print_exc()
    
    print("=" * 60)
    print("🔍 ПРОВЕРКА ЗАВЕРШЕНА")
    print("=" * 60)