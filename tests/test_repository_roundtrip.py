import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core import config as config_module
from core import database as database_module
from core.database import init_db
from repositories.bot_repo import BotRepository
from repositories.channel_repo import ChannelRepository
from repositories.schedule_repo import ScheduleRepository
from repositories.youtube_repo import YouTubeRepository
from repositories.user_repo import UserRepository


class RepositoryRoundtripTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        self.original_config_db_path = config_module.DB_PATH
        self.original_database_db_path = database_module.DB_PATH

        config_module.DB_PATH = self.db_path
        database_module.DB_PATH = self.db_path

        init_db()

        self.user_repo = UserRepository()
        self.bot_repo = BotRepository()
        self.channel_repo = ChannelRepository()
        self.schedule_repo = ScheduleRepository()
        self.youtube_repo = YouTubeRepository()

    def tearDown(self):
        config_module.DB_PATH = self.original_config_db_path
        database_module.DB_PATH = self.original_database_db_path
        self.temp_dir.cleanup()

    def test_schedule_repository_roundtrip(self):
        user_id = self.user_repo.create("tester", "secret123", "Test User")
        post_id = self.schedule_repo.save_post(
            user_id=user_id,
            channels=[{"id": 1, "channel_id": "@demo", "platform": "telegram"}],
            post_text="hello world",
            media_path=None,
            media_name=None,
            media_size=None,
            media_type="text",
            button={"text": "Open", "url": "https://example.com"},
            scheduled_at="2030-01-01T10:00:00+03:00",
            is_regular=True,
            regular_settings={"interval_hours": 24},
        )

        saved = self.schedule_repo.get_post_by_id(post_id, user_id)
        pending = self.schedule_repo.get_pending_posts()

        self.assertIsNotNone(saved)
        self.assertEqual(saved["post_text"], "hello world")
        self.assertEqual(saved["channels"][0]["channel_id"], "@demo")
        self.assertEqual(saved["button"]["url"], "https://example.com")
        self.assertEqual(saved["regular_settings"]["interval_hours"], 24)
        self.assertTrue(any(item["id"] == post_id for item in pending))

    def test_channel_and_bot_link_roundtrip(self):
        user_id = self.user_repo.create("owner", "secret123", "Owner User")
        bot_id = self.bot_repo.add_bot(
            user_id=user_id,
            name="poster_bot",
            token="123:telegram-token",
            platform="telegram",
        )
        channel_id = self.channel_repo.add_channel(
            user_id=user_id,
            channel_name="Main channel",
            channel_id="@main_channel",
            channel_url="https://t.me/main_channel",
            platform="telegram",
        )

        linked = self.bot_repo.add_bot_channel(bot_id, channel_id)
        channel = self.channel_repo.get_channel_by_id(channel_id, user_id)

        self.assertTrue(linked)
        self.assertIsNotNone(channel)
        self.assertEqual(channel["bot_id"], bot_id)
        self.assertEqual(channel["bot_name"], "poster_bot")
        self.assertEqual(channel["bot_token"], "123:telegram-token")

    def test_youtube_repository_roundtrip(self):
        user_id = self.user_repo.create("ytowner", "secret123", "YouTube Owner")
        self.user_repo.update_youtube_api_key(user_id, "AIza-test-key")

        channel_id = self.youtube_repo.add_channel(
            user_id=user_id,
            youtube_channel_id="UC1234567890123456789012",
            youtube_channel_name="Demo YouTube",
            youtube_channel_url="https://youtube.com/channel/UC1234567890123456789012",
            target_channels=[{"id": 7, "name": "Main TG", "channel_id": "@demo"}],
            post_template="New video: {video_title}",
            include_description=1,
            button_url="https://youtube.com/@demo",
            button_style="primary",
        )

        user_channels = self.youtube_repo.get_user_channels(user_id)
        active_channels = self.youtube_repo.get_active_channels()
        saved = self.youtube_repo.get_channel_by_id(channel_id, user_id)

        self.assertIsNotNone(saved)
        self.assertEqual(saved["youtube_channel_name"], "Demo YouTube")
        self.assertEqual(saved["target_channels"][0]["channel_id"], "@demo")
        self.assertTrue(saved["include_description"])
        self.assertEqual(saved["button_style"], "primary")
        self.assertTrue(any(item["id"] == channel_id for item in user_channels))
        self.assertTrue(any(item["id"] == channel_id for item in active_channels))


if __name__ == "__main__":
    unittest.main()
