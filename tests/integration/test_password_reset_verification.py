"""
Integration tests for password reset verification code flow
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.counselor import Counselor
from app.models.password_reset import PasswordResetToken


@pytest.mark.asyncio
async def test_request_generates_verification_code(
    async_client: AsyncClient,
    db_session,
    test_counselor_subscription: Counselor,
):
    """Test that password reset request generates 6-digit verification code"""
    # Request password reset
    response = await async_client.post(
        "/api/v1/auth/password-reset/request",
        json={
            "email": test_counselor_subscription.email,
            "tenant_id": test_counselor_subscription.tenant_id,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Password reset email sent successfully"

    # Verify token was created in database
    result = db_session.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.email == test_counselor_subscription.email)
        .order_by(PasswordResetToken.created_at.desc())
    )
    reset_token = result.scalar_one_or_none()

    assert reset_token is not None, "No reset token found in database"

    # Verify verification code exists and is 6 digits
    assert reset_token.verification_code is not None
    assert len(reset_token.verification_code) == 6
    assert reset_token.verification_code.isdigit()

    # Verify code_expires_at is set to 10 minutes from now
    assert reset_token.code_expires_at is not None
    now = datetime.now(timezone.utc)
    expected_expiry = now + timedelta(minutes=10)

    # Ensure timezone awareness for comparison
    code_expires_at = reset_token.code_expires_at
    if code_expires_at.tzinfo is None:
        code_expires_at = code_expires_at.replace(tzinfo=timezone.utc)

    # Allow 5 second tolerance for test execution time
    time_diff = abs((code_expires_at - expected_expiry).total_seconds())
    assert time_diff < 5, f"Expiry time diff: {time_diff}s"

    # Verify token_expires_at is still set (backward compatibility)
    assert reset_token.expires_at is not None


@pytest.mark.asyncio
async def test_request_without_email(
    async_client: AsyncClient,
    test_counselor_subscription: Counselor,
):
    """Test that request without email returns 400"""
    response = await async_client.post(
        "/api/v1/auth/password-reset/request",
        json={
            "tenant_id": test_counselor_subscription.tenant_id,
        },
    )

    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower() or "phone" in response.json()["detail"].lower()
