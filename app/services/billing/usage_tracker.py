"""Usage tracking service for counselor billing."""
from datetime import datetime, timedelta


class UsageTracker:
    """Service to track and manage counselor usage limits."""

    PERIOD_DAYS = 30

    def reset_if_period_expired(self, counselor) -> None:
        """
        Reset usage period if 30 days have elapsed.

        Args:
            counselor: Counselor model instance
        """
        # Only reset for subscription mode
        if counselor.billing_mode != "subscription":
            return

        # Check if period has expired
        if counselor.period_start_date is None:
            # First time - initialize period
            counselor.period_start_date = datetime.utcnow()
            counselor.monthly_usage = 0
            return

        days_elapsed = (datetime.utcnow() - counselor.period_start_date).days

        if days_elapsed >= self.PERIOD_DAYS:
            # Reset usage and start new period
            counselor.monthly_usage = 0
            counselor.period_start_date = datetime.utcnow()

    def is_limit_exceeded(self, counselor) -> bool:
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
        if counselor.monthly_limit is None:
            return False

        return counselor.monthly_usage >= counselor.monthly_limit

    def get_usage_stats(self, counselor) -> dict:
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
        limit = counselor.monthly_limit or 0
        used = counselor.monthly_usage or 0
        remaining = max(0, limit - used)

        # Calculate percentage (handle division by zero)
        if limit > 0:
            percentage = (used / limit) * 100
        else:
            percentage = 100.0 if used > 0 else 100.0  # 0/0 treated as 100%

        # Calculate period dates
        period_start = counselor.period_start_date
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
