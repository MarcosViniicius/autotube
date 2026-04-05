import pytest
import os
import json
import tempfile
from datetime import datetime, timedelta


class TestSchedulingManager:
    """Tests for the SchedulingManager class."""

    def test_scheduling_manager_class_exists(self):
        """Test that SchedulingManager class can be imported."""
        from core.scheduler import SchedulingManager

        assert SchedulingManager is not None

    def test_init_with_custom_files(self):
        """Test that SchedulingManager initializes with custom file paths."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            assert manager.state_file == state_file
            assert manager.log_file == log_file
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_init_loads_existing_state(self):
        """Test that SchedulingManager loads existing state."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_data = {"session_id": "test", "slots": []}
            json.dump(state_data, sf)
            sf.flush()
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            assert manager.state["session_id"] == "test"
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_init_handles_corrupted_state(self):
        """Test that SchedulingManager handles corrupted state."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            sf.write("invalid {{{")
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            assert manager.state == {}
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_save_state_updates_state(self):
        """Test that save_state updates internal state."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            config = {"days": 7}
            slots = [{"index": 0}]
            manager.save_state("session_123", config, slots)

            assert manager.state["session_id"] == "session_123"
            assert manager.state["config"] == config
            assert manager.state["slots"] == slots
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_update_slot_modifies_slot(self):
        """Test that update_slot modifies a slot."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_data = {
                "slots": [
                    {"index": 0, "status": "pendente"},
                    {"index": 1, "status": "pendente"},
                ]
            }
            json.dump(state_data, sf)
            sf.flush()
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            manager.update_slot(0, {"status": "processado"})

            assert manager.state["slots"][0]["status"] == "processado"
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_generate_slots_with_custom_hours(self):
        """Test slot generation with custom hours."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            slots = manager.generate_slots(
                days=2,
                posts_per_day=2,
                start_hour=8,
                interval_hours=4,
                custom_hours=[8, 14],
            )
            assert len(slots) == 4
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_generate_slots_with_interval(self):
        """Test slot generation with interval."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            slots = manager.generate_slots(
                days=1,
                posts_per_day=3,
                start_hour=10,
                interval_hours=4,
                custom_hours=None,
            )
            assert len(slots) == 3
            hours = [datetime.fromisoformat(s["scheduled_time"]).hour for s in slots]
            assert hours == [10, 14, 18]
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_generate_slots_respects_hour_limit(self):
        """Test that slots respect 24-hour limit."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            slots = manager.generate_slots(
                days=1,
                posts_per_day=10,
                start_hour=20,
                interval_hours=3,
                custom_hours=None,
            )
            hours = [datetime.fromisoformat(s["scheduled_time"]).hour for s in slots]
            assert all(h < 24 for h in hours)
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_generate_slots_structure(self):
        """Test that generated slots have correct structure."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            slots = manager.generate_slots(
                days=1,
                posts_per_day=1,
                start_hour=10,
                interval_hours=4,
                custom_hours=None,
            )

            slot = slots[0]
            assert "index" in slot
            assert "scheduled_time" in slot
            assert "status" in slot
            assert slot["status"] == "pendente"
            assert "project_id" in slot
            assert "video_path" in slot
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_get_pending_slots(self):
        """Test get_pending_slots returns correct slots."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_data = {
                "slots": [
                    {"index": 0, "status": "pendente"},
                    {"index": 1, "status": "processado"},
                    {"index": 2, "status": "pendente_log"},
                    {"index": 3, "status": "agendado_api"},
                    {"index": 4, "status": "rotulado"},
                ]
            }
            json.dump(state_data, sf)
            sf.flush()
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            pending = manager.get_pending_slots()
            assert len(pending) == 4
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_get_pending_slots_empty_state(self):
        """Test get_pending_slots with empty state."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            pending = manager.get_pending_slots()
            assert pending == []
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_log_error_writes_to_file(self):
        """Test that log_error writes to log file."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            manager.log_error(
                slot_index=0,
                scheduled_time="2024-01-01T10:00:00",
                path="/path/to/video.mp4",
                stage="render",
                error="Render failed",
            )

            with open(log_file, "r") as f:
                content = f.read()
            assert "SLOT: 0" in content
            assert "ERROR: Render failed" in content
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_reschedule_pending_slots_method_exists(self):
        """Test that reschedule_pending_slots method exists."""
        from core.scheduler import SchedulingManager

        assert hasattr(SchedulingManager, "reschedule_pending_slots")

    def test_reschedule_pending_slots_updates_times(self):
        """Test that reschedule_pending_slots updates scheduled times."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_data = {
                "session_id": "test",
                "config": {
                    "days": 7,
                    "posts_per_day": 2,
                    "start_hour": 8,
                    "interval_hours": 4,
                    "custom_hours": None,
                },
                "slots": [
                    {
                        "index": 0,
                        "status": "pendente",
                        "scheduled_time": "2024-01-01T08:00:00",
                    },
                    {
                        "index": 1,
                        "status": "pendente_log",
                        "scheduled_time": "2024-01-01T12:00:00",
                    },
                ],
            }
            json.dump(state_data, sf)
            sf.flush()
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            original_times = [s["scheduled_time"] for s in manager.state["slots"]]
            manager.reschedule_pending_slots()

            new_times = [s["scheduled_time"] for s in manager.state["slots"]]
            assert new_times != original_times
            for time_str in new_times:
                new_date = datetime.fromisoformat(time_str)
                assert new_date.date() >= (datetime.now() + timedelta(days=1)).date()
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_reschedule_pending_slots_no_pending(self):
        """Test that reschedule_pending_slots does nothing with no pending slots."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_data = {
                "session_id": "test",
                "config": {"days": 7},
                "slots": [
                    {
                        "index": 0,
                        "status": "agendado_api",
                        "scheduled_time": "2024-01-01T08:00:00",
                    },
                ],
            }
            json.dump(state_data, sf)
            sf.flush()
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            original_time = manager.state["slots"][0]["scheduled_time"]
            manager.reschedule_pending_slots()

            assert manager.state["slots"][0]["scheduled_time"] == original_time
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_get_scheduling_summary_method_exists(self):
        """Test that get_scheduling_summary method exists."""
        from core.scheduler import SchedulingManager

        assert hasattr(SchedulingManager, "get_scheduling_summary")

    def test_get_scheduling_summary_with_active_session(self):
        """Test get_scheduling_summary returns correct summary."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_data = {
                "session_id": "test",
                "slots": [
                    {
                        "index": 0,
                        "status": "agendado_api",
                        "scheduled_time": "2099-01-01T08:00:00",
                    },
                    {
                        "index": 1,
                        "status": "pendente",
                        "scheduled_time": "2099-01-01T12:00:00",
                    },
                    {
                        "index": 2,
                        "status": "pendente_log",
                        "scheduled_time": "2099-01-01T16:00:00",
                    },
                ],
            }
            json.dump(state_data, sf)
            sf.flush()
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            summary = manager.get_scheduling_summary()

            assert "Progresso" in summary or "concluídos" in summary.lower()
            assert "Restantes" in summary or "pendentes" in summary.lower()
            assert "Próximo" in summary or "agendado para" in summary
        finally:
            os.unlink(state_file)
            os.unlink(log_file)

    def test_get_scheduling_summary_empty_state(self):
        """Test get_scheduling_summary with empty state."""
        from core.scheduler import SchedulingManager

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as sf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as lf,
        ):
            state_file = sf.name
            log_file = lf.name

        try:
            manager = SchedulingManager(state_file=state_file, log_file=log_file)
            summary = manager.get_scheduling_summary()

            assert "Nenhuma sessão" in summary or "andamento" in summary.lower()
        finally:
            os.unlink(state_file)
            os.unlink(log_file)
