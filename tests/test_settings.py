import pytest
import os
import sys


class TestSettings:
    """Tests for the Settings class."""

    def test_settings_class_exists(self):
        """Test that Settings class can be imported."""
        from config.settings import Settings

        assert Settings is not None

    def test_settings_has_required_attributes(self):
        """Test that Settings class has the required class attributes."""
        from config.settings import Settings

        attrs = [
            "REAL_API_EMAIL",
            "REAL_API_PASSWORD",
            "REAL_API_TOKEN",
            "REAL_API_BASE_URL",
            "OPENROUTER_API_KEY",
            "OPENROUTER_MODEL",
            "TELEGRAM_BOT_TOKEN",
            "TELEGRAM_CHAT_ID",
            "YOUTUBE_CLIENT_SECRET_FILE",
            "MODO_DEFAULT",
            "CRON_INTERVAL",
            "LOG_LEVEL",
            "DOWNLOAD_PATH",
        ]

        for attr in attrs:
            assert hasattr(Settings, attr), f"Missing attribute: {attr}"

    def test_settings_default_values(self):
        """Test that Settings has correct default values."""
        from config.settings import Settings

        assert Settings.REAL_API_BASE_URL == "https://api.realoficial.com.br/api/v1"
        assert Settings.YOUTUBE_CLIENT_SECRET_FILE == "client_secret.json"
        assert Settings.MODO_DEFAULT == "manual"
        assert Settings.CRON_INTERVAL == 30
        assert Settings.LOG_LEVEL == "INFO"
        assert Settings.DOWNLOAD_PATH == "downloads/"

    def test_settings_instance_has_attributes(self):
        """Test that Settings instance has all expected attributes."""
        from config.settings import Settings

        settings = Settings()

        assert hasattr(settings, "REAL_API_EMAIL")
        assert hasattr(settings, "REAL_API_PASSWORD")
        assert hasattr(settings, "REAL_API_TOKEN")
        assert hasattr(settings, "REAL_API_BASE_URL")
        assert hasattr(settings, "OPENROUTER_API_KEY")
        assert hasattr(settings, "OPENROUTER_MODEL")
        assert hasattr(settings, "TELEGRAM_BOT_TOKEN")
        assert hasattr(settings, "TELEGRAM_CHAT_ID")
        assert hasattr(settings, "YOUTUBE_CLIENT_SECRET_FILE")
        assert hasattr(settings, "MODO_DEFAULT")
        assert hasattr(settings, "CRON_INTERVAL")
        assert hasattr(settings, "LOG_LEVEL")
        assert hasattr(settings, "DOWNLOAD_PATH")
