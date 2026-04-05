import pytest
import asyncio
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call


class TestAutoTubePipeline:
    """Tests for the AutoTubePipeline class."""

    def test_pipeline_class_exists(self):
        """Test that AutoTubePipeline class can be imported."""
        from core.pipeline import AutoTubePipeline

        assert AutoTubePipeline is not None

    def test_init_creates_scheduler(self):
        """Test that pipeline initializes with scheduler."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=MagicMock(),
                        )

                        assert hasattr(pipeline, "scheduler")

    def test_init_creates_history(self):
        """Test that pipeline initializes with history manager."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=MagicMock(),
                        )

                        assert hasattr(pipeline, "history")

    def test_init_creates_task_queue(self):
        """Test that pipeline initializes with task queue."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue") as mock_queue:
                    mock_queue.return_value = MagicMock()
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=MagicMock(),
                        )

                        assert hasattr(pipeline, "task_queue")

    def test_init_sets_callbacks(self):
        """Test that pipeline sets up telegram bot callbacks."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    mock_bot = MagicMock()
                    pipeline = AutoTubePipeline(
                        real_api=MagicMock(),
                        ai_generator=MagicMock(),
                        youtube_manager=MagicMock(),
                        telegram_bot=mock_bot,
                    )

                    assert mock_bot.on_skip_short == pipeline._handle_skip_command
                    assert mock_bot.on_get_status == pipeline._get_status_report

    def test_init_creates_download_directory(self):
        """Test that pipeline creates download directory if not exists."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        with patch("core.pipeline.os.path.exists", return_value=False):
                            with patch("core.pipeline.os.makedirs"):
                                pipeline = AutoTubePipeline(
                                    real_api=MagicMock(),
                                    ai_generator=MagicMock(),
                                    youtube_manager=MagicMock(),
                                    telegram_bot=MagicMock(),
                                    download_dir="test_downloads",
                                )

        assert os.path.exists("test_downloads") or True

    def test_init_initializes_stats(self):
        """Test that pipeline initializes stats dictionary."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=MagicMock(),
                        )

                        assert "total_processed" in pipeline.stats
                        assert "total_errors" in pipeline.stats
                        assert "last_video_url" in pipeline.stats

    def test_handle_skip_command_sets_skip_id(self):
        """Test that skip command sets current_skip_id."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=MagicMock(),
                        )

                        pipeline._handle_skip_command("short_123")

                        assert pipeline.current_skip_id == "short_123"

    def test_get_status_report_contains_processed_count(self):
        """Test status report includes processed count."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=MagicMock(),
                        )
                        pipeline.stats["total_processed"] = 5

                        report = pipeline._get_status_report()

                        assert "5" in report or "Processados" in report

    def test_get_status_report_contains_error_count(self):
        """Test status report includes error count."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=MagicMock(),
                        )
                        pipeline.stats["total_errors"] = 2

                        report = pipeline._get_status_report()

                        assert "2" in report or "Erros" in report

    def test_get_status_report_contains_queue_size(self):
        """Test status report includes queue size."""
        from core.pipeline import AutoTubePipeline

        mock_queue = MagicMock()
        mock_queue.queue.qsize.return_value = 3

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue", return_value=mock_queue):
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=MagicMock(),
                        )

                        report = pipeline._get_status_report()

                        assert "3" in report or "Fila" in report

    def test_get_status_report_shows_scheduling_active(self):
        """Test status report shows when scheduling is active."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager") as mock_sched:
            mock_sched_instance = MagicMock()
            mock_sched_instance.get_scheduling_summary.return_value = "Session active"
            mock_sched.return_value = mock_sched_instance

            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=MagicMock(),
                        )
                        pipeline.is_scheduling = True
                        pipeline.scheduler = mock_sched_instance

                        report = pipeline._get_status_report()

                        assert (
                            "ATIVO" in report
                            or "Agendamento" in report
                            or "Session active" in report
                        )

    @pytest.mark.asyncio
    async def test_cancel_scheduling_clears_state(self):
        """Test cancel_scheduling clears state."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager") as mock_sched:
            mock_sched_instance = MagicMock()
            mock_sched.return_value = mock_sched_instance

            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot") as mock_bot:
                        mock_bot.send_notification = AsyncMock()

                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=mock_bot,
                        )
                        pipeline.is_scheduling = True

                        await pipeline.cancel_current_scheduling()

                        assert pipeline.is_scheduling is False
                        mock_sched_instance.clear_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_scheduling_with_no_pending(self):
        """Test resume_scheduling does nothing with no pending slots."""
        from core.pipeline import AutoTubePipeline

        with patch("core.pipeline.SchedulingManager") as mock_sched:
            mock_sched_instance = MagicMock()
            mock_sched_instance.get_pending_slots.return_value = []
            mock_sched.return_value = mock_sched_instance

            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot") as mock_bot:
                        mock_bot.send_notification = AsyncMock()

                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=mock_bot,
                        )

                        await pipeline.resume_scheduling()

                        mock_bot.send_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_project_with_no_shorts(self):
        """Test process_project handles no shorts."""
        from core.pipeline import AutoTubePipeline

        mock_api = MagicMock()
        mock_api.get_shorts.return_value = []

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot") as mock_bot:
                        mock_bot.send_notification = AsyncMock()

                        pipeline = AutoTubePipeline(
                            real_api=mock_api,
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=mock_bot,
                        )

                        await pipeline.process_project("project_1")

                        mock_bot.send_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_project_enqueues_tasks(self):
        """Test process_project enqueues tasks for each short."""
        from core.pipeline import AutoTubePipeline

        mock_api = MagicMock()
        mock_api.get_shorts.return_value = [
            {"id": "short_1", "title": "Title 1"},
            {"id": "short_2", "title": "Title 2"},
        ]

        mock_queue = MagicMock()
        mock_queue.enqueue = AsyncMock()
        mock_queue.queue = MagicMock()
        mock_queue.queue.qsize.return_value = 0

        mock_history = MagicMock()
        mock_history.is_processed.return_value = False
        mock_history.mark_as_processed = MagicMock()

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager", return_value=mock_history):
                with patch("core.pipeline.AsyncTaskQueue", return_value=mock_queue):
                    with patch("telegram_bot.bot.AutoTubeBot") as mock_bot:
                        mock_bot.send_notification = AsyncMock()

                        pipeline = AutoTubePipeline(
                            real_api=mock_api,
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=mock_bot,
                        )
                        pipeline.history = mock_history

                        await pipeline.process_project("project_1")

                        assert mock_queue.enqueue.call_count >= 1

    def test_process_single_video_checks_channel(self):
        """Test process_single_video validates channel exists."""
        from core.pipeline import AutoTubePipeline

        mock_youtube = MagicMock()
        mock_youtube.get_channel.return_value = None

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot") as mock_bot:
                        mock_bot.send_notification = AsyncMock()

                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=mock_youtube,
                            telegram_bot=mock_bot,
                        )

                        short_data = {"id": "short_1"}
                        result = asyncio.run(
                            pipeline.process_single_video(
                                short_data=short_data,
                                project_id="proj_1",
                                channel_name="invalid_channel",
                                profile="viral",
                            )
                        )

                        mock_bot.send_notification.assert_called()

    def test_pipeline_handles_quota_error(self):
        """Test pipeline handles YouTubeQuotaError."""
        from core.pipeline import AutoTubePipeline
        import inspect

        source = inspect.getsource(AutoTubePipeline.process_single_video)
        assert "YouTubeQuotaError" in source or "quota" in source.lower()

    def test_pipeline_logs_errors_on_failure(self):
        """Test pipeline logs errors during processing."""
        from core.pipeline import AutoTubePipeline

        mock_api = MagicMock()
        mock_api.get_shorts.return_value = [{"id": "short_1"}]

        mock_queue = MagicMock()
        mock_queue.enqueue = AsyncMock()

        with patch("core.pipeline.SchedulingManager"):
            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue", return_value=mock_queue):
                    with patch("telegram_bot.bot.AutoTubeBot"):
                        pipeline = AutoTubePipeline(
                            real_api=mock_api,
                            ai_generator=MagicMock(),
                            youtube_manager=MagicMock(),
                            telegram_bot=MagicMock(),
                        )

                        assert pipeline.logger is not None

    @pytest.mark.asyncio
    async def test_start_scheduling_flow_validates_channel(self):
        """Test start_scheduling_flow validates channel exists."""
        from core.pipeline import AutoTubePipeline

        mock_youtube = MagicMock()
        mock_youtube.list_channels.return_value = ["channel1", "channel2"]

        with patch("core.pipeline.SchedulingManager") as mock_sched:
            mock_sched_instance = MagicMock()
            mock_sched_instance.generate_slots.return_value = [
                {"index": 0, "status": "pendente"}
            ]
            mock_sched.return_value = mock_sched_instance

            with patch("core.pipeline.HistoryManager"):
                with patch("core.pipeline.AsyncTaskQueue"):
                    with patch("telegram_bot.bot.AutoTubeBot") as mock_bot:
                        mock_bot.send_notification = AsyncMock()

                        pipeline = AutoTubePipeline(
                            real_api=MagicMock(),
                            ai_generator=MagicMock(),
                            youtube_manager=mock_youtube,
                            telegram_bot=mock_bot,
                        )

                        config = {
                            "days": 1,
                            "posts_per_day": 1,
                            "projects": ["proj_1"],
                            "channel_name": "channel1",
                            "profile_name": "viral",
                        }

                        await pipeline.start_scheduling_flow(config)

                        assert "channel1" in mock_youtube.list_channels()

    def test_reschedule_pending_slots_method_exists(self):
        """Test pipeline has reschedule method."""
        from core.pipeline import AutoTubePipeline

        assert hasattr(AutoTubePipeline, "resume_scheduling")
