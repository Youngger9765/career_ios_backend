"""
Integration tests for authentication API
TDD - Write tests first
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor
from uuid import uuid4


class TestAuthAPI:
    """Test authentication endpoints"""

    def test_login_success(self, db_session: Session):
        """Test successful login returns access token"""
        with TestClient(app) as client:
            # Create test counselor
            counselor = Counselor(
                id=uuid4(),
                email="test@example.com",
                username="testuser",
                full_name="Test User",
                hashed_password=hash_password("password123"),
                tenant_id="career",
                role="counselor",
                is_active=True,
            )
            db_session.add(counselor)
            db_session.commit()

            # Attempt login
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "password123", "tenant_id": "career"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data
            assert isinstance(data["access_token"], str)
            assert len(data["access_token"]) > 0

    def test_login_wrong_password(self, db_session: Session):
        """Test login with wrong password returns 401"""
        with TestClient(app) as client:
            # Create test counselor
            counselor = Counselor(
                id=uuid4(),
                email="test@example.com",
                username="testuser",
                full_name="Test User",
                hashed_password=hash_password("correct_password"),
                tenant_id="career",
                role="counselor",
                is_active=True,
            )
            db_session.add(counselor)
            db_session.commit()

            # Attempt login with wrong password
            response = client.post(
                "/api/auth/login",
                json={"email": "test@example.com", "password": "wrong_password"},
            )

            assert response.status_code == 401
            assert response.json()["detail"] == "Incorrect email or password"

    def test_login_nonexistent_user(self):
        """Test login with nonexistent email returns 401"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": "nonexistent@example.com", "password": "password123", "tenant_id": "career"},
            )

            assert response.status_code == 401
            assert response.json()["detail"] == "Incorrect email or password"

    def test_login_inactive_user(self, db_session: Session):
        """Test login with inactive account returns 403"""
        with TestClient(app) as client:
            # Create inactive counselor
            counselor = Counselor(
                id=uuid4(),
                email="inactive@example.com",
                username="inactive",
                full_name="Inactive User",
                hashed_password=hash_password("password123"),
                tenant_id="career",
                role="counselor",
                is_active=False,
            )
            db_session.add(counselor)
            db_session.commit()

            response = client.post(
                "/api/auth/login",
                json={"email": "inactive@example.com", "password": "password123", "tenant_id": "career"},
            )

            assert response.status_code == 403
            assert response.json()["detail"] == "Account is inactive"

    def test_get_me_success(self, db_session: Session):
        """Test GET /me with valid token returns counselor info"""
        with TestClient(app) as client:
            # Create test counselor
            counselor = Counselor(
                id=uuid4(),
                email="me@example.com",
                username="meuser",
                full_name="Me User",
                hashed_password=hash_password("password123"),
                tenant_id="career",
                role="counselor",
                is_active=True,
            )
            db_session.add(counselor)
            db_session.commit()

            # Login to get token
            login_response = client.post(
                "/api/auth/login",
                json={"email": "me@example.com", "password": "password123", "tenant_id": "career"},
            )
            token = login_response.json()["access_token"]

            # Get current user info
            response = client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "me@example.com"
            assert data["username"] == "meuser"
            assert data["full_name"] == "Me User"
            assert data["role"] == "counselor"
            assert data["tenant_id"] == "career"
            assert data["is_active"] is True

    def test_get_me_no_token(self):
        """Test GET /me without token returns 403"""
        with TestClient(app) as client:
            response = client.get("/api/auth/me")

            assert response.status_code == 403

    def test_get_me_invalid_token(self):
        """Test GET /me with invalid token returns 401"""
        with TestClient(app) as client:
            response = client.get(
                "/api/auth/me",
                headers={"Authorization": "Bearer invalid_token_here"},
            )

            assert response.status_code == 401

    def test_update_me_success(self, db_session: Session):
        """Test PATCH /api/auth/me - Update counselor profile"""
        with TestClient(app) as client:
            # Create test counselor
            counselor = Counselor(
                id=uuid4(),
                email="update@example.com",
                username="updateuser",
                full_name="Update User",
                hashed_password=hash_password("password123"),
                tenant_id="career",
                role="counselor",
                is_active=True,
            )
            db_session.add(counselor)
            db_session.commit()

            # Login to get token
            login_response = client.post(
                "/api/auth/login",
                json={"email": "update@example.com", "password": "password123", "tenant_id": "career"},
            )
            token = login_response.json()["access_token"]

            # Update profile
            response = client.patch(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "full_name": "Updated Full Name",
                    "username": "updateduser",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["full_name"] == "Updated Full Name"
            assert data["username"] == "updateduser"
            assert data["email"] == "update@example.com"  # Email should not change

    def test_update_me_no_token(self):
        """Test PATCH /me without token returns 403"""
        with TestClient(app) as client:
            response = client.patch(
                "/api/auth/me",
                json={"full_name": "New Name"},
            )

            assert response.status_code == 403

    def test_update_me_invalid_token(self):
        """Test PATCH /me with invalid token returns 401"""
        with TestClient(app) as client:
            response = client.patch(
                "/api/auth/me",
                headers={"Authorization": "Bearer invalid_token_here"},
                json={"full_name": "New Name"},
            )

            assert response.status_code == 401
