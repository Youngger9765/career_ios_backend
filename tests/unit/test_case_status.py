"""
Unit tests for CaseStatus enum
TDD - Write test first (RED phase)
"""
import pytest

from app.models.case import CaseStatus


class TestCaseStatus:
    """Test CaseStatus enum values"""

    def test_case_status_is_integer(self):
        """Test that CaseStatus values are integers"""
        assert CaseStatus.NOT_STARTED.value == 0
        assert CaseStatus.IN_PROGRESS.value == 1
        assert CaseStatus.COMPLETED.value == 2

    def test_case_status_labels(self):
        """Test Chinese labels for case status"""
        status_labels = {
            CaseStatus.NOT_STARTED: "未進行",
            CaseStatus.IN_PROGRESS: "進行中",
            CaseStatus.COMPLETED: "已完成",
        }

        assert status_labels[CaseStatus.NOT_STARTED] == "未進行"
        assert status_labels[CaseStatus.IN_PROGRESS] == "進行中"
        assert status_labels[CaseStatus.COMPLETED] == "已完成"

    def test_case_status_from_int(self):
        """Test creating CaseStatus from integer"""
        assert CaseStatus(0) == CaseStatus.NOT_STARTED
        assert CaseStatus(1) == CaseStatus.IN_PROGRESS
        assert CaseStatus(2) == CaseStatus.COMPLETED

    def test_invalid_status_raises_error(self):
        """Test that invalid status value raises ValueError"""
        with pytest.raises(ValueError):
            CaseStatus(99)
