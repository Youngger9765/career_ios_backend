"""
Integration tests for authentication API
TDD - Write tests first
"""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor


class TestAuthAPI:
    """Test authentication endpoints"""

    def test_login_success(self, db_session: Session):
        """Test successful login returns access token"""
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

        # Create client after database setup
        with TestClient(app) as client:
            # Attempt login
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
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

        with TestClient(app) as client:
            # Attempt login with wrong password
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "wrong_password",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 401
            assert (
                response.json()["detail"] == "Incorrect email, password, or tenant ID"
            )

    def test_login_nonexistent_user(self, db_session: Session):
        """Test login with nonexistent email returns 401"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 401
            assert (
                response.json()["detail"] == "Incorrect email, password, or tenant ID"
            )

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
                json={
                    "email": "inactive@example.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
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
                json={
                    "email": "me@example.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
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
                json={
                    "email": "update@example.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
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

    def test_register_success(self, db_session: Session):
        """Test successful registration returns access token"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "newuser@example.com",
                    "username": "newuser",
                    "password": "password123",
                    "full_name": "New User",
                    "tenant_id": "career",
                    "role": "counselor",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data
            assert isinstance(data["access_token"], str)
            assert len(data["access_token"]) > 0

            # Verify counselor was created in database
            from sqlalchemy import select

            result = db_session.execute(
                select(Counselor).where(
                    Counselor.email == "newuser@example.com",
                    Counselor.tenant_id == "career",
                )
            )
            counselor = result.scalar_one_or_none()
            assert counselor is not None
            assert counselor.username == "newuser"
            assert counselor.full_name == "New User"
            assert counselor.is_active is True

    def test_register_duplicate_email_tenant(self, db_session: Session):
        """Test registration with duplicate email+tenant_id returns 400"""
        # Create existing counselor
        counselor = Counselor(
            id=uuid4(),
            email="existing@example.com",
            username="existing",
            full_name="Existing User",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "existing@example.com",
                    "username": "newusername",
                    "password": "password123",
                    "full_name": "New User",
                    "tenant_id": "career",
                    "role": "counselor",
                },
            )

            assert response.status_code == 400
            assert "already exists" in response.json()["detail"].lower()

    def test_register_duplicate_username(self, db_session: Session):
        """Test registration with duplicate username returns 400"""
        # Create existing counselor
        counselor = Counselor(
            id=uuid4(),
            email="user1@example.com",
            username="taken_username",
            full_name="User One",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "user2@example.com",
                    "username": "taken_username",
                    "password": "password123",
                    "full_name": "User Two",
                    "tenant_id": "career",
                    "role": "counselor",
                },
            )

            assert response.status_code == 400
            assert "username" in response.json()["detail"].lower()
            assert "already exists" in response.json()["detail"].lower()

    def test_register_same_email_different_tenant(self, db_session: Session):
        """Test registration with same email but different tenant_id succeeds"""
        # Create counselor in career tenant
        counselor = Counselor(
            id=uuid4(),
            email="shared@example.com",
            username="career_user",
            full_name="Career User",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            # Register same email in different tenant should succeed
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "shared@example.com",
                    "username": "island_user",
                    "password": "password123",
                    "full_name": "Island User",
                    "tenant_id": "island",
                    "role": "counselor",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data

    def test_register_default_role(self, db_session: Session):
        """Test registration without role defaults to counselor"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "defaultrole@example.com",
                    "username": "defaultrole",
                    "password": "password123",
                    "full_name": "Default Role User",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 201

            # Verify role is set to counselor by default
            from sqlalchemy import select

            result = db_session.execute(
                select(Counselor).where(Counselor.email == "defaultrole@example.com")
            )
            counselor = result.scalar_one_or_none()
            assert counselor is not None
            assert counselor.role.value == "counselor"

    def test_register_password_min_length(self, db_session: Session):
        """Test registration with password less than 8 characters returns 422"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "shortpass@example.com",
                    "username": "shortpass",
                    "password": "short",  # Less than 8 characters
                    "full_name": "Short Pass User",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422  # Validation error
