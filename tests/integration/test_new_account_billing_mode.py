"""
Test to verify new accounts default to subscription mode.

This test validates the business requirement that all new accounts
should default to subscription billing mode (for RevenueCat integration),
rather than prepaid mode.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.counselor import Counselor, BillingMode

client = TestClient(app)


def test_new_registration_defaults_to_subscription(db_session: Session, monkeypatch):
    """
    Test that a new account created via registration defaults to subscription mode.

    Business context:
    - Frontend uses RevenueCat for subscription management
    - All new accounts should default to subscription mode, not prepaid
    - Existing accounts (like purpleice9765@msn.com) are NOT affected
    """
    # Disable email verification for this test
    from app.core.config import settings
    monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", False)

    # Register a new user
    response = client.post(
        "/api/auth/register",
        json={
            "email": "newsubscriber@example.com",
            "password": "SecurePass123!",
            "tenant_id": "test_tenant"
        }
    )

    assert response.status_code == 201  # Registration returns 201, not 200
    data = response.json()

    # Verify the account was created
    from sqlalchemy import select
    result = db_session.execute(
        select(Counselor).where(
            Counselor.email == "newsubscriber@example.com",
            Counselor.tenant_id == "test_tenant"
        )
    )
    counselor = result.scalar_one_or_none()

    assert counselor is not None
    assert counselor.billing_mode == BillingMode.SUBSCRIPTION, \
        f"Expected billing_mode=SUBSCRIPTION, got {counselor.billing_mode}"

    # Verify subscription fields have sensible defaults
    assert counselor.monthly_usage_limit_minutes == 360, \
        "Default subscription should have 360 minute (6 hour) limit"
    assert counselor.monthly_minutes_used == 0, \
        "New accounts should start with 0 minutes used"


def test_existing_prepaid_accounts_unaffected(db_session: Session):
    """
    Test that explicitly creating a prepaid account still works.

    This ensures backward compatibility for existing prepaid users
    (like purpleice9765@msn.com).
    """
    from app.core.security import hash_password

    # Explicitly create a prepaid counselor
    counselor = Counselor(
        email="prepaid_user@example.com",
        username="prepaid_user",
        hashed_password=hash_password("SecurePass123!"),
        tenant_id="test_tenant",
        role="counselor",
        billing_mode=BillingMode.PREPAID,
        available_credits=1000.0
    )

    db_session.add(counselor)
    db_session.commit()
    db_session.refresh(counselor)

    # Verify it's still prepaid
    assert counselor.billing_mode == BillingMode.PREPAID
    assert counselor.available_credits == 1000.0
