"""Test counselor billing mode fields"""
import pytest
from datetime import datetime, timezone
from app.models.counselor import Counselor, BillingMode


def test_counselor_default_billing_mode_is_subscription():
    """New counselors should default to subscription mode"""
    counselor = Counselor(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        tenant_id="test",
        role="counselor"
    )
    assert counselor.billing_mode == BillingMode.SUBSCRIPTION


def test_counselor_subscription_fields_exist():
    """Counselor should have subscription usage tracking fields"""
    counselor = Counselor(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        tenant_id="test",
        role="counselor",
        billing_mode=BillingMode.SUBSCRIPTION
    )
    assert hasattr(counselor, 'monthly_usage_limit_minutes')
    assert hasattr(counselor, 'monthly_minutes_used')
    assert hasattr(counselor, 'usage_period_start')


def test_subscription_default_limit_is_360_minutes():
    """Subscription users should default to 360 minute limit"""
    counselor = Counselor(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        tenant_id="test",
        role="counselor",
        billing_mode=BillingMode.SUBSCRIPTION
    )
    assert counselor.monthly_usage_limit_minutes == 360
