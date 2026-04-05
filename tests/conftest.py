import pytest
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import tempfile
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def temp_dir():
    """Creates a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_history_file(temp_dir):
    """Creates a temporary history file path."""
    return os.path.join(temp_dir, "test_history.json")


@pytest.fixture
def temp_state_file(temp_dir):
    """Creates a temporary state file path."""
    return os.path.join(temp_dir, "test_state.json")


@pytest.fixture
def temp_log_file(temp_dir):
    """Creates a temporary log file path."""
    return os.path.join(temp_dir, "test_log.txt")


@pytest.fixture
def temp_video_path(temp_dir):
    """Creates a temporary video file."""
    video_path = os.path.join(temp_dir, "test_video.mp4")
    with open(video_path, "wb") as f:
        f.write(b"fake video content")
    return video_path


@pytest.fixture
def mock_settings():
    """Mocks the Settings class with test values."""
    with patch("config.settings.load_dotenv"):
        from config.settings import Settings

        with patch.object(Settings, "__init__", lambda self: None):
            settings = Settings.__new__(Settings)
            settings.REAL_API_EMAIL = "test@example.com"
            settings.REAL_API_PASSWORD = "test_password"
            settings.REAL_API_TOKEN = "test_token_123"
            settings.REAL_API_BASE_URL = "https://api.test.com/api/v1"
            settings.OPENROUTER_API_KEY = "test_api_key"
            settings.OPENROUTER_MODEL = "google/gemini-2.0-flash-lite-001"
            settings.TELEGRAM_BOT_TOKEN = "123456:ABC-DEF"
            settings.TELEGRAM_CHAT_ID = "123456789"
            settings.YOUTUBE_CLIENT_SECRET_FILE = "client_secret.json"
            settings.MODO_DEFAULT = "manual"
            settings.CRON_INTERVAL = 30
            settings.LOG_LEVEL = "INFO"
            settings.DOWNLOAD_PATH = "downloads/"
            yield settings


@pytest.fixture
def mock_real_api():
    """Creates a mock RealOficialAPI instance."""
    with patch("real_api.client.requests"):
        from real_api.client import RealOficialAPI

        api = RealOficialAPI(
            email="test@example.com",
            password="test_password",
            token="test_token",
            base_url="https://api.test.com/api/v1",
        )
        api.token = "test_token"
        return api


@pytest.fixture
def mock_content_generator():
    """Creates a mock ContentGenerator instance."""
    with patch("ai.generator.openai"):
        from ai.generator import ContentGenerator

        gen = ContentGenerator(api_key="test_key")
        return gen


@pytest.fixture
def mock_youtube_uploader():
    """Creates a mock YouTubeUploader instance."""
    with (
        patch("youtube.uploader.build") as mock_build,
        patch("youtube.uploader.InstalledAppFlow"),
        patch("youtube.uploader.Credentials"),
    ):
        mock_build.return_value = MagicMock()
        from youtube.uploader import YouTubeUploader

        uploader = YouTubeUploader(client_secret_file="test_secret.json")
        return uploader


@pytest.fixture
def mock_telegram_bot():
    """Creates a mock AutoTubeBot instance."""
    with patch("telegram_bot.bot.ApplicationBuilder"):
        from telegram_bot.bot import AutoTubeBot

        bot = AutoTubeBot(token="123456:ABC-DEF", chat_id="123456789")
        bot.app = MagicMock()
        bot.app.bot = MagicMock()
        bot.app.bot.send_message = AsyncMock()
        bot.app.bot.send_photo = AsyncMock()
        return bot


@pytest.fixture
def sample_projects():
    """Sample project data for testing."""
    return [
        {
            "id": "proj_001",
            "name": "Project Alpha",
            "title": "Alpha",
            "status": "active",
        },
        {"id": "proj_002", "name": "Project Beta", "title": "Beta", "status": "active"},
    ]


@pytest.fixture
def sample_shorts():
    """Sample shorts data for testing."""
    return [
        {
            "id": "short_001",
            "title": "Amazing Short 1",
            "description": "This is an amazing short video",
            "score": 95,
            "duration": 30,
            "thumbnail": "https://example.com/thumb1.jpg",
            "status": "pending",
        },
        {
            "id": "short_002",
            "title": "Amazing Short 2",
            "description": "Another great short video",
            "score": 88,
            "duration": 45,
            "thumbnail": "https://example.com/thumb2.jpg",
            "status": "pending",
        },
    ]


@pytest.fixture
def sample_ai_metadata():
    """Sample AI-generated metadata for testing."""
    return {
        "title": "INCREDIBLE CONTENT YOU MUST SEE!",
        "description": "Watch this amazing video now! Subscribe for more!",
        "hashtags": "#viral #trending #shorts #amazing #mustwatch",
    }


@pytest.fixture
def sample_render_status_done():
    """Sample render status for completed render."""
    return {"status": "done", "download_url": "https://example.com/video.mp4"}


@pytest.fixture
def sample_render_status_processing():
    """Sample render status for processing render."""
    return {"status": "processing"}


@pytest.fixture
def sample_render_status_failed():
    """Sample render status for failed render."""
    return {"status": "failed"}
