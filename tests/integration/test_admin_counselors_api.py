"""
Integration tests for Admin Counselor Management API
Following TDD approach - these tests define the expected behavior
"""
from uuid import uuid4

import pytest


class TestAdminListCounselors:
    """Test GET /api/v1/admin/counselors - List all counselors"""

    def test_list_counselors_success(self, client, admin_token, test_counselors):
        """Admin can list all counselors"""
        response = client.get(
            "/api/v1/admin/counselors",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "counselors" in data
        assert isinstance(data["counselors"], list)
        assert data["total"] > 0

        # Verify counselor fields
        counselor = data["counselors"][0]
        assert "id" in counselor
        assert "email" in counselor
        assert "username" in counselor
        assert "full_name" in counselor
        assert "phone" in counselor
        assert "tenant_id" in counselor
        assert "role" in counselor
        assert "is_active" in counselor
        assert "total_credits" in counselor
        assert "credits_used" in counselor
        assert "available_credits" in counselor
        assert "subscription_expires_at" in counselor
        assert "last_login" in counselor
        assert "created_at" in counselor

    def test_list_counselors_filter_by_tenant(
        self, client, admin_token, test_counselors
    ):
        """Admin can filter counselors by tenant_id within their scope"""
        response = client.get(
            "/api/v1/admin/counselors?tenant_id=career",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for counselor in data["counselors"]:
            assert counselor["tenant_id"] == "career"

    def test_list_counselors_filter_by_tenant_forbidden(
        self, client, admin_token, test_counselors
    ):
        """Admin cannot access other tenants without permission"""
        response = client.get(
            "/api/v1/admin/counselors?tenant_id=island_parents",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 403

    def test_list_counselors_filter_by_role(self, client, admin_token, test_counselors):
        """Admin can filter counselors by role"""
        response = client.get(
            "/api/v1/admin/counselors?role=counselor",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for counselor in data["counselors"]:
            assert counselor["role"] == "counselor"

    def test_list_counselors_filter_by_active_status(
        self, client, admin_token, test_counselors
    ):
        """Admin can filter counselors by is_active status"""
        response = client.get(
            "/api/v1/admin/counselors?is_active=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for counselor in data["counselors"]:
            assert counselor["is_active"] is True

    def test_list_counselors_search(self, client, admin_token, test_counselors):
        """Admin can search counselors by email, username, or full_name"""
        response = client.get(
            "/api/v1/admin/counselors?search=test_career",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["counselors"]) > 0
        # Should match email or username or full_name containing "test_career"

    def test_list_counselors_pagination(self, client, admin_token, test_counselors):
        """Admin can paginate counselor list"""
        response = client.get(
            "/api/v1/admin/counselors?limit=2&offset=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["counselors"]) <= 2

    def test_list_counselors_sorting(self, client, admin_token, test_counselors):
        """Admin can sort counselors by various fields"""
        response = client.get(
            "/api/v1/admin/counselors?sort_by=created_at&sort_order=desc",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["counselors"]) > 0
        # Verify sorting order (most recent first)

    def test_list_counselors_unauthorized(self, client, counselor_token):
        """Non-admin cannot list counselors"""
        response = client.get(
            "/api/v1/admin/counselors",
            headers={"Authorization": f"Bearer {counselor_token}"},
        )

        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()


class TestAdminGetCounselor:
    """Test GET /api/v1/admin/counselors/{counselor_id} - Get single counselor"""

    def test_get_counselor_success(self, client, admin_token, test_counselor_id):
        """Admin can view single counselor details"""
        response = client.get(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_counselor_id)
        assert "email" in data
        assert "username" in data
        assert "full_name" in data
        assert "tenant_id" in data
        assert "role" in data
        assert "is_active" in data
        assert "total_credits" in data
        assert "credits_used" in data
        assert "available_credits" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_counselor_not_found(self, client, admin_token):
        """Getting non-existent counselor returns 404"""
        fake_id = str(uuid4())
        response = client.get(
            f"/api/v1/admin/counselors/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404

    def test_get_counselor_unauthorized(
        self, client, counselor_token, test_counselor_id
    ):
        """Non-admin cannot view counselor details"""
        response = client.get(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {counselor_token}"},
        )

        assert response.status_code == 403


class TestAdminUpdateCounselor:
    """Test PATCH /api/v1/admin/counselors/{counselor_id} - Update counselor"""

    def test_update_counselor_full_name(self, client, admin_token, test_counselor_id):
        """Admin can update counselor's full_name"""
        request_data = {"full_name": "Updated Name"}

        response = client.patch(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    def test_update_counselor_phone(self, client, admin_token, test_counselor_id):
        """Admin can update counselor's phone"""
        request_data = {"phone": "+886987654321"}

        response = client.patch(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == "+886987654321"

    def test_update_counselor_role(self, client, admin_token, test_counselor_id):
        """Admin can update counselor's role"""
        request_data = {"role": "admin"}

        response = client.patch(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"

    def test_update_counselor_is_active(self, client, admin_token, test_counselor_id):
        """Admin can activate/deactivate counselor"""
        request_data = {"is_active": False}

        response = client.patch(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_update_counselor_subscription_expires_at(
        self, client, admin_token, test_counselor_id
    ):
        """Admin can update subscription expiry date"""
        from datetime import datetime, timedelta

        future_date = (datetime.utcnow() + timedelta(days=365)).isoformat()
        request_data = {"subscription_expires_at": future_date}

        response = client.patch(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["subscription_expires_at"] is not None

    def test_update_counselor_multiple_fields(
        self, client, admin_token, test_counselor_id
    ):
        """Admin can update multiple fields at once"""
        request_data = {
            "full_name": "New Name",
            "phone": "+886911111111",
            "is_active": True,
        }

        response = client.patch(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "New Name"
        assert data["phone"] == "+886911111111"
        assert data["is_active"] is True

    def test_update_counselor_cannot_change_email(
        self, client, admin_token, test_counselor_id
    ):
        """Admin cannot change email (unique identifier)"""
        request_data = {"email": "newemail@test.com"}

        # Email field is not in the update schema, so it should be ignored
        client.patch(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        # Verify email remains unchanged
        verify_response = client.get(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert verify_response.json()["email"] != "newemail@test.com"

    def test_update_counselor_cannot_change_tenant_id(
        self, client, admin_token, test_counselor_id
    ):
        """Admin cannot change tenant_id (multi-tenant isolation)"""
        request_data = {"tenant_id": "different_tenant"}

        # tenant_id field is not in the update schema, so it should be ignored
        client.patch(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        # Verify tenant_id remains unchanged
        verify_response = client.get(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert verify_response.json()["tenant_id"] != "different_tenant"

    def test_update_counselor_not_found(self, client, admin_token):
        """Updating non-existent counselor returns 404"""
        fake_id = str(uuid4())
        request_data = {"full_name": "Test"}

        response = client.patch(
            f"/api/v1/admin/counselors/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 404

    def test_update_counselor_unauthorized(
        self, client, counselor_token, test_counselor_id
    ):
        """Non-admin cannot update counselor"""
        request_data = {"full_name": "Hacked Name"}

        response = client.patch(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {counselor_token}"},
            json=request_data,
        )

        assert response.status_code == 403


class TestAdminDeleteCounselor:
    """Test DELETE /api/v1/admin/counselors/{counselor_id} - Soft delete counselor"""

    def test_delete_counselor_success(self, client, admin_token, db_session):
        """Admin can delete counselor (soft delete)"""
        from app.core.security import hash_password
        from app.models.counselor import Counselor, CounselorRole

        # Create a counselor to delete
        counselor = Counselor(
            email="todelete@test.com",
            username="todelete",
            full_name="To Delete",
            hashed_password=hash_password("test123"),
            tenant_id="career",
            role=CounselorRole.COUNSELOR,
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()
        counselor_id = counselor.id

        response = client.delete(
            f"/api/v1/admin/counselors/{counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()
        assert data["counselor_id"] == str(counselor_id)

    def test_delete_counselor_not_found(self, client, admin_token):
        """Deleting non-existent counselor returns 404"""
        fake_id = str(uuid4())

        response = client.delete(
            f"/api/v1/admin/counselors/{fake_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 404

    def test_delete_counselor_unauthorized(
        self, client, counselor_token, test_counselor_id
    ):
        """Non-admin cannot delete counselor"""
        response = client.delete(
            f"/api/v1/admin/counselors/{test_counselor_id}",
            headers={"Authorization": f"Bearer {counselor_token}"},
        )

        assert response.status_code == 403

    def test_deleted_counselor_cannot_login(self, client, admin_token, db_session):
        """Deleted counselor cannot login"""
        from app.core.security import hash_password
        from app.models.counselor import Counselor, CounselorRole

        # Create a counselor
        counselor = Counselor(
            email="willdelete@test.com",
            username="willdelete",
            full_name="Will Delete",
            hashed_password=hash_password("test123"),
            tenant_id="career",
            role=CounselorRole.COUNSELOR,
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()
        counselor_id = counselor.id

        # Delete the counselor
        client.delete(
            f"/api/v1/admin/counselors/{counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Try to login (should fail)
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "willdelete", "password": "test123"},
        )

        assert login_response.status_code in [401, 404]


class TestAdminCreateCounselor:
    """Test POST /api/v1/admin/counselors - Create new counselor (Optional feature)"""

    def test_create_counselor_success(self, client, admin_token):
        """Admin can create new counselor with password"""
        from datetime import datetime, timedelta

        request_data = {
            "email": "newuser@test.com",
            "username": "newuser",
            "full_name": "New User",
            "phone": "+886912345678",
            "password": "test_password_123",
            "tenant_id": "career",
            "role": "counselor",
            "total_credits": 500,
            "subscription_expires_at": (
                datetime.utcnow() + timedelta(days=365)
            ).isoformat(),
        }

        response = client.post(
            "/api/v1/admin/counselors",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "counselor" in data
        assert data["counselor"]["email"] == "newuser@test.com"
        assert data["counselor"]["username"] == "newuser"
        assert data["counselor"]["tenant_id"] == "career"
        assert data["counselor"]["total_credits"] == 500

    def test_create_counselor_duplicate_username(
        self, client, admin_token, test_counselors
    ):
        """Creating counselor with duplicate username fails"""
        request_data = {
            "email": "another@test.com",
            "username": "test_career",  # Already exists
            "full_name": "Another User",
            "password": "test_password_123",
            "tenant_id": "career",
            "role": "counselor",
        }

        response = client.post(
            "/api/v1/admin/counselors",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 400

    def test_create_counselor_duplicate_email_same_tenant(
        self, client, admin_token, test_counselors
    ):
        """Creating counselor with duplicate email in same tenant fails"""
        request_data = {
            "email": "test_career@test.com",  # Already exists in career tenant
            "username": "newusername",
            "full_name": "Another User",
            "password": "test_password_123",
            "tenant_id": "career",
            "role": "counselor",
        }

        response = client.post(
            "/api/v1/admin/counselors",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 400

    def test_create_counselor_other_tenant_forbidden(self, client, admin_token):
        """Admin cannot create counselors in other tenants without permission"""
        request_data = {
            "email": "shared@test.com",
            "username": "user_island",
            "full_name": "User Island",
            "password": "test_password_123",
            "tenant_id": "island",
            "role": "counselor",
        }

        response = client.post(
            "/api/v1/admin/counselors",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )
        assert response.status_code == 403

    def test_create_counselor_unauthorized(self, client, counselor_token):
        """Non-admin cannot create counselor"""
        request_data = {
            "email": "hacker@test.com",
            "username": "hacker",
            "full_name": "Hacker",
            "tenant_id": "career",
            "role": "counselor",
        }

        response = client.post(
            "/api/v1/admin/counselors",
            headers={"Authorization": f"Bearer {counselor_token}"},
            json=request_data,
        )

        assert response.status_code == 403


# ============================================================================
# Fixtures (reuse from test_admin_credits_api.py)
# ============================================================================


@pytest.fixture
def admin_token(client, db_session):
    """Create admin user and return auth token"""
    from app.core.security import hash_password
    from app.models.counselor import Counselor, CounselorRole

    admin = Counselor(
        email="admin@test.com",
        username="admin",
        full_name="Admin User",
        hashed_password=hash_password("admin123"),
        tenant_id="career",
        role=CounselorRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Login to get token
    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@test.com",
            "password": "admin123",
            "tenant_id": "career",
        },
    )
    return response.json()["access_token"]


@pytest.fixture
def counselor_token(client, db_session):
    """Create regular counselor and return auth token"""
    from app.core.security import hash_password
    from app.models.counselor import Counselor, CounselorRole

    counselor = Counselor(
        email="counselor@test.com",
        username="counselor",
        full_name="Regular Counselor",
        hashed_password=hash_password("counselor123"),
        tenant_id="career",
        role=CounselorRole.COUNSELOR,
        is_active=True,
    )
    db_session.add(counselor)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "email": "counselor@test.com",
            "password": "counselor123",
            "tenant_id": "career",
        },
    )
    return response.json()["access_token"]


@pytest.fixture
def test_counselors(db_session):
    """Create test counselors for all three tenants"""
    from app.core.security import hash_password
    from app.models.counselor import Counselor, CounselorRole

    counselors = []
    for tenant_id in ["career", "island", "island_parents"]:
        counselor = Counselor(
            email=f"test_{tenant_id}@test.com",
            username=f"test_{tenant_id}",
            full_name=f"Test {tenant_id.title()}",
            hashed_password=hash_password("test123"),
            tenant_id=tenant_id,
            role=CounselorRole.COUNSELOR,
            is_active=True,
            total_credits=0,
            credits_used=0,
        )
        db_session.add(counselor)
        counselors.append(counselor)

    db_session.commit()
    return counselors


@pytest.fixture
def test_counselor_id(test_counselors):
    """Return ID of first test counselor"""
    return test_counselors[0].id
