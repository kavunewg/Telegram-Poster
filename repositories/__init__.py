"""
Репозитории для работы с базой данных
"""
from repositories.user_repo import user_repo
from repositories.channel_repo import channel_repo
from repositories.bot_repo import bot_repo
from repositories.post_stats_repo import post_stats_repo
from repositories.schedule_repo import schedule_repo
from repositories.youtube_repo import youtube_repo

__all__ = [
    'user_repo',
    'channel_repo',
    'bot_repo',
    'post_stats_repo',
    'schedule_repo',
    'youtube_repo'
]