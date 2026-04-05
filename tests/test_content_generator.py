import pytest
import json
from unittest.mock import Mock, patch, MagicMock


class TestContentGenerator:
    """Tests for the ContentGenerator class."""

    def test_generator_class_exists(self):
        """Test that ContentGenerator class can be imported."""
        from ai.generator import ContentGenerator

        assert ContentGenerator is not None

    def test_init_with_api_key(self):
        """Test that ContentGenerator initializes with API key."""
        from ai.generator import ContentGenerator

        with patch("ai.generator.openai"):
            gen = ContentGenerator(api_key="sk_test_123")
            assert gen.api_key == "sk_test_123"

    def test_init_with_custom_model(self):
        """Test that ContentGenerator initializes with custom model."""
        from ai.generator import ContentGenerator

        with patch("ai.generator.openai"):
            gen = ContentGenerator(api_key="sk_test", model="custom/model")
            assert gen.model == "custom/model"

    def test_init_default_model(self):
        """Test that ContentGenerator uses default model."""
        from ai.generator import ContentGenerator

        with patch("ai.generator.openai"):
            gen = ContentGenerator(api_key="sk_test")
            assert gen.model == "google/gemini-2.0-flash-lite-001"

    def test_init_creates_openai_client(self):
        """Test that ContentGenerator creates OpenAI client."""
        from ai.generator import ContentGenerator

        with patch("ai.generator.openai") as mock_openai:
            mock_client = MagicMock()
            mock_openai.OpenAI.return_value = mock_client

            gen = ContentGenerator(api_key="sk_test")

            mock_openai.OpenAI.assert_called_once_with(
                base_url="https://openrouter.ai/api/v1", api_key="sk_test"
            )

    def test_generate_metadata_success(self):
        """Test successful metadata generation."""
        from ai.generator import ContentGenerator

        with patch("ai.generator.openai") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps(
                {
                    "title": "VIRAL VIDEO!",
                    "description": "Watch now!",
                    "hashtags": "#viral #shorts",
                }
            )

            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.OpenAI.return_value = mock_client

            gen = ContentGenerator(api_key="sk_test")
            result = gen.generate_shorts_metadata("Test description")

            assert result["title"] == "VIRAL VIDEO!"
            assert "description" in result
            assert "hashtags" in result

    def test_generate_metadata_with_markdown_json(self):
        """Test metadata with markdown-formatted JSON."""
        from ai.generator import ContentGenerator

        with patch("ai.generator.openai") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[
                0
            ].message.content = '```json\n{"title": "Test", "description": "Desc", "hashtags": "#tag"}\n```'

            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.OpenAI.return_value = mock_client

            gen = ContentGenerator(api_key="sk_test")
            result = gen.generate_shorts_metadata("Test")

            assert result["title"] == "Test"

    def test_generate_metadata_api_error_returns_fallback(self):
        """Test that API error returns fallback metadata."""
        from ai.generator import ContentGenerator

        with patch("ai.generator.openai") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            mock_openai.OpenAI.return_value = mock_client

            gen = ContentGenerator(api_key="sk_test")
            result = gen.generate_shorts_metadata("Test description")

            assert "title" in result
            assert "description" in result
            assert "hashtags" in result
            assert "#shorts" in result["hashtags"]

    def test_generate_metadata_empty_response(self):
        """Test metadata generation with empty response."""
        from ai.generator import ContentGenerator

        with patch("ai.generator.openai") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = ""

            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.OpenAI.return_value = mock_client

            gen = ContentGenerator(api_key="sk_test")
            result = gen.generate_shorts_metadata("Test")

            assert "title" in result

    def test_generate_metadata_calls_api_with_correct_params(self):
        """Test that generate calls API with correct parameters."""
        from ai.generator import ContentGenerator

        with patch("ai.generator.openai") as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps(
                {"title": "Test", "description": "Desc", "hashtags": "#tag"}
            )

            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.OpenAI.return_value = mock_client

            gen = ContentGenerator(api_key="sk_test", model="test/model")
            gen.generate_shorts_metadata("Test description")

            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "test/model"
            assert len(call_kwargs["messages"]) == 2

    def test_call_ai_with_retry_method_exists(self):
        """Test that _call_ai_with_retry method exists."""
        from ai.generator import ContentGenerator

        assert hasattr(ContentGenerator, "_call_ai_with_retry")

    def test_call_ai_with_retry_decorated(self):
        """Test that _call_ai_with_retry has retry decorator."""
        from ai.generator import ContentGenerator
        from tenacity import RetryCallState

        gen = ContentGenerator(api_key="sk_test")
        assert callable(gen._call_ai_with_retry)
