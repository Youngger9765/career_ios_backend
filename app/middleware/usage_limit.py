"""Middleware for enforcing usage limits before session creation."""
from datetime import datetime

from fastapi import HTTPException

from app.models.counselor import BillingMode, Counselor
from app.services.billing.usage_tracker import UsageTracker


def check_usage_limit(counselor: Counselor) -> None:
    """
    Check if counselor can create new session based on billing mode and usage.

    Args:
        counselor: Counselor model instance

    Raises:
        HTTPException: 402 if insufficient credits or expired subscription
        HTTPException: 429 if monthly usage limit exceeded

    Notes:
        - Prepaid mode: Check available_credits > 0
        - Subscription mode: Check expiry, auto-reset period, check limit
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

    # Subscription Mode: Check expiry, period, and limit
    if counselor.billing_mode == BillingMode.SUBSCRIPTION:
        # Check if subscription expired
        if counselor.subscription_expires_at is None or counselor.subscription_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "SUBSCRIPTION_EXPIRED",
                    "message": "訂閱已過期，請續訂後再試",
                    "subscription_expires_at": counselor.subscription_expires_at,
                },
            )

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
                    "period_start": counselor.usage_period_start,
                },
            )
