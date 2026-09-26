"""Tests for pytest-rerunfailures retry support."""

import pytest
from unittest import mock

from pytest_reportportal.service import PyTestService


class TestRetryDetection:
    """Tests for retry detection and state tracking."""

    def test_detect_retry_returns_execution_count(self):
        """Verify execution_count is returned."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock()
        test_item.execution_count = 1

        result = service._detect_retry_attempt(test_item)
        assert result == 1

    def test_detect_retry_second_execution(self):
        """Verify second execution is detected."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock()
        test_item.execution_count = 2

        result = service._detect_retry_attempt(test_item)
        assert result == 2

    def test_detect_retry_defaults_when_missing(self):
        """Verify defaults to 1 if attribute missing."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock(spec=[])

        result = service._detect_retry_attempt(test_item)
        assert result == 1

    def test_get_item_key_from_object_id(self):
        """Verify item key is based on object id."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock()
        key = service._get_item_key(test_item)

        assert key == str(id(test_item))

    def test_get_item_key_is_consistent(self):
        """Verify same object returns same key."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock()
        key1 = service._get_item_key(test_item)
        key2 = service._get_item_key(test_item)

        assert key1 == key2

    def test_retry_tracker_tracks_attempts(self):
        """Verify retry tracker records execution counts."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock()
        test_item.execution_count = 1

        key = service._get_item_key(test_item)
        service._retry_tracker[key] = {"last_reported_execution_count": 1}

        # Simulate second execution
        test_item.execution_count = 2
        current = service._detect_retry_attempt(test_item)
        last = service._retry_tracker[key]["last_reported_execution_count"]

        assert current > last


class TestRetryTransition:
    """Tests for retry transition handling."""

    def test_first_execution_registers_without_duplicate(self):
        """Verify first execution registers tree leaf without creating duplicate."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock()
        test_item.execution_count = 1
        test_item.location = ("test_file.py",)

        key = service._get_item_key(test_item)
        tree_leaf = {
            "name": "test_item",
            "item_id": "item-1",
            "exec": "IN_PROGRESS"
        }
        service._tree_path[test_item] = [tree_leaf]

        report = mock.MagicMock()
        report.when = "call"

        service.handle_retry_transition(test_item, report)

        tracker = service._retry_tracker[key]
        assert tracker["last_reported_execution_count"] == 1
        assert len(tracker["attempts"]) == 1
        assert tracker["attempts"][0]["execution_count"] == 1

    def test_ignores_non_call_and_setup_phases(self):
        """Verify teardown phases are ignored."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock()
        test_item.execution_count = 1

        key = service._get_item_key(test_item)

        report = mock.MagicMock()
        report.when = "teardown"

        service.handle_retry_transition(test_item, report)

        assert key not in service._retry_tracker

    def test_setup_phase_is_processed(self):
        """Verify setup phase is processed like call phase."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock()
        test_item.execution_count = 1

        key = service._get_item_key(test_item)
        tree_leaf = {
            "name": "test_item",
            "item_id": "item-1",
            "exec": "IN_PROGRESS"
        }
        service._tree_path[test_item] = [tree_leaf]

        report = mock.MagicMock()
        report.when = "setup"

        service.handle_retry_transition(test_item, report)

        tracker = service._retry_tracker[key]
        assert tracker["last_reported_execution_count"] == 1


class TestRetryMetadata:
    """Tests for retry metadata in payloads."""

    def test_finish_payload_includes_retry_fields(self):
        """Verify finish payload has retry metadata."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        leaf = {
            "name": "test_retry",
            "description": "Test",
            "status": "PASSED",
            "item_id": "item-123",
            "retry": True,
            "retry_of": "prev-item"
        }

        payload = service._build_finish_step_rq(leaf)

        assert payload.get("retry") == True
        assert payload.get("retry_of") == "prev-item"

    def test_finish_payload_defaults_retry_false(self):
        """Verify retry defaults to false."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        leaf = {
            "name": "test_normal",
            "description": "Test",
            "status": "PASSED",
            "item_id": "item-456"
        }

        payload = service._build_finish_step_rq(leaf)

        assert payload.get("retry") == False
        assert payload.get("retry_of") is None


class TestRetryStateManagement:
    """Tests for retry state tracking and cleanup."""

    def test_state_initialized(self):
        """Verify state dicts are initialized."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        assert hasattr(service, '_retry_tracker')
        assert hasattr(service, '_active_leaves')
        assert isinstance(service._retry_tracker, dict)
        assert isinstance(service._active_leaves, dict)

    def test_cleanup_clears_all_state(self):
        """Verify cleanup empties both dicts."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        service._retry_tracker["key1"] = {"data": "value"}
        service._active_leaves["key2"] = {"leaf": "data"}

        service.cleanup_retry_state()

        assert len(service._retry_tracker) == 0
        assert len(service._active_leaves) == 0

    def test_active_leaves_updated_for_new_attempt(self):
        """Verify active leaf is replaced for new attempt."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock()
        key = service._get_item_key(test_item)

        leaf1 = {"item_id": "attempt-1", "execution": 1}
        service._active_leaves[key] = leaf1

        assert service._active_leaves[key]["item_id"] == "attempt-1"

        leaf2 = {"item_id": "attempt-2", "execution": 2}
        service._active_leaves[key] = leaf2

        assert service._active_leaves[key]["item_id"] == "attempt-2"

    def test_post_log_uses_active_leaf(self):
        """Verify post_log routes to active leaf when present."""
        from pytest_reportportal.config import AgentConfig

        config = mock.MagicMock(spec=AgentConfig)
        service = PyTestService(config)

        test_item = mock.MagicMock()
        key = service._get_item_key(test_item)

        # Setup mocks
        service.rp = mock.MagicMock()

        active_leaf = {"item_id": "active-item-id"}
        service._active_leaves[key] = active_leaf

        tree_leaf = {"item_id": "tree-item-id"}
        service._tree_path[test_item] = [tree_leaf]

        service.post_log(test_item, "test message", "INFO")

        # Verify rp.log was called
        assert service.rp.log.called
        call_args = service.rp.log.call_args
        # The item_id should come from active_leaf
        assert call_args[1]["item_id"] == "active-item-id"
