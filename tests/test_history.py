import pytest
import os
import json
import tempfile


class TestHistoryManager:
    """Tests for the HistoryManager class."""

    def test_history_manager_class_exists(self):
        """Test that HistoryManager class can be imported."""
        from core.history import HistoryManager

        assert HistoryManager is not None

    def test_init_with_custom_file(self):
        """Test that HistoryManager initializes with custom file path."""
        from core.history import HistoryManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([], f)
            temp_file = f.name

        try:
            manager = HistoryManager(history_file=temp_file)
            assert manager.history_file == temp_file
        finally:
            os.unlink(temp_file)

    def test_init_loads_existing_data(self):
        """Test that HistoryManager loads existing history."""
        from core.history import HistoryManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(["id1", "id2", "id3"], f)
            temp_file = f.name

        try:
            manager = HistoryManager(history_file=temp_file)
            assert "id1" in manager.processed_ids
            assert "id2" in manager.processed_ids
            assert "id3" in manager.processed_ids
        finally:
            os.unlink(temp_file)

    def test_init_handles_corrupted_file(self):
        """Test that HistoryManager handles corrupted JSON."""
        from core.history import HistoryManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {{{")
            temp_file = f.name

        try:
            manager = HistoryManager(history_file=temp_file)
            assert manager.processed_ids == set()
        finally:
            os.unlink(temp_file)

    def test_init_handles_empty_file(self):
        """Test that HistoryManager handles empty file."""
        from core.history import HistoryManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([], f)
            temp_file = f.name

        try:
            manager = HistoryManager(history_file=temp_file)
            assert manager.processed_ids == set()
        finally:
            os.unlink(temp_file)

    def test_is_processed_returns_true_for_existing(self):
        """Test is_processed returns True for existing IDs."""
        from core.history import HistoryManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(["existing_id"], f)
            temp_file = f.name

        try:
            manager = HistoryManager(history_file=temp_file)
            assert manager.is_processed("existing_id") is True
        finally:
            os.unlink(temp_file)

    def test_is_processed_returns_false_for_new(self):
        """Test is_processed returns False for new IDs."""
        from core.history import HistoryManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(["existing_id"], f)
            temp_file = f.name

        try:
            manager = HistoryManager(history_file=temp_file)
            assert manager.is_processed("new_id") is False
        finally:
            os.unlink(temp_file)

    def test_mark_as_processed_adds_id(self):
        """Test mark_as_processed adds new ID."""
        from core.history import HistoryManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([], f)
            temp_file = f.name

        try:
            manager = HistoryManager(history_file=temp_file)
            manager.mark_as_processed("new_id")
            assert "new_id" in manager.processed_ids
        finally:
            os.unlink(temp_file)

    def test_mark_as_processed_converts_to_string(self):
        """Test mark_as_processed converts ID to string."""
        from core.history import HistoryManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([], f)
            temp_file = f.name

        try:
            manager = HistoryManager(history_file=temp_file)
            manager.mark_as_processed(123)
            assert "123" in manager.processed_ids
        finally:
            os.unlink(temp_file)

    def test_get_all_processed_returns_list(self):
        """Test get_all_processed returns list."""
        from core.history import HistoryManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(["a", "b"], f)
            temp_file = f.name

        try:
            manager = HistoryManager(history_file=temp_file)
            result = manager.get_all_processed()
            assert isinstance(result, list)
            assert len(result) == 2
        finally:
            os.unlink(temp_file)
