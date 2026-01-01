"""
Integration tests for Organizations API
Tests organization management endpoints
"""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.counselor import Counselor
from app.models.organization import Organization


class TestOrganizationsAPI:
    """Test organization management endpoints"""

    def test_list_organizations_success(self, db_session: Session):
        """Test listing organizations returns user's organization"""
        # Create organization
        org = Organization(
            id=uuid4(),
            tenant_id="test_school",
            name="Test School",
            description="Test Description",
            is_active=True,
            counselor_count=0,
            client_count=0,
            session_count=0,
        )
        db_session.add(org)
        db_session.flush()

        # Create counselor
        counselor = Counselor(
            id=uuid4(),
            email="counselor@test.com",
            username="counselor1",
            full_name="Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="test_school",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        # Create access token
        token = create_access_token(
            {
                "sub": counselor.email,
                "tenant_id": counselor.tenant_id,
                "role": counselor.role.value,
            }
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/organizations", headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "organizations" in data
            assert len(data["organizations"]) == 1
            assert data["organizations"][0]["tenant_id"] == "test_school"
            assert data["organizations"][0]["name"] == "Test School"
            assert data["total"] == 1

    def test_list_organizations_multi_tenant_isolation(self, db_session: Session):
        """Test that users only see their own organization"""
        # Create two organizations
        org1 = Organization(
            id=uuid4(),
            tenant_id="school_a",
            name="School A",
            is_active=True,
        )
        org2 = Organization(
            id=uuid4(),
            tenant_id="school_b",
            name="School B",
            is_active=True,
        )
        db_session.add_all([org1, org2])
        db_session.flush()

        # Create counselor for school_a
        counselor = Counselor(
            id=uuid4(),
            email="counselor@schoola.com",
            username="counselorA",
            full_name="Counselor A",
            hashed_password=hash_password("password123"),
            tenant_id="school_a",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        token = create_access_token(
            {
                "sub": counselor.email,
                "tenant_id": counselor.tenant_id,
                "role": counselor.role.value,
            }
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/organizations", headers={"Authorization": f"Bearer {token}"}
            )

            assert response.status_code == 200
            data = response.json()
            # Should only see school_a
            assert len(data["organizations"]) == 1
            assert data["organizations"][0]["tenant_id"] == "school_a"

    def test_get_organization_by_id_success(self, db_session: Session):
        """Test getting organization details by ID"""
        org = Organization(
            id=uuid4(),
            tenant_id="test_school",
            name="Test School",
            description="Detailed description",
            is_active=True,
            counselor_count=5,
            client_count=10,
            session_count=20,
        )
        db_session.add(org)
        db_session.flush()

        counselor = Counselor(
            id=uuid4(),
            email="counselor@test.com",
            username="counselor1",
            full_name="Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="test_school",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        token = create_access_token(
            {
                "sub": counselor.email,
                "tenant_id": counselor.tenant_id,
                "role": counselor.role.value,
            }
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/organizations/{org.id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(org.id)
            assert data["tenant_id"] == "test_school"
            assert data["name"] == "Test School"
            assert data["description"] == "Detailed description"
            assert data["is_active"] is True

    def test_get_organization_not_found(self, db_session: Session):
        """Test getting non-existent organization returns 404"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor@test.com",
            username="counselor1",
            full_name="Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="test_school",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        token = create_access_token(
            {
                "sub": counselor.email,
                "tenant_id": counselor.tenant_id,
                "role": counselor.role.value,
            }
        )

        fake_id = uuid4()

        with TestClient(app) as client:
            response = client.get(
                f"/api/organizations/{fake_id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_create_organization_success(self, db_session: Session):
        """Test creating a new organization"""
        counselor = Counselor(
            id=uuid4(),
            email="admin@test.com",
            username="admin1",
            full_name="Admin User",
            hashed_password=hash_password("password123"),
            tenant_id="admin_tenant",
            role="admin",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        token = create_access_token(
            {
                "sub": counselor.email,
                "tenant_id": counselor.tenant_id,
                "role": counselor.role.value,
            }
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/organizations",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "tenant_id": "new_school",
                    "name": "New School",
                    "description": "A brand new school",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["tenant_id"] == "new_school"
            assert data["name"] == "New School"
            assert data["description"] == "A brand new school"
            assert data["is_active"] is True
            assert "id" in data

    def test_create_organization_duplicate_tenant_id(self, db_session: Session):
        """Test creating organization with duplicate tenant_id fails"""
        # Create existing organization
        org = Organization(
            id=uuid4(),
            tenant_id="existing_school",
            name="Existing School",
            is_active=True,
        )
        db_session.add(org)
        db_session.flush()

        counselor = Counselor(
            id=uuid4(),
            email="admin@test.com",
            username="admin1",
            full_name="Admin User",
            hashed_password=hash_password("password123"),
            tenant_id="admin_tenant",
            role="admin",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        token = create_access_token(
            {
                "sub": counselor.email,
                "tenant_id": counselor.tenant_id,
                "role": counselor.role.value,
            }
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/organizations",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "tenant_id": "existing_school",
                    "name": "Another School",
                    "description": "Should fail",
                },
            )

            assert response.status_code == 409
            assert "already exists" in response.json()["detail"].lower()

    def test_update_organization_success(self, db_session: Session):
        """Test updating organization details"""
        org = Organization(
            id=uuid4(),
            tenant_id="test_school",
            name="Old Name",
            description="Old description",
            is_active=True,
        )
        db_session.add(org)
        db_session.flush()

        counselor = Counselor(
            id=uuid4(),
            email="counselor@test.com",
            username="counselor1",
            full_name="Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="test_school",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        token = create_access_token(
            {
                "sub": counselor.email,
                "tenant_id": counselor.tenant_id,
                "role": counselor.role.value,
            }
        )

        with TestClient(app) as client:
            response = client.patch(
                f"/api/organizations/{org.id}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": "New Name",
                    "description": "New description",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "New Name"
            assert data["description"] == "New description"
            assert data["tenant_id"] == "test_school"  # Unchanged

    def test_delete_organization_soft_delete(self, db_session: Session):
        """Test deleting organization (soft delete)"""
        org = Organization(
            id=uuid4(),
            tenant_id="test_school",
            name="To Be Deleted",
            is_active=True,
        )
        db_session.add(org)
        db_session.flush()

        counselor = Counselor(
            id=uuid4(),
            email="counselor@test.com",
            username="counselor1",
            full_name="Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="test_school",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        token = create_access_token(
            {
                "sub": counselor.email,
                "tenant_id": counselor.tenant_id,
                "role": counselor.role.value,
            }
        )

        with TestClient(app) as client:
            response = client.delete(
                f"/api/organizations/{org.id}",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 204

            # Verify soft delete - is_active should be False
            db_session.refresh(org)
            assert org.is_active is False

    def test_get_organization_stats(self, db_session: Session):
        """Test getting organization statistics"""
        org = Organization(
            id=uuid4(),
            tenant_id="test_school",
            name="Test School",
            is_active=True,
            counselor_count=3,
            client_count=10,
            session_count=25,
        )
        db_session.add(org)
        db_session.flush()

        counselor = Counselor(
            id=uuid4(),
            email="counselor@test.com",
            username="counselor1",
            full_name="Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="test_school",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        token = create_access_token(
            {
                "sub": counselor.email,
                "tenant_id": counselor.tenant_id,
                "role": counselor.role.value,
            }
        )

        with TestClient(app) as client:
            response = client.get(
                f"/api/organizations/{org.id}/stats",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["tenant_id"] == "test_school"
            assert data["name"] == "Test School"
            assert "counselor_count" in data
            assert "client_count" in data
            assert "session_count" in data

    def test_list_organizations_requires_auth(self):
        """Test listing organizations requires authentication"""
        with TestClient(app) as client:
            response = client.get("/api/organizations")
            # System returns 403 for missing auth (FastAPI default)
            assert response.status_code == 403

    def test_list_organizations_pagination(self, db_session: Session):
        """Test organization list pagination"""
        org = Organization(
            id=uuid4(),
            tenant_id="test_school",
            name="Test School",
            is_active=True,
        )
        db_session.add(org)
        db_session.flush()

        counselor = Counselor(
            id=uuid4(),
            email="counselor@test.com",
            username="counselor1",
            full_name="Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="test_school",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        token = create_access_token(
            {
                "sub": counselor.email,
                "tenant_id": counselor.tenant_id,
                "role": counselor.role.value,
            }
        )

        with TestClient(app) as client:
            response = client.get(
                "/api/organizations?page=1&page_size=10",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 1
            assert data["page_size"] == 10
            assert "organizations" in data
