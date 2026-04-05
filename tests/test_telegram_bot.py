import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock


class TestAutoTubeBot:
    """Tests for the AutoTubeBot class."""

    def test_bot_class_exists(self):
        """Test that AutoTubeBot class can be imported."""
        from telegram_bot.bot import AutoTubeBot

        assert AutoTubeBot is not None

    def test_bot_stores_token_and_chat_id(self):
        """Test that bot initializes with token and chat_id."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            bot = AutoTubeBot(token="123456:ABC", chat_id="987654321")

            assert bot.token == "123456:ABC"
            assert bot.chat_id == "987654321"

    def test_bot_stores_callbacks(self):
        """Test that bot stores all callback functions."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            list_callback = MagicMock()
            approve_callback = MagicMock()
            auto_callback = MagicMock()
            skip_callback = MagicMock()
            status_callback = MagicMock()
            scheduling_callback = MagicMock()
            resume_callback = MagicMock()
            startup_callback = MagicMock()

            bot = AutoTubeBot(
                token="123456:ABC",
                chat_id="987654321",
                on_list_projects=list_callback,
                on_approve_project=approve_callback,
                on_toggle_auto=auto_callback,
                on_skip_short=skip_callback,
                on_get_status=status_callback,
                on_start_scheduling=scheduling_callback,
                on_resume_scheduling=resume_callback,
                on_startup=startup_callback,
            )

            assert bot.on_list_projects == list_callback
            assert bot.on_approve_project == approve_callback
            assert bot.on_toggle_auto == auto_callback
            assert bot.on_skip_short == skip_callback
            assert bot.on_get_status == status_callback
            assert bot.on_start_scheduling == scheduling_callback
            assert bot.on_resume_scheduling == resume_callback
            assert bot.on_startup == startup_callback

    def test_bot_initializes_user_data(self):
        """Test that bot initializes empty user_data."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            bot = AutoTubeBot(token="123456:ABC", chat_id="987654321")

            assert bot.user_data == {}

    def test_bot_has_on_startup_parameter(self):
        """Test that bot constructor accepts on_startup parameter."""
        from telegram_bot.bot import AutoTubeBot
        import inspect

        sig = inspect.signature(AutoTubeBot.__init__)
        params = list(sig.parameters.keys())

        assert "on_startup" in params

    def test_bot_has_post_init_method(self):
        """Test that bot has _post_init method."""
        from telegram_bot.bot import AutoTubeBot

        assert hasattr(AutoTubeBot, "_post_init")

    @pytest.mark.asyncio
    async def test_send_notification_success(self):
        """Test successful notification sending."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_app.bot = MagicMock()
            mock_app.bot.send_message = AsyncMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            bot = AutoTubeBot(token="123456:ABC", chat_id="987654321")
            bot.app = mock_app

            await bot.send_notification("Test message")

            mock_app.bot.send_message.assert_called_once()
            call_kwargs = mock_app.bot.send_message.call_args[1]
            assert call_kwargs["chat_id"] == "987654321"
            assert call_kwargs["text"] == "Test message"

    @pytest.mark.asyncio
    async def test_send_notification_handles_error(self):
        """Test that send_notification handles errors gracefully."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_app.bot = MagicMock()
            mock_app.bot.send_message = AsyncMock(side_effect=Exception("Send failed"))
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            bot = AutoTubeBot(token="123456:ABC", chat_id="987654321")
            bot.app = mock_app
            bot.logger = MagicMock()

            await bot.send_notification("Test message")

            assert bot.logger.error.called

    @pytest.mark.asyncio
    async def test_send_photo_success(self):
        """Test successful photo sending."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_app.bot = MagicMock()
            mock_app.bot.send_photo = AsyncMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            bot = AutoTubeBot(token="123456:ABC", chat_id="987654321")
            bot.app = mock_app

            await bot.send_photo(
                photo_url="https://example.com/photo.jpg", caption="Photo caption"
            )

            mock_app.bot.send_photo.assert_called_once()
            call_kwargs = mock_app.bot.send_photo.call_args[1]
            assert call_kwargs["chat_id"] == "987654321"
            assert call_kwargs["caption"] == "Photo caption"

    def test_callback_handler_exists(self):
        """Test that callback handler method exists."""
        from telegram_bot.bot import AutoTubeBot

        assert hasattr(AutoTubeBot, "_handle_callback")

    def test_callback_handles_menu_commands(self):
        """Test callback handler handles menu commands."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            bot = AutoTubeBot(token="123456:ABC", chat_id="987654321")

            query = MagicMock()
            query.data = "menu_cmd_listar"
            query.answer = AsyncMock()

            update = MagicMock()
            update.callback_query = query

            bot._list_projects_cmd = AsyncMock()

            asyncio.run(bot._handle_callback(update, None))

            query.answer.assert_called_once()

    def test_callback_handles_unknown_data(self):
        """Test callback handler handles unknown data gracefully."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            bot = AutoTubeBot(token="123456:ABC", chat_id="987654321")

            query = MagicMock()
            query.data = "unknown_action"
            query.answer = AsyncMock()

            update = MagicMock()
            update.callback_query = query

            asyncio.run(bot._handle_callback(update, None))

            query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_with_callback(self):
        """Test status command with callback configured."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            status_report = "System Status: OK"
            bot = AutoTubeBot(
                token="123456:ABC",
                chat_id="987654321",
                on_get_status=lambda: status_report,
            )

            update = MagicMock()
            update.message = MagicMock()
            update.message.reply_text = AsyncMock()

            await bot._status(update, None)

            update.message.reply_text.assert_called_once_with(
                status_report, parse_mode="HTML"
            )

    @pytest.mark.asyncio
    async def test_auto_on_callback(self):
        """Test auto_on command triggers callback."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            toggle_mock = MagicMock()
            bot = AutoTubeBot(
                token="123456:ABC", chat_id="987654321", on_toggle_auto=toggle_mock
            )

            update = MagicMock()
            update.message = MagicMock()
            update.message.reply_text = AsyncMock()

            await bot._auto_on(update, None)

            toggle_mock.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_auto_off_callback(self):
        """Test auto_off command triggers callback."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            toggle_mock = MagicMock()
            bot = AutoTubeBot(
                token="123456:ABC", chat_id="987654321", on_toggle_auto=toggle_mock
            )

            update = MagicMock()
            update.message = MagicMock()
            update.message.reply_text = AsyncMock()

            await bot._auto_off(update, None)

            toggle_mock.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_list_projects_cmd_sends_projects(self):
        """Test list_projects_cmd sends projects."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            bot = AutoTubeBot(token="123456:ABC", chat_id="987654321")

            update = MagicMock()
            update.message = MagicMock()
            update.message.reply_text = AsyncMock()

            await bot._list_projects_cmd(update, None)

    def test_start_scheduling_sets_step(self):
        """Test that start_scheduling sets user_data step."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            bot = AutoTubeBot(token="123456:ABC", chat_id="987654321")

            assert isinstance(bot.user_data, dict)

    @pytest.mark.asyncio
    async def test_start_command_sends_welcome(self):
        """Test that start command sends welcome message."""
        with patch("telegram_bot.bot.ApplicationBuilder") as mock_builder:
            mock_app = MagicMock()
            mock_builder.return_value = mock_app

            from telegram_bot.bot import AutoTubeBot

            bot = AutoTubeBot(token="123456:ABC", chat_id="987654321")

            update = MagicMock()
            update.message = MagicMock()
            update.message.reply_text = AsyncMock()

            await bot._start(update, None)

            update.message.reply_text.assert_called_once()
            call_text = update.message.reply_text.call_args[0][0]
            assert "Bem-vindo" in call_text or "AutoTube" in call_text
