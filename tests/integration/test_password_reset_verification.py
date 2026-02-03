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


# ===== Task 8: Verify Code Endpoint Tests =====


@pytest.mark.asyncio
async def test_verify_code_success(
    async_client: AsyncClient,
    db_session,
    test_counselor_subscription: Counselor,
):
    """Test that valid verification code returns 200"""
    # Request password reset
    response = await async_client.post(
        "/api/v1/auth/password-reset/request",
        json={
            "email": test_counselor_subscription.email,
            "tenant_id": test_counselor_subscription.tenant_id,
        },
    )
    assert response.status_code == 200

    # Get the verification code from database
    result = db_session.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.email == test_counselor_subscription.email)
        .order_by(PasswordResetToken.created_at.desc())
    )
    reset_token = result.scalar_one_or_none()
    assert reset_token is not None

    # Verify the code
    verify_response = await async_client.post(
        "/api/v1/auth/password-reset/verify-code",
        json={
            "email": test_counselor_subscription.email,
            "verification_code": reset_token.verification_code,
            "tenant_id": test_counselor_subscription.tenant_id,
        },
    )

    assert verify_response.status_code == 200
    data = verify_response.json()
    assert data["valid"] is True
    assert data["message"] == "Verification code is valid"


@pytest.mark.asyncio
async def test_verify_code_invalid(
    async_client: AsyncClient,
    db_session,
    test_counselor_subscription: Counselor,
):
    """Test that wrong verification code returns 400"""
    # Request password reset
    response = await async_client.post(
        "/api/v1/auth/password-reset/request",
        json={
            "email": test_counselor_subscription.email,
            "tenant_id": test_counselor_subscription.tenant_id,
        },
    )
    assert response.status_code == 200

    # Try to verify with wrong code
    verify_response = await async_client.post(
        "/api/v1/auth/password-reset/verify-code",
        json={
            "email": test_counselor_subscription.email,
            "verification_code": "000000",  # Wrong code
            "tenant_id": test_counselor_subscription.tenant_id,
        },
    )

    assert verify_response.status_code == 400
    assert "invalid" in verify_response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_code_expired(
    async_client: AsyncClient,
    db_session,
    test_counselor_subscription: Counselor,
):
    """Test that expired verification code returns 400"""
    # Request password reset
    response = await async_client.post(
        "/api/v1/auth/password-reset/request",
        json={
            "email": test_counselor_subscription.email,
            "tenant_id": test_counselor_subscription.tenant_id,
        },
    )
    assert response.status_code == 200

    # Get the verification code from database
    result = db_session.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.email == test_counselor_subscription.email)
        .order_by(PasswordResetToken.created_at.desc())
    )
    reset_token = result.scalar_one_or_none()
    assert reset_token is not None

    # Manually expire the code
    reset_token.code_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    # Try to verify expired code
    verify_response = await async_client.post(
        "/api/v1/auth/password-reset/verify-code",
        json={
            "email": test_counselor_subscription.email,
            "verification_code": reset_token.verification_code,
            "tenant_id": test_counselor_subscription.tenant_id,
        },
    )

    assert verify_response.status_code == 400
    assert "expired" in verify_response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_code_max_attempts_lockout(
    async_client: AsyncClient,
    db_session,
    test_counselor_subscription: Counselor,
):
    """Test that 5 failed verification attempts locks account for 15 minutes"""
    # Request password reset
    response = await async_client.post(
        "/api/v1/auth/password-reset/request",
        json={
            "email": test_counselor_subscription.email,
            "tenant_id": test_counselor_subscription.tenant_id,
        },
    )
    assert response.status_code == 200

    # Attempt 5 times with wrong code
    for i in range(5):
        verify_response = await async_client.post(
            "/api/v1/auth/password-reset/verify-code",
            json={
                "email": test_counselor_subscription.email,
                "verification_code": "000000",  # Wrong code
                "tenant_id": test_counselor_subscription.tenant_id,
            },
        )
        assert verify_response.status_code == 400

    # Check that account is locked
    result = db_session.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.email == test_counselor_subscription.email)
        .order_by(PasswordResetToken.created_at.desc())
    )
    reset_token = result.scalar_one_or_none()
    assert reset_token is not None
    assert reset_token.verify_attempts == 5
    assert reset_token.locked_until is not None

    # Check that locked_until is ~15 minutes in the future
    now = datetime.now(timezone.utc)
    expected_lockout = now + timedelta(minutes=15)
    locked_until = reset_token.locked_until
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    time_diff = abs((locked_until - expected_lockout).total_seconds())
    assert time_diff < 10, f"Lockout time diff: {time_diff}s"

    # Try to verify again (should still be locked)
    verify_response = await async_client.post(
        "/api/v1/auth/password-reset/verify-code",
        json={
            "email": test_counselor_subscription.email,
            "verification_code": reset_token.verification_code,
            "tenant_id": test_counselor_subscription.tenant_id,
        },
    )

    assert verify_response.status_code == 400
    assert "locked" in verify_response.json()["detail"].lower() or "too many" in verify_response.json()["detail"].lower()


# ===== Task 11: End-to-End Integration Test =====


class TestPasswordResetEndToEnd:
    """End-to-end password reset verification flow tests"""

    @pytest.mark.asyncio
    async def test_complete_password_reset_flow(
        self,
        async_client: AsyncClient,
        db_session,
        test_counselor_subscription: Counselor,
    ):
        """Test complete password reset flow: request → verify → confirm → login"""
        original_password = "original_password_123"
        new_password = "new_password_456"

        # Step 1: Request password reset
        request_response = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor_subscription.email,
                "tenant_id": test_counselor_subscription.tenant_id,
            },
        )
        assert request_response.status_code == 200
        assert request_response.json()["message"] == "Password reset email sent successfully"

        # Get verification code from database
        result = db_session.execute(
            select(PasswordResetToken)
            .where(PasswordResetToken.email == test_counselor_subscription.email)
            .order_by(PasswordResetToken.created_at.desc())
        )
        reset_token = result.scalar_one_or_none()
        assert reset_token is not None
        verification_code = reset_token.verification_code

        # Step 2: Verify verification code
        verify_response = await async_client.post(
            "/api/v1/auth/password-reset/verify-code",
            json={
                "email": test_counselor_subscription.email,
                "verification_code": verification_code,
                "tenant_id": test_counselor_subscription.tenant_id,
            },
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()
        assert verify_data["valid"] is True
        assert verify_data["message"] == "Verification code is valid"

        # Step 3: Confirm password reset
        confirm_response = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "verification_code": verification_code,
                "new_password": new_password,
                "email": test_counselor_subscription.email,
                "tenant_id": test_counselor_subscription.tenant_id,
            },
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["message"] == "Password reset successfully"

        # Verify token is marked as used
        db_session.refresh(reset_token)
        assert reset_token.used is True
        assert reset_token.used_at is not None

        # Step 4: Login with new password
        login_response = await async_client.post(
            "/api/auth/login",
            json={
                "email": test_counselor_subscription.email,
                "password": new_password,
                "tenant_id": test_counselor_subscription.tenant_id,
            },
        )
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data
        assert login_data["token_type"] == "bearer"

        # Step 5: Verify old password no longer works
        old_password_response = await async_client.post(
            "/api/auth/login",
            json={
                "email": test_counselor_subscription.email,
                "password": original_password,
                "tenant_id": test_counselor_subscription.tenant_id,
            },
        )
        assert old_password_response.status_code == 401
