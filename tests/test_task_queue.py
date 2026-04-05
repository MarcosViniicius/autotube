import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestAsyncTaskQueue:
    """Tests for the AsyncTaskQueue class."""

    def test_task_queue_class_exists(self):
        """Test that AsyncTaskQueue class can be imported."""
        from core.task_queue import AsyncTaskQueue

        assert AsyncTaskQueue is not None

    def test_init_with_default_workers(self):
        """Test AsyncTaskQueue initializes with default workers."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()
        assert queue.num_workers == 3
        assert not queue.is_running

    def test_init_with_custom_workers(self):
        """Test AsyncTaskQueue initializes with custom workers."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue(num_workers=5)
        assert queue.num_workers == 5

    def test_queue_is_asyncio_queue(self):
        """Test that queue is an asyncio Queue."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()
        assert isinstance(queue.queue, asyncio.Queue)

    @pytest.mark.asyncio
    async def test_start_creates_workers(self):
        """Test that start creates worker tasks."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue(num_workers=2)
        await queue.start()

        assert queue.is_running
        assert len(queue.workers) == 2

        await queue.stop()

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """Test that start is idempotent (won't start twice)."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue(num_workers=2)
        await queue.start()
        initial_workers = len(queue.workers)

        await queue.start()

        assert len(queue.workers) == initial_workers

        await queue.stop()

    @pytest.mark.asyncio
    async def test_stop_sends_poison_pill(self):
        """Test that stop sends poison pills to workers."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue(num_workers=2)
        await queue.start()

        await queue.stop()

        assert not queue.is_running
        assert queue.workers == []

    @pytest.mark.asyncio
    async def test_enqueue_adds_task(self):
        """Test that enqueue adds task to queue."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()
        task_func = AsyncMock()

        await queue.enqueue(task_func, "arg1", kwarg1="value1")

        assert queue.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_worker_executes_task(self):
        """Test that worker executes task function."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue(num_workers=1)
        task_func = AsyncMock()
        await queue.enqueue(task_func, "arg1")

        await queue.start()

        await asyncio.sleep(0.1)

        task_func.assert_called_once_with("arg1")

        await queue.stop()

    @pytest.mark.asyncio
    async def test_worker_handles_exception(self):
        """Test that worker handles task exceptions."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue(num_workers=1)
        queue.logger = MagicMock()

        async def failing_task():
            raise Exception("Task failed")

        await queue.enqueue(failing_task)
        await queue.start()

        await asyncio.sleep(0.1)

        assert queue.logger.error.called

        await queue.stop()

    @pytest.mark.asyncio
    async def test_worker_stops_on_poison(self):
        """Test that worker stops when receiving None (poison pill)."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue(num_workers=1)
        await queue.queue.put(None)

        await queue._worker("TestWorker")

    @pytest.mark.asyncio
    async def test_worker_handles_cancelled_error(self):
        """Test that worker handles CancelledError."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()
        queue.is_running = True

        with patch.object(queue.queue, "get", side_effect=asyncio.CancelledError):
            await queue._worker("TestWorker")

    @pytest.mark.asyncio
    async def test_multiple_workers_process_multiple_tasks(self):
        """Test that multiple workers process multiple tasks."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue(num_workers=2)
        task_func = AsyncMock()

        for i in range(4):
            await queue.enqueue(task_func, i)

        await queue.start()

        await asyncio.sleep(0.2)

        assert task_func.call_count >= 4

        await queue.stop()

    @pytest.mark.asyncio
    async def test_enqueue_logs_debug(self):
        """Test that enqueue logs debug message."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue()
        queue.logger = MagicMock()
        task_func = MagicMock()
        task_func.__name__ = "test_task"

        await queue.enqueue(task_func)

        assert queue.logger.debug.called

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full lifecycle: start, enqueue, process, stop."""
        from core.task_queue import AsyncTaskQueue

        queue = AsyncTaskQueue(num_workers=2)
        results = []

        async def task(val):
            results.append(val)

        for i in range(3):
            await queue.enqueue(task, i)

        await queue.start()

        await asyncio.sleep(0.3)

        await queue.stop()

        assert len(results) == 3
        assert sorted(results) == [0, 1, 2]
