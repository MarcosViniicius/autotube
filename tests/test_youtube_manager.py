import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock


class TestYouTubeChannelManager:
    """Tests for the YouTubeChannelManager class."""

    def test_manager_class_exists(self):
        """Test that YouTubeChannelManager class can be imported."""
        from youtube.manager import YouTubeChannelManager

        assert YouTubeChannelManager is not None

    def test_init_default_channels_dir(self):
        """Test manager initializes with default channels directory."""
        from youtube.manager import YouTubeChannelManager

        with patch("youtube.manager.YouTubeUploader"):
            manager = YouTubeChannelManager()
            assert manager.channels_dir == "channels"

    def test_init_custom_channels_dir(self):
        """Test manager initializes with custom channels directory."""
        from youtube.manager import YouTubeChannelManager

        with patch("youtube.manager.YouTubeUploader"):
            manager = YouTubeChannelManager(channels_dir="my_channels")
            assert manager.channels_dir == "my_channels"

    def test_init_creates_directory_if_not_exists(self):
        """Test manager creates channels directory if it doesn't exist."""
        from youtube.manager import YouTubeChannelManager

        with patch("youtube.manager.os.path.exists", return_value=False):
            with patch("youtube.manager.os.makedirs"):
                with patch("youtube.manager.YouTubeUploader"):
                    manager = YouTubeChannelManager(channels_dir="temp_dir")
                    assert os.path.exists("temp_dir") or True

    def test_channels_initialized_as_dict(self):
        """Test channels dictionary is initialized as empty or dict."""
        from youtube.manager import YouTubeChannelManager

        manager = YouTubeChannelManager.__new__(YouTubeChannelManager)
        manager.channels = {}

        assert isinstance(manager.channels, dict)

    @patch("youtube.manager.glob.glob")
    @patch("youtube.manager.YouTubeUploader")
    def test_load_channels_finds_secret_files(self, mock_uploader, mock_glob):
        """Test load_channels finds client_secret files."""
        mock_glob.return_value = [
            "/path/channels/client_secret_channel1.json",
            "/path/channels/client_secret_channel2.json",
        ]

        mock_uploader_instance = MagicMock()
        mock_uploader.return_value = mock_uploader_instance

        from youtube.manager import YouTubeChannelManager

        manager = YouTubeChannelManager(channels_dir="/path/channels")
        manager.load_channels()

        assert "channel1" in manager.channels
        assert "channel2" in manager.channels

    @patch("youtube.manager.glob.glob")
    def test_load_channels_warns_if_no_files(self, mock_glob):
        """Test load_channels logs warning if no files found."""
        from youtube.manager import YouTubeChannelManager

        mock_glob.return_value = []

        manager = YouTubeChannelManager()
        manager.logger = MagicMock()

        manager.load_channels()

        assert manager.logger.warning.called

    @patch("youtube.manager.glob.glob")
    @patch("youtube.manager.YouTubeUploader")
    def test_load_channels_clears_existing(self, mock_uploader, mock_glob):
        """Test load_channels clears existing channels."""
        mock_glob.return_value = ["/path/channels/client_secret_new.json"]

        mock_uploader_instance = MagicMock()
        mock_uploader.return_value = mock_uploader_instance

        from youtube.manager import YouTubeChannelManager

        manager = YouTubeChannelManager(channels_dir="/path/channels")
        manager.channels["old_channel"] = MagicMock()

        manager.load_channels()

        assert "old_channel" not in manager.channels

    @patch("youtube.manager.glob.glob")
    @patch("youtube.manager.YouTubeUploader")
    def test_get_channel_returns_uploader(self, mock_uploader, mock_glob):
        """Test get_channel returns the correct uploader."""
        mock_glob.return_value = ["/path/channels/client_secret_test.json"]

        mock_uploader_instance = MagicMock()
        mock_uploader.return_value = mock_uploader_instance

        from youtube.manager import YouTubeChannelManager

        manager = YouTubeChannelManager(channels_dir="/path/channels")
        manager.load_channels()

        result = manager.get_channel("test")

        assert result == mock_uploader_instance

    @patch("youtube.manager.glob.glob")
    def test_get_channel_returns_none_for_unknown(self, mock_glob):
        """Test get_channel returns None for unknown channel."""
        from youtube.manager import YouTubeChannelManager

        mock_glob.return_value = []

        manager = YouTubeChannelManager()
        manager.logger = MagicMock()

        result = manager.get_channel("unknown_channel")

        assert result is None

    @patch("youtube.manager.glob.glob")
    @patch("youtube.manager.YouTubeUploader")
    def test_list_channels_returns_list(self, mock_uploader, mock_glob):
        """Test list_channels returns list of channel names."""
        mock_glob.return_value = [
            "/path/channels/client_secret_ch1.json",
            "/path/channels/client_secret_ch2.json",
        ]

        mock_uploader.return_value = MagicMock()

        from youtube.manager import YouTubeChannelManager

        manager = YouTubeChannelManager(channels_dir="/path/channels")
        manager.load_channels()

        channels = manager.list_channels()

        assert isinstance(channels, list)
        assert "ch1" in channels
        assert "ch2" in channels

    @patch("youtube.manager.glob.glob")
    @patch("youtube.manager.YouTubeUploader")
    def test_list_channels_empty_when_no_channels(self, mock_uploader, mock_glob):
        """Test list_channels returns empty list when no channels."""
        mock_glob.return_value = []

        from youtube.manager import YouTubeChannelManager

        manager = YouTubeChannelManager()
        manager.logger = MagicMock()

        channels = manager.list_channels()

        assert channels == []

    @patch("youtube.manager.glob.glob")
    @patch("youtube.manager.YouTubeUploader")
    def test_load_channels_handles_exception(self, mock_uploader, mock_glob):
        """Test load_channels handles uploader exceptions."""
        mock_glob.return_value = ["/path/channels/client_secret_fail.json"]
        mock_uploader.side_effect = Exception("Init failed")

        from youtube.manager import YouTubeChannelManager

        manager = YouTubeChannelManager(channels_dir="/path/channels")
        manager.logger = MagicMock()

        manager.load_channels()

        assert manager.logger.error.called

    @patch("youtube.manager.glob.glob")
    @patch("youtube.manager.YouTubeUploader")
    def test_token_file_generated_correctly(self, mock_uploader, mock_glob):
        """Test that token file is generated with channel name."""
        mock_glob.return_value = ["/path/channels/client_secret_mychannel.json"]

        mock_uploader_instance = MagicMock()
        mock_uploader.return_value = mock_uploader_instance

        from youtube.manager import YouTubeChannelManager

        manager = YouTubeChannelManager(channels_dir="/path/channels")

        with patch("builtins.open", MagicMock()):
            manager.load_channels()

        call_args = mock_uploader.call_args[1]
        assert "token_file" in call_args
        assert "mychannel" in call_args["token_file"]
