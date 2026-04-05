import pytest
from unittest.mock import Mock, patch, MagicMock


class TestRealOficialAPI:
    """Tests for the RealOficialAPI client."""

    def test_real_api_class_exists(self):
        """Test that RealOficialAPI class can be imported."""
        from real_api.client import RealOficialAPI

        assert RealOficialAPI is not None

    def test_init_with_credentials(self):
        """Test API initialization with credentials."""
        from real_api.client import RealOficialAPI

        api = RealOficialAPI(
            email="test@example.com",
            password="password123",
            base_url="https://api.test.com",
        )

        assert api.email == "test@example.com"
        assert api.password == "password123"
        assert api.base_url == "https://api.test.com"

    def test_init_with_token(self):
        """Test API initialization with token only."""
        from real_api.client import RealOficialAPI

        api = RealOficialAPI(token="my_token")
        assert api.token == "my_token"

    def test_init_default_base_url(self):
        """Test API uses default base URL."""
        from real_api.client import RealOficialAPI

        api = RealOficialAPI()
        assert api.base_url == "https://api.realoficial.com.br/api/v1"

    def test_login_returns_true_with_token(self):
        """Test login returns True when token exists."""
        from real_api.client import RealOficialAPI

        api = RealOficialAPI(token="existing_token")
        assert api.login() is True

    def test_login_returns_false_without_credentials(self):
        """Test login returns False without credentials."""
        from real_api.client import RealOficialAPI

        api = RealOficialAPI()
        assert api.login() is False

    def test_get_headers_returns_bearer(self):
        """Test _get_headers returns correct format."""
        from real_api.client import RealOficialAPI

        api = RealOficialAPI(token="test_token")
        headers = api._get_headers()
        assert headers == {"Authorization": "Bearer test_token"}

    @patch("real_api.client.requests.post")
    def test_login_with_valid_credentials(self, mock_post):
        """Test login with valid credentials."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "new_token_123"}
        mock_post.return_value = mock_response

        api = RealOficialAPI(email="test@test.com", password="pass123")
        result = api.login()

        assert result is True
        assert api.token == "new_token_123"

    @patch("real_api.client.requests.post")
    def test_login_fails_on_api_error(self, mock_post):
        """Test login fails on API error."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Error")
        mock_post.return_value = mock_response

        api = RealOficialAPI(email="test@test.com", password="wrong")
        result = api.login()

        assert result is False

    @patch("real_api.client.requests.get")
    @patch("real_api.client.requests.post")
    def test_get_projects_success(self, mock_post, mock_get):
        """Test get_projects returns data successfully."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "p1", "name": "Project 1"}]}
        mock_get.return_value = mock_response

        api = RealOficialAPI(token="test_token")
        projects = api.get_projects()

        assert len(projects) == 1
        assert projects[0]["id"] == "p1"

    @patch("real_api.client.requests.get")
    def test_get_projects_returns_empty_on_error(self, mock_get):
        """Test get_projects returns empty list on error."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_response.raise_for_status.side_effect = Exception("500 Error")
        mock_get.return_value = mock_response

        api = RealOficialAPI(token="test_token")
        projects = api.get_projects()

        assert projects == []

    @patch("real_api.client.requests.get")
    def test_get_shorts_with_nested_data(self, mock_get):
        """Test get_shorts parses nested data structure."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "data": [
                    {"id": "s1", "title": "Short 1"},
                    {"id": "s2", "title": "Short 2"},
                ]
            }
        }
        mock_get.return_value = mock_response

        api = RealOficialAPI(token="test_token")
        shorts = api.get_shorts("project_123")

        assert len(shorts) == 2
        assert shorts[0]["id"] == "s1"

    @patch("real_api.client.requests.get")
    def test_get_shorts_with_flat_data(self, mock_get):
        """Test get_shorts parses flat data structure."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": "s1", "title": "Short 1"}]}
        mock_get.return_value = mock_response

        api = RealOficialAPI(token="test_token")
        shorts = api.get_shorts("project_123")

        assert len(shorts) == 1

    @patch("real_api.client.requests.get")
    def test_get_shorts_returns_empty_on_error(self, mock_get):
        """Test get_shorts returns empty list on error."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        mock_get.return_value = mock_response

        api = RealOficialAPI(token="test_token")
        shorts = api.get_shorts("project_123")

        assert shorts == []

    @patch("real_api.client.requests.post")
    def test_render_short_success(self, mock_post):
        """Test render_short returns render_id."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"render_id": "render_abc"}
        mock_post.return_value = mock_response

        api = RealOficialAPI(token="test_token")
        render_id = api.render_short("project_1", "short_1")

        assert render_id == "render_abc"

    @patch("real_api.client.requests.post")
    def test_render_short_tries_without_body_on_400(self, mock_post):
        """Test render_short retries without body on 400."""
        from real_api.client import RealOficialAPI

        mock_response_400 = Mock()
        mock_response_400.status_code = 400

        mock_response_ok = Mock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = {"render_id": "render_xyz"}

        mock_post.side_effect = [mock_response_400, mock_response_ok]

        api = RealOficialAPI(token="test_token")
        render_id = api.render_short("project_1", "short_1")

        assert render_id == "render_xyz"
        assert mock_post.call_count == 2

    @patch("real_api.client.requests.post")
    def test_render_short_returns_none_on_failure(self, mock_post):
        """Test render_short returns None on failure."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("Error")
        mock_post.return_value = mock_response

        api = RealOficialAPI(token="test_token")
        render_id = api.render_short("project_1", "short_1")

        assert render_id is None

    @patch("real_api.client.requests.get")
    def test_get_render_status_finds_render(self, mock_get):
        """Test get_render_status finds the render."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "data": [
                    {
                        "id": "render_1",
                        "status": "done",
                        "download_url": "http://test.com/video.mp4",
                    },
                    {"id": "render_2", "status": "processing"},
                ]
            }
        }
        mock_get.return_value = mock_response

        api = RealOficialAPI(token="test_token")
        status = api.get_render_status("render_1")

        assert status["status"] == "done"
        assert status["download_url"] == "http://test.com/video.mp4"

    @patch("real_api.client.requests.get")
    def test_get_render_status_returns_empty_when_not_found(self, mock_get):
        """Test get_render_status returns empty dict when render not found."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"data": [{"id": "render_2", "status": "done"}]}
        }
        mock_get.return_value = mock_response

        api = RealOficialAPI(token="test_token")
        status = api.get_render_status("render_1")

        assert status == {}

    @patch("real_api.client.requests.get")
    @patch("builtins.open", create=True)
    def test_download_video_success(self, mock_open, mock_get):
        """Test download_video downloads successfully."""
        from real_api.client import RealOficialAPI

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content = lambda chunk_size: [b"fake video data"]
        mock_get.return_value = mock_response

        mock_file = MagicMock()
        mock_open.return_value = mock_file

        api = RealOficialAPI(token="test_token")
        result = api.download_video("http://test.com/video.mp4", "/tmp/video.mp4")

        assert result is True

    @patch("real_api.client.time.sleep")
    @patch("real_api.client.requests.get")
    def test_download_video_retries_on_404(self, mock_get, mock_sleep):
        """Test download_video retries on 404."""
        from real_api.client import RealOficialAPI
        import requests

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        api = RealOficialAPI(token="test_token")
        result = api.download_video("http://test.com/bad.mp4", "/tmp/video.mp4")

        assert result is False
        assert mock_get.call_count == 3

    @patch("real_api.client.requests.get")
    def test_download_video_returns_false_on_exception(self, mock_get):
        """Test download_video returns False on general exception."""
        from real_api.client import RealOficialAPI

        mock_get.side_effect = Exception("Network error")

        api = RealOficialAPI(token="test_token")
        result = api.download_video("http://test.com/video.mp4", "/tmp/video.mp4")

        assert result is False
