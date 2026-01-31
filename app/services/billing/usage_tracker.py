"""Usage tracking service for counselor billing."""
from datetime import datetime, timedelta
from typing import Any, Dict

from app.models.counselor import Counselor


class UsageTracker:
    """Service to track and manage counselor usage limits."""

    PERIOD_DAYS = 30

    def reset_if_period_expired(self, counselor: Counselor) -> None:
        """
        Reset usage period if 30 days have elapsed.

        Args:
            counselor: Counselor model instance
        """
        # Only reset for subscription mode
        if counselor.billing_mode != "subscription":
            return

        # Check if period has expired
        if counselor.usage_period_start is None:
            # First time - initialize period
            from datetime import timezone

            counselor.usage_period_start = datetime.now(timezone.utc)
            counselor.monthly_minutes_used = 0
            return

        from datetime import timezone

        now_utc = datetime.now(timezone.utc)
        # Handle both timezone-aware and naive datetimes
        if counselor.usage_period_start.tzinfo is None:
            # Convert naive to aware
            from datetime import timezone as tz

            period_start = counselor.usage_period_start.replace(tzinfo=tz.utc)
        else:
            period_start = counselor.usage_period_start

        days_elapsed = (now_utc - period_start).days

        if days_elapsed >= self.PERIOD_DAYS:
            # Reset usage and start new period
            counselor.monthly_minutes_used = 0
            counselor.usage_period_start = now_utc

    def is_limit_exceeded(self, counselor: Counselor) -> bool:
        """
        Check if counselor has exceeded monthly limit.

        Args:
            counselor: Counselor model instance

        Returns:
            True if limit exceeded, False otherwise
        """
        # Prepaid mode has no monthly limits
        if counselor.billing_mode != "subscription":
            return False

        # Check if usage >= limit
        if counselor.monthly_usage_limit_minutes is None:
            return False

        return counselor.monthly_minutes_used >= counselor.monthly_usage_limit_minutes

    def get_usage_stats(self, counselor: Counselor) -> Dict[str, Any]:
        """
        Get usage statistics for counselor.

        Args:
            counselor: Counselor model instance

        Returns:
            Dict with usage statistics
        """
        if counselor.billing_mode == "prepaid":
            return {
                "billing_mode": "prepaid",
                "available_credits": counselor.available_credits,
            }

        # Subscription mode
        limit = counselor.monthly_usage_limit_minutes or 0
        used = counselor.monthly_minutes_used or 0
        remaining = max(0, limit - used)

        # Calculate percentage (handle division by zero)
        if limit > 0:
            percentage = (used / limit) * 100
        else:
            # When limit is 0, always return 100% to indicate "no quota available"
            # This applies both when used > 0 (over quota) and used = 0 (no quota)
            percentage = 100.0

        # Calculate period dates
        period_start = counselor.usage_period_start
        period_end = None
        if period_start:
            period_end = period_start + timedelta(days=self.PERIOD_DAYS)

        return {
            "billing_mode": "subscription",
            "monthly_limit_minutes": limit,
            "monthly_used_minutes": used,
            "monthly_remaining_minutes": remaining,
            "usage_percentage": round(percentage, 2),
            "is_limit_reached": used >= limit,
            "usage_period_start": period_start,
            "usage_period_end": period_end,
        }
