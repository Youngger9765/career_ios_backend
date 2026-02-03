"""
Integration tests for rate limiting on authentication endpoints

Tests rate limiting functionality to prevent abuse and brute force attacks.
Rate limits are configured in app/core/config.py:
- Registration: 3/hour (effective limit in tests)
- Login: 5/minute (effective limit in tests)
- Password Reset: 3/hour (effective limit in tests)

Note: Password must be at least 12 characters for registration.
Note: Rate limiter uses in-memory storage, so tests may affect each other if run in parallel.
"""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor


class TestRateLimiting:
    """Test rate limiting on authentication endpoints"""

    def test_register_rate_limit_enforced(self, db_session: Session):
        """Test registration rate limit blocks excess requests"""
        with TestClient(app) as client:
            # Make requests up to the limit
            limit = settings.RATE_LIMIT_REGISTER_PER_HOUR

            for i in range(limit):
                response = client.post(
                    "/api/auth/register",
                    json={
                        "email": f"test{i}@example.com",
                        "password": "ValidPassword123!",  # 12+ chars required
                        "tenant_id": "career",
                    },
                )
                # All requests within limit should succeed (201) or fail for other reasons (not 429)
                assert response.status_code != 429, f"Request {i+1} got rate limited prematurely"

            # The next request should be rate limited
            response = client.post(
                "/api/auth/register",
                json={
                    "email": f"test{limit}@example.com",
                    "password": "ValidPassword123!",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 429, f"Expected 429, got {response.status_code}"
            response_data = response.json()
            assert "detail" in response_data or "error" in response_data

    def test_login_rate_limit_enforced(self, db_session: Session):
        """Test login rate limit blocks excess requests"""
        # Create test counselor
        counselor = Counselor(
            id=uuid4(),
            email="logintest@example.com",
            username="logintest",
            full_name="Login Test",
            hashed_password=hash_password("ValidPassword123!"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            # Make requests up to the limit
            limit = settings.RATE_LIMIT_LOGIN_PER_MINUTE

            for i in range(limit):
                response = client.post(
                    "/api/auth/login",
                    json={
                        "email": "logintest@example.com",
                        "password": "ValidPassword123!",
                        "tenant_id": "career",
                    },
                )
                # All requests within limit should succeed (200)
                assert response.status_code != 429, f"Request {i+1} got rate limited prematurely"

            # The next request should be rate limited
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "logintest@example.com",
                    "password": "ValidPassword123!",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 429, f"Expected 429, got {response.status_code}"
            response_data = response.json()
            assert "detail" in response_data or "error" in response_data

    def test_password_reset_rate_limit_enforced(self, db_session: Session):
        """Test password reset rate limit blocks excess requests"""
        # Create test counselor
        counselor = Counselor(
            id=uuid4(),
            email="resettest@example.com",
            username="resettest",
            full_name="Reset Test",
            hashed_password=hash_password("ValidPassword123!"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            # Make requests up to the limit
            limit = settings.RATE_LIMIT_PASSWORD_RESET_PER_HOUR

            for i in range(limit):
                response = client.post(
                    "/api/v1/auth/password-reset/request",  # Correct path
                    json={
                        "email": "resettest@example.com",
                        "tenant_id": "career",
                    },
                )
                # All requests within limit should succeed (200)
                assert response.status_code != 429, f"Request {i+1} got rate limited prematurely"

            # The next request should be rate limited
            response = client.post(
                "/api/v1/auth/password-reset/request",  # Correct path
                json={
                    "email": "resettest@example.com",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 429, f"Expected 429, got {response.status_code}"
            response_data = response.json()
            assert "detail" in response_data or "error" in response_data
