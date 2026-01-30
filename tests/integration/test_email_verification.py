"""
Integration tests for email verification system

Tests the complete email verification workflow:
- Registration creates inactive users (when ENABLE_EMAIL_VERIFICATION=true)
- Inactive users cannot login
- Email verification activates users
- Resend verification email functionality
- Environment variable toggle works
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email_verification import create_verification_token
from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor


class TestEmailVerification:
    """Test email verification system"""

    @pytest.fixture(autouse=True)
    def reset_settings(self):
        """Reset settings to default values after each test to ensure isolation.

        This fixture automatically runs before/after each test to prevent
        test pollution when using monkeypatch to modify settings.
        """
        # Store original value
        original_email_verification = settings.ENABLE_EMAIL_VERIFICATION

        yield

        # Restore original value after test
        # Note: monkeypatch already handles cleanup, but this provides extra safety
        settings.ENABLE_EMAIL_VERIFICATION = original_email_verification

    @patch("app.api.auth.EmailSenderService")
    def test_register_creates_inactive_user_when_verification_enabled(
        self, mock_email_service, db_session: Session, monkeypatch
    ):
        """Test new users start with is_active=False when ENABLE_EMAIL_VERIFICATION=true"""
        # Ensure email verification is enabled
        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", True)

        # Mock email sending
        mock_instance = mock_email_service.return_value
        mock_instance.send_verification_email = AsyncMock()

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "SecurePass123!@#",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data  # Auto-login still works

            # Check database: user.is_active should be False
            result = db_session.execute(
                select(Counselor).where(
                    Counselor.email == "newuser@example.com",
                    Counselor.tenant_id == "career",
                )
            )
            counselor = result.scalar_one_or_none()
            assert counselor is not None
            assert counselor.is_active is False

            # Verify email was sent
            mock_instance.send_verification_email.assert_called_once()

    @patch("app.api.auth.EmailSenderService")
    def test_register_creates_active_user_when_verification_disabled(
        self, mock_email_service, db_session: Session, monkeypatch
    ):
        """Test ENABLE_EMAIL_VERIFICATION=false creates active users"""
        # Disable email verification
        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", False)

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "activeuser@example.com",
                    "password": "SecurePass123!@#",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 201

            # Check database: user.is_active should be True
            result = db_session.execute(
                select(Counselor).where(
                    Counselor.email == "activeuser@example.com",
                    Counselor.tenant_id == "career",
                )
            )
            counselor = result.scalar_one_or_none()
            assert counselor is not None
            assert counselor.is_active is True

            # Verify email was NOT sent
            mock_email_service.return_value.send_verification_email.assert_not_called()

    def test_login_blocked_for_unverified_user(self, db_session: Session):
        """Test unverified users cannot login"""
        # Create inactive user (unverified)
        counselor = Counselor(
            id=uuid4(),
            email="unverified@example.com",
            username="unverified",
            full_name="Unverified User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=False,  # Unverified
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            # Try to login
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "unverified@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )

            # Should return 403 Forbidden with verification message
            assert response.status_code == 403
            data = response.json()
            assert "Email not verified" in data["detail"]
            assert "verification link" in data["detail"]

    def test_verify_email_activates_user(self, db_session: Session):
        """Test /auth/verify-email activates user with valid token"""
        # Create inactive user
        counselor = Counselor(
            id=uuid4(),
            email="pending@example.com",
            username="pending",
            full_name="Pending User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=False,
        )
        db_session.add(counselor)
        db_session.commit()

        # Generate valid verification token
        verification_token = create_verification_token("pending@example.com", "career")

        with TestClient(app) as client:
            # POST /auth/verify-email with token
            response = client.post(
                "/api/auth/verify-email",
                json={"token": verification_token},
            )

            # Should return 200
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Email verified successfully"
            assert data["email"] == "pending@example.com"

            # Check database: user.is_active should be True
            db_session.refresh(counselor)
            assert counselor.is_active is True

    def test_verify_email_invalid_token(self, db_session: Session):
        """Test verification fails with invalid token"""
        with TestClient(app) as client:
            # POST /auth/verify-email with bad token
            response = client.post(
                "/api/auth/verify-email",
                json={"token": "invalid_token_here"},
            )

            # Should return 401 Unauthorized
            assert response.status_code == 401
            data = response.json()
            assert "Invalid or expired" in data["detail"]

    def test_verify_email_expired_token(self, db_session: Session):
        """Test verification fails with expired token"""
        # Create user
        counselor = Counselor(
            id=uuid4(),
            email="expired@example.com",
            username="expired",
            full_name="Expired User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=False,
        )
        db_session.add(counselor)
        db_session.commit()

        # Generate token with past expiry
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        to_encode = {
            "sub": "expired@example.com",
            "tenant_id": "career",
            "type": "email_verification",
            "exp": expire,
        }
        expired_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        with TestClient(app) as client:
            # POST /auth/verify-email with expired token
            response = client.post(
                "/api/auth/verify-email",
                json={"token": expired_token},
            )

            # Should return 401
            assert response.status_code == 401
            data = response.json()
            assert "Invalid or expired" in data["detail"]

    def test_verify_email_wrong_token_type(self, db_session: Session):
        """Test verification fails with wrong token type (e.g., access token)"""
        # Create user
        counselor = Counselor(
            id=uuid4(),
            email="wrongtype@example.com",
            username="wrongtype",
            full_name="Wrong Type User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=False,
        )
        db_session.add(counselor)
        db_session.commit()

        # Generate token with wrong type
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
        to_encode = {
            "sub": "wrongtype@example.com",
            "tenant_id": "career",
            "type": "access_token",  # Wrong type
            "exp": expire,
        }
        wrong_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/verify-email",
                json={"token": wrong_token},
            )

            # Should return 401
            assert response.status_code == 401

    def test_verify_email_already_verified(self, db_session: Session):
        """Test verification returns success message for already verified users"""
        # Create already verified user
        counselor = Counselor(
            id=uuid4(),
            email="verified@example.com",
            username="verified",
            full_name="Verified User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,  # Already verified
        )
        db_session.add(counselor)
        db_session.commit()

        # Generate valid verification token
        verification_token = create_verification_token("verified@example.com", "career")

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/verify-email",
                json={"token": verification_token},
            )

            # Should return 200 with "already verified" message
            assert response.status_code == 200
            data = response.json()
            assert "already verified" in data["message"].lower()

    @patch("app.api.auth.EmailSenderService")
    def test_resend_verification_email(
        self, mock_email_service, db_session: Session
    ):
        """Test /auth/resend-verification sends new email"""
        # Create unverified user
        counselor = Counselor(
            id=uuid4(),
            email="resend@example.com",
            username="resend",
            full_name="Resend User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=False,
        )
        db_session.add(counselor)
        db_session.commit()

        # Mock email sending
        mock_instance = mock_email_service.return_value
        mock_instance.send_verification_email = AsyncMock()

        with TestClient(app) as client:
            # POST /auth/resend-verification
            response = client.post(
                "/api/auth/resend-verification",
                json={
                    "email": "resend@example.com",
                    "tenant_id": "career",
                },
            )

            # Should return 200 with success message
            assert response.status_code == 200
            data = response.json()
            assert "Verification email sent" in data["message"]

            # Verify email was sent
            mock_instance.send_verification_email.assert_called_once()
            call_args = mock_instance.send_verification_email.call_args
            assert call_args.kwargs["to_email"] == "resend@example.com"
            assert call_args.kwargs["tenant_id"] == "career"
            assert "verification_token" in call_args.kwargs

    @patch("app.api.auth.EmailSenderService")
    def test_resend_verification_already_verified(
        self, mock_email_service, db_session: Session
    ):
        """Test resend fails for already verified users"""
        # Create already verified user
        counselor = Counselor(
            id=uuid4(),
            email="alreadyverified@example.com",
            username="alreadyverified",
            full_name="Already Verified User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,  # Already verified
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            # Try to resend verification
            response = client.post(
                "/api/auth/resend-verification",
                json={
                    "email": "alreadyverified@example.com",
                    "tenant_id": "career",
                },
            )

            # Should return 400 Bad Request
            assert response.status_code == 400
            data = response.json()
            assert "already verified" in data["detail"].lower()

            # Verify email was NOT sent
            mock_email_service.return_value.send_verification_email.assert_not_called()

    @patch("app.api.auth.EmailSenderService")
    def test_resend_verification_nonexistent_user(
        self, mock_email_service, db_session: Session
    ):
        """Test resend returns success message for nonexistent users (security)"""
        with TestClient(app) as client:
            # POST /auth/resend-verification with nonexistent email
            response = client.post(
                "/api/auth/resend-verification",
                json={
                    "email": "nonexistent@example.com",
                    "tenant_id": "career",
                },
            )

            # Should return 200 with generic message (don't reveal if email exists)
            assert response.status_code == 200
            data = response.json()
            assert "If the email exists" in data["message"]

            # Verify email was NOT sent
            mock_email_service.return_value.send_verification_email.assert_not_called()

    @patch("app.api.auth.EmailSenderService")
    def test_verified_user_can_login(self, mock_email_service, db_session: Session):
        """Test verified users can login successfully"""
        # Create verified user
        counselor = Counselor(
            id=uuid4(),
            email="canlogin@example.com",
            username="canlogin",
            full_name="Can Login User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,  # Verified
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            # Login should succeed
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "canlogin@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data

    @patch("app.api.auth.EmailSenderService")
    def test_complete_verification_workflow(
        self, mock_email_service, db_session: Session, monkeypatch
    ):
        """Test complete workflow: register -> verify -> login"""
        # Enable email verification
        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", True)

        # Mock email sending
        mock_instance = mock_email_service.return_value
        mock_instance.send_verification_email = AsyncMock()

        with TestClient(app) as client:
            # Step 1: Register (creates inactive user)
            register_response = client.post(
                "/api/auth/register",
                json={
                    "email": "workflow@example.com",
                    "password": "SecurePass123!@#",
                    "tenant_id": "career",
                },
            )
            assert register_response.status_code == 201

            # Step 2: Login should fail (unverified)
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "workflow@example.com",
                    "password": "SecurePass123!@#",
                    "tenant_id": "career",
                },
            )
            assert login_response.status_code == 403

            # Step 3: Verify email
            verification_token = create_verification_token("workflow@example.com", "career")
            verify_response = client.post(
                "/api/auth/verify-email",
                json={"token": verification_token},
            )
            assert verify_response.status_code == 200

            # Step 4: Login should now succeed
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "workflow@example.com",
                    "password": "SecurePass123!@#",
                    "tenant_id": "career",
                },
            )
            assert login_response.status_code == 200
            data = login_response.json()
            assert "access_token" in data

    def test_verify_email_nonexistent_user(self, db_session: Session):
        """Test verification fails for user that doesn't exist"""
        # Generate valid token for nonexistent user
        verification_token = create_verification_token("nonexistent@example.com", "career")

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/verify-email",
                json={"token": verification_token},
            )

            # Should return 401
            assert response.status_code == 401
            data = response.json()
            assert "Invalid verification token" in data["detail"]

    def test_verify_email_wrong_tenant(self, db_session: Session):
        """Test verification fails with correct email but wrong tenant_id"""
        # Create user in "career" tenant
        counselor = Counselor(
            id=uuid4(),
            email="wrongtenant@example.com",
            username="wrongtenant",
            full_name="Wrong Tenant User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=False,
        )
        db_session.add(counselor)
        db_session.commit()

        # Generate token for different tenant
        verification_token = create_verification_token("wrongtenant@example.com", "island")

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/verify-email",
                json={"token": verification_token},
            )

            # Should return 401 (user not found with this email+tenant combination)
            assert response.status_code == 401
