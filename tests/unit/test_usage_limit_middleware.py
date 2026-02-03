"""Unit tests for usage limit enforcement middleware."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.middleware.usage_limit import check_usage_limit
from app.models.counselor import BillingMode


class TestUsageLimitMiddleware:
    """Test usage limit enforcement middleware."""

    @pytest.fixture
    def prepaid_counselor_with_credits(self):
        """Create prepaid counselor with available credits."""
        counselor = Mock()
        counselor.billing_mode = BillingMode.PREPAID
        counselor.available_credits = 100.0
        return counselor

    @pytest.fixture
    def prepaid_counselor_no_credits(self):
        """Create prepaid counselor with zero credits."""
        counselor = Mock()
        counselor.billing_mode = BillingMode.PREPAID
        counselor.available_credits = 0.0
        return counselor

    @pytest.fixture
    def subscription_counselor_under_limit(self):
        """Create subscription counselor under monthly limit."""
        counselor = Mock()
        counselor.billing_mode = BillingMode.SUBSCRIPTION
        counselor.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=15)
        counselor.monthly_usage_limit_minutes = 360
        counselor.monthly_minutes_used = 300
        counselor.usage_period_start = datetime.now(timezone.utc) - timedelta(days=15)
        return counselor

    @pytest.fixture
    def subscription_counselor_at_limit(self):
        """Create subscription counselor at monthly limit."""
        counselor = Mock()
        counselor.billing_mode = BillingMode.SUBSCRIPTION
        counselor.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=15)
        counselor.monthly_usage_limit_minutes = 360
        counselor.monthly_minutes_used = 360  # At limit
        counselor.usage_period_start = datetime.now(timezone.utc) - timedelta(days=15)
        return counselor

    @pytest.fixture
    def subscription_counselor_expired(self):
        """Create subscription counselor with expired subscription."""
        counselor = Mock()
        counselor.billing_mode = BillingMode.SUBSCRIPTION
        counselor.subscription_expires_at = datetime.now(timezone.utc) - timedelta(days=1)  # Expired
        counselor.monthly_usage_limit_minutes = 360
        counselor.monthly_minutes_used = 0
        counselor.usage_period_start = datetime.now(timezone.utc) - timedelta(days=15)
        return counselor

    @pytest.fixture
    def subscription_counselor_period_expired(self):
        """Create subscription counselor with expired usage period."""
        counselor = Mock()
        counselor.billing_mode = BillingMode.SUBSCRIPTION
        counselor.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=15)
        counselor.monthly_usage_limit_minutes = 360
        counselor.monthly_minutes_used = 350  # High usage
        counselor.usage_period_start = datetime.now(timezone.utc) - timedelta(days=31)  # Period expired
        return counselor

    def test_prepaid_with_credits_allowed(self, prepaid_counselor_with_credits):
        """Test prepaid counselor with credits is allowed."""
        # Act - should not raise
        check_usage_limit(prepaid_counselor_with_credits)
        # Assert - no exception means success

    def test_prepaid_no_credits_blocked(self, prepaid_counselor_no_credits):
        """Test prepaid counselor with zero credits is blocked."""
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            check_usage_limit(prepaid_counselor_no_credits)

        # Verify HTTP 402 Payment Required
        assert exc_info.value.status_code == 402
        assert exc_info.value.detail["code"] == "INSUFFICIENT_CREDITS"
        assert "額度不足" in exc_info.value.detail["message"]

    def test_subscription_under_limit_allowed(self, subscription_counselor_under_limit):
        """Test subscription counselor under limit is allowed."""
        # Mock UsageTracker
        with patch("app.middleware.usage_limit.UsageTracker") as mock_tracker:
            tracker_instance = mock_tracker.return_value
            tracker_instance.is_limit_exceeded.return_value = False

            # Act - should not raise
            check_usage_limit(subscription_counselor_under_limit)

            # Assert tracker methods were called
            tracker_instance.reset_if_period_expired.assert_called_once()
            tracker_instance.is_limit_exceeded.assert_called_once()

    def test_subscription_at_limit_blocked(self, subscription_counselor_at_limit):
        """Test subscription counselor at limit is blocked."""
        # Mock UsageTracker
        with patch("app.middleware.usage_limit.UsageTracker") as mock_tracker:
            tracker_instance = mock_tracker.return_value
            tracker_instance.is_limit_exceeded.return_value = True

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                check_usage_limit(subscription_counselor_at_limit)

            # Verify HTTP 429 Too Many Requests
            assert exc_info.value.status_code == 429
            assert exc_info.value.detail["code"] == "MONTHLY_USAGE_LIMIT_EXCEEDED"
            assert "本月使用額度已用盡" in exc_info.value.detail["message"]

    def test_subscription_expired_allowed_by_revenuecat(self, subscription_counselor_expired):
        """Test subscription counselor with expired subscription is allowed (RevenueCat manages validity).

        Backend no longer checks subscription_expires_at. RevenueCat is the single source of truth
        for subscription validity on iOS client side. Backend only enforces monthly usage limits.
        """
        # Mock UsageTracker
        with patch("app.middleware.usage_limit.UsageTracker") as mock_tracker:
            tracker_instance = mock_tracker.return_value
            tracker_instance.is_limit_exceeded.return_value = False

            # Act - should not raise (RevenueCat handles expiry)
            check_usage_limit(subscription_counselor_expired)

            # Assert tracker methods were called normally
            tracker_instance.reset_if_period_expired.assert_called_once()
            tracker_instance.is_limit_exceeded.assert_called_once()

    def test_subscription_auto_reset_period(self, subscription_counselor_period_expired):
        """Test subscription auto-resets usage when period expires."""
        # Mock UsageTracker
        with patch("app.middleware.usage_limit.UsageTracker") as mock_tracker:
            tracker_instance = mock_tracker.return_value
            # After reset, should not be at limit
            tracker_instance.is_limit_exceeded.return_value = False

            # Act - should not raise
            check_usage_limit(subscription_counselor_period_expired)

            # Assert tracker.reset_if_period_expired was called
            tracker_instance.reset_if_period_expired.assert_called_once_with(
                subscription_counselor_period_expired
            )
