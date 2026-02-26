"""
Integration tests for authentication API
TDD - Write tests first
"""
from datetime import datetime, timezone
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
            hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "password": "ValidP@ssw0rd123",
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
            hashed_password=hash_password("C0rrect!P@ssw0rd"),
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
                    "password": "Wr0ng!P@ssw0rd",
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
                    "password": "ValidP@ssw0rd123",
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
                hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 403
            # Check for inactive account message
            assert "not active" in response.json()["detail"]

    def test_get_me_success(self, db_session: Session):
        """Test GET /me with valid token returns counselor info"""
        with TestClient(app) as client:
            # Create test counselor
            counselor = Counselor(
                id=uuid4(),
                email="me@example.com",
                username="meuser",
                full_name="Me User",
                hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "password": "ValidP@ssw0rd123",
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

    def test_get_me_with_null_username_and_full_name(self, db_session: Session):
        """Test GET /me with counselor that has null username and full_name"""
        with TestClient(app) as client:
            # Create test counselor with null username and full_name
            counselor = Counselor(
                id=uuid4(),
                email="nulluser@example.com",
                username=None,
                full_name=None,
                hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "email": "nulluser@example.com",
                    "password": "ValidP@ssw0rd123",
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
            assert data["email"] == "nulluser@example.com"
            assert data["username"] is None
            assert data["full_name"] is None
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
                hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "password": "ValidP@ssw0rd123",
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

    def test_register_success_simplified(self, db_session: Session, monkeypatch):
        """Test successful simplified registration (email + password only) returns access token"""
        # Disable email verification for this legacy test
        from app.core.config import settings

        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", False)

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
            assert counselor.username is None  # Username is optional now
            assert counselor.full_name is None  # Full name is optional now
            assert counselor.is_active is True

    def test_register_success_with_optional_fields(
        self, db_session: Session, monkeypatch
    ):
        """Test successful registration with optional username and full_name (backward compatibility)"""
        # Disable email verification for this legacy test
        from app.core.config import settings

        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", False)

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "newuser2@example.com",
                    "username": "newuser",
                    "password": "ValidP@ssw0rd123",
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
                    Counselor.email == "newuser2@example.com",
                    Counselor.tenant_id == "career",
                )
            )
            counselor = result.scalar_one_or_none()
            assert counselor is not None
            assert counselor.username == "newuser"
            assert counselor.full_name == "New User"
            assert counselor.is_active is True

    def test_register_duplicate_email_tenant(self, db_session: Session):
        """Test registration with duplicate email+tenant_id returns 409"""
        # Create existing counselor
        counselor = Counselor(
            id=uuid4(),
            email="existing@example.com",
            username="existing",
            full_name="Existing User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 409
            response_data = response.json()
            assert "type" in response_data  # RFC 7807 format
            assert "detail" in response_data
            assert "already exists" in response_data["detail"].lower()

    def test_register_duplicate_username(self, db_session: Session):
        """Test registration with duplicate username returns 409 (when username is provided)"""
        # Create existing counselor
        counselor = Counselor(
            id=uuid4(),
            email="user1@example.com",
            username="taken_username",
            full_name="User One",
            hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "password": "ValidP@ssw0rd123",
                    "full_name": "User Two",
                    "tenant_id": "career",
                    "role": "counselor",
                },
            )

            assert response.status_code == 409
            response_data = response.json()
            assert "type" in response_data  # RFC 7807 format
            assert "detail" in response_data
            assert "username" in response_data["detail"].lower()
            assert "already exists" in response_data["detail"].lower()

    def test_register_same_email_different_tenant(self, db_session: Session):
        """Test registration with same email but different tenant_id succeeds"""
        # Create counselor in career tenant
        counselor = Counselor(
            id=uuid4(),
            email="shared@example.com",
            username="career_user",
            full_name="Career User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "island",
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
                    "password": "ValidP@ssw0rd123",
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
                    "password": "short",  # Less than 8 characters
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422  # Validation error

    def test_delete_account_success(self, db_session: Session):
        """Test successful account deletion schedules for deletion with 14-day grace period"""
        with TestClient(app) as client:
            # Create test counselor
            counselor = Counselor(
                id=uuid4(),
                email="deleteme@example.com",
                username="deletemeuser",
                full_name="Delete Me",
                phone="+1234567890",
                hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "email": "deleteme@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

            # Delete account
            response = client.post(
                "/api/auth/delete-account",
                headers={"Authorization": f"Bearer {token}"},
                json={"password": "ValidP@ssw0rd123"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "14 days" in data["message"]

            # Verify in database — grace period: email/username/full_name preserved
            from sqlalchemy import select

            db_session.expire_all()
            result = db_session.execute(
                select(Counselor).where(Counselor.id == counselor.id)
            )
            updated_counselor = result.scalar_one_or_none()
            assert updated_counselor is not None
            # Email NOT anonymized yet (grace period active)
            assert updated_counselor.email == "deleteme@example.com"
            # Username and full_name preserved during grace period
            assert updated_counselor.username == "deletemeuser"
            assert updated_counselor.full_name == "Delete Me"
            assert updated_counselor.is_active is False
            assert updated_counselor.deleted_at is not None
            assert updated_counselor.hashed_password is not None

    def test_delete_account_no_token(self):
        """Test delete account without token returns 403"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/delete-account",
                json={"password": "ValidP@ssw0rd123"},
            )

            assert response.status_code == 403

    def test_delete_account_invalid_token(self):
        """Test delete account with invalid token returns 401"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/delete-account",
                headers={"Authorization": "Bearer invalid_token_here"},
                json={"password": "ValidP@ssw0rd123"},
            )

            assert response.status_code == 401

    def test_delete_account_login_restores_within_grace_period(
        self, db_session: Session
    ):
        """Test that login within 14-day grace period restores the account"""
        with TestClient(app) as client:
            # Create test counselor
            counselor = Counselor(
                id=uuid4(),
                email="gracelogin@example.com",
                username="gracelogin",
                full_name="Grace Login",
                hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "email": "gracelogin@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

            # Delete account
            delete_response = client.post(
                "/api/auth/delete-account",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )
            assert delete_response.status_code == 200

            # Login again within grace period — should succeed and restore account
            login_again_response = client.post(
                "/api/auth/login",
                json={
                    "email": "gracelogin@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )

            assert login_again_response.status_code == 200
            data = login_again_response.json()
            assert data["account_restored"] is True
            assert "access_token" in data

            # Verify account is restored in database
            from sqlalchemy import select

            db_session.expire_all()
            result = db_session.execute(
                select(Counselor).where(Counselor.id == counselor.id)
            )
            restored = result.scalar_one_or_none()
            assert restored is not None
            assert restored.is_active is True
            assert restored.deleted_at is None

    def test_delete_account_login_fails_after_grace_period(self, db_session: Session):
        """Test that login after 14-day grace period returns 403 permanently deleted"""
        from datetime import timedelta

        with TestClient(app) as client:
            # Create test counselor already in expired grace period state
            counselor = Counselor(
                id=uuid4(),
                email="expiredgrace@example.com",
                username="expiredgrace",
                full_name="Expired Grace",
                hashed_password=hash_password("ValidP@ssw0rd123"),
                tenant_id="career",
                role="counselor",
                is_active=False,
                deleted_at=datetime.now(timezone.utc) - timedelta(days=15),
            )
            db_session.add(counselor)
            db_session.commit()

            # Login should fail — grace period expired
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "expiredgrace@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )

            assert login_response.status_code == 403
            assert "permanently deleted" in login_response.json()["detail"]

    def test_delete_account_no_anonymization_immediately(self, db_session: Session):
        """Test that deletion does NOT anonymize email/username/full_name immediately"""
        from sqlalchemy import select

        with TestClient(app) as client:
            # Create test counselor
            counselor = Counselor(
                id=uuid4(),
                email="noanon@example.com",
                username="noanonuser",
                full_name="No Anon User",
                phone="+1234567890",
                hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "email": "noanon@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

            # Delete account
            delete_response = client.post(
                "/api/auth/delete-account",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )
            assert delete_response.status_code == 200

            # Verify DB: PII NOT anonymized during grace period
            db_session.expire_all()
            result = db_session.execute(
                select(Counselor).where(Counselor.id == counselor.id)
            )
            updated = result.scalar_one_or_none()
            assert updated is not None
            assert updated.email == "noanon@example.com"  # NOT anonymized
            assert updated.username == "noanonuser"  # NOT cleared
            assert updated.full_name == "No Anon User"  # NOT cleared
            assert updated.is_active is False
            assert updated.deleted_at is not None

    def test_restored_account_works_normally(self, db_session: Session):
        """Test that a restored account can use the API normally after grace period restore"""
        with TestClient(app) as client:
            # Create test counselor
            counselor = Counselor(
                id=uuid4(),
                email="restoredworks@example.com",
                username="restoredworks",
                full_name="Restored Works",
                hashed_password=hash_password("ValidP@ssw0rd123"),
                tenant_id="career",
                role="counselor",
                is_active=True,
            )
            db_session.add(counselor)
            db_session.commit()

            # Login to get initial token
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "restoredworks@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

            # Delete account
            delete_response = client.post(
                "/api/auth/delete-account",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )
            assert delete_response.status_code == 200

            # Restore via login within grace period
            restore_response = client.post(
                "/api/auth/login",
                json={
                    "email": "restoredworks@example.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )
            assert restore_response.status_code == 200
            assert restore_response.json()["account_restored"] is True
            new_token = restore_response.json()["access_token"]

            # Use /me endpoint with restored token — should work normally
            me_response = client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {new_token}"},
            )
            assert me_response.status_code == 200
            me_data = me_response.json()
            assert me_data["email"] == "restoredworks@example.com"
            assert me_data["is_active"] is True
