"""
Integration tests for Password Reset API endpoints

Test Coverage:
1. Request password reset (happy path)
2. Request password reset (invalid email)
3. Request password reset (rate limiting)
4. Verify reset token (valid token)
5. Verify reset token (invalid/expired token)
6. Confirm password reset (happy path)
7. Confirm password reset (token reuse prevention)
8. Confirm password reset (weak password rejection)
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.counselor import Counselor, CounselorRole


@pytest.fixture(autouse=True)
def clear_rate_limit_cache():
    """Clear rate limit cache before each test"""
    from app.api.v1.password_reset import _rate_limit_cache

    _rate_limit_cache.clear()
    yield
    _rate_limit_cache.clear()


@pytest.fixture
def test_counselor(db_session: Session) -> Counselor:
    """Create a test counselor for password reset tests"""
    counselor = Counselor(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        hashed_password=hash_password("TestPassword123!"),
        tenant_id="test_tenant",
        role=CounselorRole.COUNSELOR,
        is_active=True,
        phone="+886912345678",
    )
    db_session.add(counselor)
    db_session.commit()
    db_session.refresh(counselor)
    return counselor


@pytest.mark.asyncio
class TestPasswordResetRequest:
    """Test POST /api/v1/auth/password-reset/request"""

    async def test_request_password_reset_success(
        self,
        async_client: AsyncClient,
        db_session: Session,
        test_counselor: Counselor,
    ):
        """Test successful password reset request"""
        response = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Password reset email sent successfully"
        assert "token" in data  # For testing purposes
        assert len(data["token"]) >= 32  # Token should be secure

    async def test_request_password_reset_invalid_email(
        self,
        async_client: AsyncClient,
    ):
        """Test password reset request with non-existent email"""
        response = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": "nonexistent@example.com",
                "tenant_id": "test_tenant",
            },
        )

        # Should return success to prevent user enumeration
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Password reset email sent successfully"
        assert data.get("token") is None  # No token for invalid email

    async def test_request_password_reset_rate_limiting(
        self,
        async_client: AsyncClient,
        test_counselor: Counselor,
    ):
        """Test rate limiting for password reset requests"""
        # First request should succeed
        response1 = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second request within 5 minutes should be rate limited
        response2 = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        assert response2.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response2.json()
        assert (
            "rate limit" in data["detail"].lower() or "wait" in data["detail"].lower()
        )

    async def test_request_password_reset_by_phone(
        self,
        async_client: AsyncClient,
        db_session: Session,
        test_counselor: Counselor,
    ):
        """Test password reset request using phone number"""
        # Update counselor with phone number
        test_counselor.phone = "+886912345678"
        db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "phone": test_counselor.phone,
                "tenant_id": test_counselor.tenant_id,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Password reset email sent successfully"
        assert "token" in data


@pytest.mark.asyncio
class TestPasswordResetVerify:
    """Test GET /api/v1/auth/password-reset/verify"""

    async def test_verify_valid_token(
        self,
        async_client: AsyncClient,
        test_counselor: Counselor,
    ):
        """Test verifying a valid reset token"""
        # First request a password reset
        response1 = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        token = response1.json()["token"]

        # Verify the token
        response2 = await async_client.get(
            f"/api/v1/auth/password-reset/verify?token={token}"
        )

        assert response2.status_code == status.HTTP_200_OK
        data = response2.json()
        assert data["valid"] is True
        assert data["email"] == test_counselor.email

    async def test_verify_invalid_token(
        self,
        async_client: AsyncClient,
    ):
        """Test verifying an invalid token"""
        response = await async_client.get(
            "/api/v1/auth/password-reset/verify?token=invalid_token_12345"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "invalid" in data["detail"].lower()

    async def test_verify_expired_token(
        self,
        async_client: AsyncClient,
        db_session: Session,
        test_counselor: Counselor,
    ):
        """Test verifying an expired token"""
        # Request password reset
        response1 = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        token = response1.json()["token"]

        # Manually expire the token in database
        from app.models.password_reset import PasswordResetToken

        db_token = db_session.query(PasswordResetToken).filter_by(token=token).first()
        db_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        # Verify the expired token
        response2 = await async_client.get(
            f"/api/v1/auth/password-reset/verify?token={token}"
        )

        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        data = response2.json()
        assert "expired" in data["detail"].lower()

    async def test_verify_used_token(
        self,
        async_client: AsyncClient,
        db_session: Session,
        test_counselor: Counselor,
    ):
        """Test verifying a token that has already been used"""
        # Request password reset
        response1 = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        token = response1.json()["token"]

        # Confirm password reset (uses the token)
        await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": "NewSecurePassword123!",
            },
        )

        # Try to verify the used token
        response2 = await async_client.get(
            f"/api/v1/auth/password-reset/verify?token={token}"
        )

        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        data = response2.json()
        assert "already used" in data["detail"].lower()


@pytest.mark.asyncio
class TestPasswordResetConfirm:
    """Test POST /api/v1/auth/password-reset/confirm"""

    async def test_confirm_password_reset_success(
        self,
        async_client: AsyncClient,
        db_session: Session,
        test_counselor: Counselor,
    ):
        """Test successful password reset confirmation"""
        old_password_hash = test_counselor.hashed_password

        # Request password reset
        response1 = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        token = response1.json()["token"]

        # Confirm password reset
        new_password = "NewSecurePassword123!"
        response2 = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": new_password,
            },
        )

        assert response2.status_code == status.HTTP_200_OK
        data = response2.json()
        assert data["message"] == "Password reset successfully"

        # Verify password was updated
        db_session.refresh(test_counselor)
        assert test_counselor.hashed_password != old_password_hash
        assert verify_password(new_password, test_counselor.hashed_password)

    async def test_confirm_password_reset_invalid_token(
        self,
        async_client: AsyncClient,
    ):
        """Test password reset confirmation with invalid token"""
        response = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": "invalid_token_12345",
                "new_password": "NewSecurePassword123!",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "invalid" in data["detail"].lower()

    async def test_confirm_password_reset_weak_password(
        self,
        async_client: AsyncClient,
        test_counselor: Counselor,
    ):
        """Test password reset confirmation with weak password"""
        # Request password reset
        response1 = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        token = response1.json()["token"]

        # Try to set a weak password
        weak_passwords = [
            "123456",  # Too weak
            "password",  # Common password
            "abc123",  # Too short
            "12345678",  # Only numbers
        ]

        for weak_password in weak_passwords:
            response2 = await async_client.post(
                "/api/v1/auth/password-reset/confirm",
                json={
                    "token": token,
                    "new_password": weak_password,
                },
            )

            assert response2.status_code == status.HTTP_400_BAD_REQUEST
            data = response2.json()
            assert "password" in data["detail"].lower()

    async def test_confirm_password_reset_token_reuse_prevention(
        self,
        async_client: AsyncClient,
        test_counselor: Counselor,
    ):
        """Test that reset token can only be used once"""
        # Request password reset
        response1 = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        token = response1.json()["token"]

        # First confirmation should succeed
        response2 = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": "NewSecurePassword123!",
            },
        )
        assert response2.status_code == status.HTTP_200_OK

        # Second confirmation with same token should fail
        response3 = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": "AnotherPassword456!",
            },
        )
        assert response3.status_code == status.HTTP_400_BAD_REQUEST
        data = response3.json()
        assert "already used" in data["detail"].lower()

    async def test_confirm_password_reset_expired_token(
        self,
        async_client: AsyncClient,
        db_session: Session,
        test_counselor: Counselor,
    ):
        """Test password reset confirmation with expired token"""
        # Request password reset
        response1 = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        token = response1.json()["token"]

        # Manually expire the token
        from app.models.password_reset import PasswordResetToken

        db_token = db_session.query(PasswordResetToken).filter_by(token=token).first()
        db_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()

        # Try to confirm with expired token
        response2 = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": "NewSecurePassword123!",
            },
        )

        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        data = response2.json()
        assert "expired" in data["detail"].lower()


@pytest.mark.asyncio
class TestPasswordResetEndToEnd:
    """End-to-end test for complete password reset flow"""

    async def test_complete_password_reset_flow(
        self,
        async_client: AsyncClient,
        db_session: Session,
        test_counselor: Counselor,
    ):
        """Test complete password reset flow from request to login"""
        original_password = "TestPassword123!"
        new_password = "NewSecurePassword456!"

        # Step 1: Request password reset
        response1 = await async_client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        assert response1.status_code == status.HTTP_200_OK
        token = response1.json()["token"]

        # Step 2: Verify token
        response2 = await async_client.get(
            f"/api/v1/auth/password-reset/verify?token={token}"
        )
        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["valid"] is True

        # Step 3: Confirm password reset
        response3 = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": token,
                "new_password": new_password,
            },
        )
        assert response3.status_code == status.HTTP_200_OK

        # Step 4: Verify old password no longer works
        response4 = await async_client.post(
            "/api/auth/login",
            json={
                "email": test_counselor.email,
                "password": original_password,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        assert response4.status_code == status.HTTP_401_UNAUTHORIZED

        # Step 5: Verify new password works
        response5 = await async_client.post(
            "/api/auth/login",
            json={
                "email": test_counselor.email,
                "password": new_password,
                "tenant_id": test_counselor.tenant_id,
            },
        )
        assert response5.status_code == status.HTTP_200_OK
        assert "access_token" in response5.json()
