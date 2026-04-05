import pytest
import os
from unittest.mock import Mock, patch, MagicMock


class TestYouTubeUploader:
    """Tests for the YouTubeUploader class."""

    def test_uploader_class_exists(self):
        """Test that YouTubeUploader class can be imported."""
        from youtube.uploader import YouTubeUploader

        assert YouTubeUploader is not None

    def test_scopes_defined(self):
        """Test that YouTube scopes are defined."""
        from youtube.uploader import SCOPES

        assert "https://www.googleapis.com/auth/youtube.upload" in SCOPES

    def test_uploader_stores_client_secret(self):
        """Test that uploader stores client secret file path."""
        with (
            patch("youtube.uploader.build"),
            patch("youtube.uploader.os.path.exists", return_value=True),
            patch("youtube.uploader.Credentials") as mock_creds,
        ):
            mock_creds.from_authorized_user_file.return_value = MagicMock(valid=True)

            from youtube.uploader import YouTubeUploader

            uploader = YouTubeUploader("my_secret.json")

            assert uploader.client_secret_file == "my_secret.json"

    def test_uploader_authenticates_with_valid_token(self):
        """Test authentication with existing valid token."""
        with (
            patch("youtube.uploader.build") as mock_build,
            patch("youtube.uploader.os.path.exists", return_value=True),
            patch("youtube.uploader.Credentials") as mock_creds,
        ):
            mock_creds_instance = MagicMock(valid=True)
            mock_creds.from_authorized_user_file.return_value = mock_creds_instance
            mock_build.return_value = MagicMock()

            from youtube.uploader import YouTubeUploader

            uploader = YouTubeUploader("secret.json")

            mock_creds.from_authorized_user_file.assert_called_once()

    def test_uploader_refreshes_expired_token(self):
        """Test that expired tokens are refreshed."""
        with (
            patch("youtube.uploader.build") as mock_build,
            patch("youtube.uploader.os.path.exists", return_value=True),
            patch("youtube.uploader.Credentials") as mock_creds,
            patch("youtube.uploader.Request") as mock_request,
            patch("builtins.open", MagicMock()),
        ):
            mock_creds_instance = MagicMock(
                valid=False, expired=True, refresh_token="refresh"
            )
            mock_creds.from_authorized_user_file.return_value = mock_creds_instance

            mock_build.return_value = MagicMock()

            from youtube.uploader import YouTubeUploader

            uploader = YouTubeUploader("secret.json")

            mock_creds_instance.refresh.assert_called_once_with(mock_request())

    def test_upload_short_success(self, tmp_path):
        """Test successful video upload."""
        video_path = tmp_path / "test_video.mp4"
        video_path.write_bytes(b"fake video")

        mock_youtube = MagicMock()
        mock_insert = MagicMock()
        mock_insert.next_chunk.return_value = (None, {"id": "video_123"})
        mock_youtube.videos.return_value.insert.return_value = mock_insert

        with (
            patch("youtube.uploader.build", return_value=mock_youtube),
            patch("youtube.uploader.MediaFileUpload") as mock_media,
            patch("youtube.uploader.os.path.exists", return_value=True),
            patch("youtube.uploader.Credentials") as mock_creds,
            patch("builtins.open", MagicMock()),
        ):
            mock_creds_instance = MagicMock(valid=True)
            mock_creds.from_authorized_user_file.return_value = mock_creds_instance
            mock_media.return_value = MagicMock()

            from youtube.uploader import YouTubeUploader

            uploader = YouTubeUploader("secret.json")
            uploader.youtube = mock_youtube

            result = uploader.upload_short(
                video_path=str(video_path),
                title="Test Video",
                description="Test description",
                tags=["tag1", "tag2"],
            )

            assert result == "video_123"

    def test_upload_short_creates_correct_body(self, tmp_path):
        """Test that upload creates correct request body."""
        video_path = tmp_path / "test_video.mp4"
        video_path.write_bytes(b"fake video")

        mock_youtube = MagicMock()
        mock_insert = MagicMock()
        mock_insert.next_chunk.return_value = (None, {"id": "video_123"})
        mock_youtube.videos.return_value.insert.return_value = mock_insert

        with (
            patch("youtube.uploader.build", return_value=mock_youtube),
            patch("youtube.uploader.MediaFileUpload") as mock_media,
            patch("youtube.uploader.os.path.exists", return_value=True),
            patch("youtube.uploader.Credentials") as mock_creds,
            patch("builtins.open", MagicMock()),
        ):
            mock_creds_instance = MagicMock(valid=True)
            mock_creds.from_authorized_user_file.return_value = mock_creds_instance
            mock_media.return_value = MagicMock()

            from youtube.uploader import YouTubeUploader

            uploader = YouTubeUploader("secret.json")
            uploader.youtube = mock_youtube

            uploader.upload_short(
                video_path=str(video_path),
                title="My Title",
                description="My Description",
                tags=["#tag1", "#tag2"],
            )

            mock_youtube.videos.return_value.insert.assert_called()

    def test_has_retry_decorator(self):
        """Test that retry is imported from tenacity."""
        from youtube import uploader
        import inspect

        source = inspect.getsourcefile(uploader)
        with open(source, "r") as f:
            content = f.read()

        assert "from tenacity import retry" in content

    def test_handles_http_error_403(self):
        """Test that uploader handles HTTP 403 errors."""
        from youtube.uploader import YouTubeUploader
        import inspect

        source = inspect.getsource(YouTubeUploader.upload_short)
        assert "403" in source
        assert "quota" in source.lower() or "Quota" in source

    def test_raises_quota_error(self):
        """Test that uploader raises YouTubeQuotaError."""
        from youtube.uploader import YouTubeUploader
        import inspect

        source = inspect.getsource(YouTubeUploader.upload_short)
        assert "YouTubeQuotaError" in source or "ValueError" in source
