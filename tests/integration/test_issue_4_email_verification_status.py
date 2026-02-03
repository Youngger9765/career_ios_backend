"""
Integration tests for Issue #4: Email Verification Status in API Responses
TDD - Write tests first
"""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor


class TestIssue4EmailVerificationStatus:
    """Test email verification status fields in auth API responses"""

    def test_register_response_includes_email_verification_status(
        self, db_session: Session, monkeypatch
    ):
        """Test register API returns email_verified, verification_email_sent, and message"""
        from app.core.config import settings

        # Enable email verification for this test
        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", True)

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 201
            data = response.json()

            # Existing fields
            assert "access_token" in data
            assert "token_type" in data
            assert data["token_type"] == "bearer"

            # NEW: Email verification status fields
            assert "email_verified" in data, "Missing email_verified field"
            assert data["email_verified"] is False, "New user should not be verified"

            assert (
                "verification_email_sent" in data
            ), "Missing verification_email_sent field"
            assert (
                data["verification_email_sent"] is True
            ), "Verification email should be sent"

            assert "message" in data, "Missing message field"
            assert "email" in data["message"].lower(), "Message should mention email"

    def test_login_success_response_includes_email_verified(self, db_session: Session):
        """Test login API returns email_verified in user object"""
        # Create verified counselor
        counselor = Counselor(
            id=uuid4(),
            email="verified@example.com",
            username="verifieduser",
            full_name="Verified User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
            email_verified=True,  # Verified user
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "verified@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Existing fields
            assert "access_token" in data
            assert "user" in data

            # NEW: email_verified in user object
            assert (
                "email_verified" in data["user"]
            ), "Missing email_verified in user object"
            assert (
                data["user"]["email_verified"] is True
            ), "User should be marked as verified"

    def test_login_unverified_email_returns_403_with_error_code(
        self, db_session: Session, monkeypatch
    ):
        """Test login with unverified email returns 403 with EMAIL_NOT_VERIFIED error code"""
        from app.core.config import settings

        # Enable email verification for this test
        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", True)

        # Create unverified counselor
        counselor = Counselor(
            id=uuid4(),
            email="unverified@example.com",
            username="unverifieduser",
            full_name="Unverified User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
            email_verified=False,  # Unverified user
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "unverified@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 403, "Should return 403 Forbidden"
            data = response.json()

            # Check error structure (may vary based on implementation)
            # Could be {"detail": {"code": "...", "message": "..."}}
            # Or {"detail": "..."}
            assert "detail" in data, "Error response should have detail field"

            # Check for error code or message indicating email not verified
            response_str = str(data).lower()
            assert (
                "email" in response_str and "verif" in response_str
            ), "Error should mention email verification"

    def test_register_when_email_disabled_shows_verified_true(
        self, db_session: Session, monkeypatch
    ):
        """Test register when email verification is disabled shows email_verified=True"""
        from app.core.config import settings

        # Disable email verification
        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", False)

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "noverify@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 201
            data = response.json()

            # When verification is disabled, user should be immediately verified
            assert data["email_verified"] is True, "Should be verified when feature disabled"
            assert (
                data["verification_email_sent"] is False
            ), "Should not send email when feature disabled"
