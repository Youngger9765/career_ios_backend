"""Middleware for enforcing usage limits before session creation."""
from fastapi import HTTPException

from app.models.counselor import BillingMode, Counselor
from app.services.billing.usage_tracker import UsageTracker


def check_usage_limit(counselor: Counselor) -> None:
    """
    Check if counselor can create new session based on billing mode and usage.

    Args:
        counselor: Counselor model instance

    Raises:
        HTTPException: 402 if insufficient credits (prepaid mode)
        HTTPException: 429 if monthly usage limit exceeded (subscription mode)

    Notes:
        - Prepaid mode: Check available_credits > 0
        - Subscription mode: Auto-reset period, check monthly limit
          (RevenueCat manages subscription validity on iOS client side)
    """
    # Prepaid Mode: Check credits
    if counselor.billing_mode == BillingMode.PREPAID:
        if counselor.available_credits <= 0:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "INSUFFICIENT_CREDITS",
                    "message": "額度不足，請儲值後再試",
                    "available_credits": counselor.available_credits,
                },
            )
        return  # Allow if credits available

    # Subscription Mode: Check monthly limit only (RevenueCat manages subscription validity)
    if counselor.billing_mode == BillingMode.SUBSCRIPTION:
        # Auto-reset usage period if expired
        tracker = UsageTracker()
        tracker.reset_if_period_expired(counselor)

        # Check if monthly limit exceeded
        if tracker.is_limit_exceeded(counselor):
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "MONTHLY_USAGE_LIMIT_EXCEEDED",
                    "message": "本月使用額度已用盡，請等待下個計費週期或升級方案",
                    "monthly_limit": counselor.monthly_usage_limit_minutes,
                    "monthly_used": counselor.monthly_minutes_used,
                    "period_start": counselor.usage_period_start.isoformat()
                    if counselor.usage_period_start
                    else None,
                },
            )
