"""Unit tests for UsageTracker service."""
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from app.services.billing.usage_tracker import UsageTracker


class TestUsageTracker:
    """Test UsageTracker service."""

    @pytest.fixture
    def tracker(self):
        """Create UsageTracker instance."""
        return UsageTracker()

    @pytest.fixture
    def counselor_subscription(self):
        """Create mock counselor with subscription billing."""
        counselor = Mock()
        counselor.billing_mode = "subscription"
        counselor.monthly_limit = 360
        counselor.monthly_usage = 300
        counselor.period_start_date = datetime.utcnow() - timedelta(days=15)
        return counselor

    @pytest.fixture
    def counselor_prepaid(self):
        """Create mock counselor with prepaid billing."""
        counselor = Mock()
        counselor.billing_mode = "prepaid"
        counselor.available_credits = 100
        counselor.monthly_limit = None
        counselor.monthly_usage = None
        counselor.period_start_date = None
        return counselor

    def test_reset_usage_period_if_expired(self, tracker, counselor_subscription):
        """Test usage resets after 30 days."""
        # Arrange: Set period start to 31 days ago
        counselor_subscription.period_start_date = datetime.utcnow() - timedelta(days=31)
        counselor_subscription.monthly_usage = 300

        # Act
        tracker.reset_if_period_expired(counselor_subscription)

        # Assert
        assert counselor_subscription.monthly_usage == 0
        # period_start_date should be updated (within 1 second of now)
        time_diff = abs((datetime.utcnow() - counselor_subscription.period_start_date).total_seconds())
        assert time_diff < 1

    def test_no_reset_if_period_active(self, tracker, counselor_subscription):
        """Test usage does NOT reset if period still active."""
        # Arrange: Set period start to 15 days ago
        original_usage = 300
        original_start = datetime.utcnow() - timedelta(days=15)
        counselor_subscription.period_start_date = original_start
        counselor_subscription.monthly_usage = original_usage

        # Act
        tracker.reset_if_period_expired(counselor_subscription)

        # Assert
        assert counselor_subscription.monthly_usage == original_usage
        assert counselor_subscription.period_start_date == original_start

    def test_check_limit_not_exceeded(self, tracker, counselor_subscription):
        """Test limit check returns False when not exceeded."""
        # Arrange: 300/360 used
        counselor_subscription.monthly_usage = 300
        counselor_subscription.monthly_limit = 360

        # Act
        exceeded = tracker.is_limit_exceeded(counselor_subscription)

        # Assert
        assert exceeded is False

    def test_check_limit_exceeded(self, tracker, counselor_subscription):
        """Test limit check returns True when at limit."""
        # Arrange: 360/360 used
        counselor_subscription.monthly_usage = 360
        counselor_subscription.monthly_limit = 360

        # Act
        exceeded = tracker.is_limit_exceeded(counselor_subscription)

        # Assert
        assert exceeded is True

    def test_check_limit_exceeded_over_limit(self, tracker, counselor_subscription):
        """Test limit check returns True when over limit."""
        # Arrange: 380/360 used (edge case)
        counselor_subscription.monthly_usage = 380
        counselor_subscription.monthly_limit = 360

        # Act
        exceeded = tracker.is_limit_exceeded(counselor_subscription)

        # Assert
        assert exceeded is True

    def test_get_usage_stats_subscription(self, tracker, counselor_subscription):
        """Test usage stats for subscription mode."""
        # Arrange
        counselor_subscription.monthly_usage = 300
        counselor_subscription.monthly_limit = 360
        period_start = datetime.utcnow() - timedelta(days=15)
        counselor_subscription.period_start_date = period_start

        # Act
        stats = tracker.get_usage_stats(counselor_subscription)

        # Assert
        assert stats["billing_mode"] == "subscription"
        assert stats["monthly_limit_minutes"] == 360
        assert stats["monthly_used_minutes"] == 300
        assert stats["monthly_remaining_minutes"] == 60
        assert stats["usage_percentage"] == pytest.approx(83.33, rel=0.01)
        assert stats["is_limit_reached"] is False
        assert stats["usage_period_start"] == period_start
        # usage_period_end should be 30 days after usage_period_start
        expected_end = period_start + timedelta(days=30)
        assert stats["usage_period_end"] == expected_end

    def test_get_usage_stats_prepaid(self, tracker, counselor_prepaid):
        """Test usage stats for prepaid mode."""
        # Arrange
        counselor_prepaid.available_credits = 100

        # Act
        stats = tracker.get_usage_stats(counselor_prepaid)

        # Assert
        assert stats["billing_mode"] == "prepaid"
        assert stats["available_credits"] == 100
        assert "monthly_limit_minutes" not in stats
        assert "monthly_used_minutes" not in stats
        assert "monthly_remaining_minutes" not in stats
        assert "usage_percentage" not in stats
        assert "is_limit_reached" not in stats
        assert "usage_period_start" not in stats
        assert "usage_period_end" not in stats

    def test_get_usage_stats_subscription_zero_limit(self, tracker, counselor_subscription):
        """Test usage stats with zero limit (edge case)."""
        # Arrange
        counselor_subscription.monthly_usage = 0
        counselor_subscription.monthly_limit = 0
        counselor_subscription.period_start_date = datetime.utcnow()

        # Act
        stats = tracker.get_usage_stats(counselor_subscription)

        # Assert
        assert stats["monthly_limit_minutes"] == 0
        assert stats["monthly_used_minutes"] == 0
        assert stats["monthly_remaining_minutes"] == 0
        assert stats["usage_percentage"] == 100.0  # 0/0 should be treated as 100%
        assert stats["is_limit_reached"] is True  # 0 >= 0

    def test_reset_initializes_first_time(self, tracker, counselor_subscription):
        """Should initialize period_start on first reset."""
        # Arrange
        counselor_subscription.period_start_date = None

        # Act
        tracker.reset_if_period_expired(counselor_subscription)

        # Assert
        assert counselor_subscription.period_start_date is not None
        assert counselor_subscription.monthly_usage == 0

    def test_prepaid_mode_not_checked_for_limits(self, tracker, counselor_prepaid):
        """Test prepaid counselors are not subject to limit checks."""
        # Act
        exceeded = tracker.is_limit_exceeded(counselor_prepaid)

        # Assert
        assert exceeded is False  # Prepaid always returns False

    def test_reset_only_affects_subscription_mode(self, tracker, counselor_prepaid):
        """Test reset does nothing for prepaid counselors."""
        # Arrange
        original_credits = 100
        counselor_prepaid.available_credits = original_credits

        # Act
        tracker.reset_if_period_expired(counselor_prepaid)

        # Assert
        assert counselor_prepaid.available_credits == original_credits
