"""Usage schemas for billing and usage tracking."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UsageStatsResponse(BaseModel):
    """
    Usage statistics response for counselor.

    Includes both prepaid and subscription mode fields.
    Fields that don't apply to current billing mode will be None.
    """

    billing_mode: str = Field(..., description="Billing mode: 'prepaid' or 'subscription'")

    # Prepaid mode fields
    available_credits: Optional[float] = Field(
        None, description="Available credits (prepaid mode only)"
    )

    # Subscription mode fields
    monthly_limit_minutes: Optional[int] = Field(
        None, description="Monthly usage limit in minutes (subscription mode only)"
    )
    monthly_used_minutes: Optional[int] = Field(
        None, description="Minutes used in current period (subscription mode only)"
    )
    monthly_remaining_minutes: Optional[int] = Field(
        None, description="Minutes remaining in current period (subscription mode only)"
    )
    usage_percentage: Optional[float] = Field(
        None, description="Usage percentage of monthly limit (subscription mode only)"
    )
    is_limit_reached: Optional[bool] = Field(
        None, description="Whether monthly limit has been reached (subscription mode only)"
    )
    usage_period_start: Optional[datetime] = Field(
        None, description="Start of current usage period (subscription mode only)"
    )
    usage_period_end: Optional[datetime] = Field(
        None, description="End of current usage period (subscription mode only)"
    )
