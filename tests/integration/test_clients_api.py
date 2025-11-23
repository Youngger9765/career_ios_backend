"""
Integration tests for Clients API
TDD - Write tests first, then implement
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.client import Client
from app.models.counselor import Counselor


class TestClientsAPI:
    """Test Clients CRUD endpoints"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        # Create test counselor
        counselor = Counselor(
            id=uuid4(),
            email="counselor@test.com",
            username="testcounselor",
            full_name="Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        # Login to get token
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "counselor@test.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    def test_create_client_success(self, db_session: Session, auth_headers):
        """Test POST /api/v1/clients - Create new client"""

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clients",
                headers=auth_headers,
                json={
                    "name": "張小明",
                    "email": "zhang@example.com",
                    "gender": "男",
                    "birth_date": "1990-01-15",
                    "phone": "0912345678",
                    "identity_option": "在職者",
                    "current_status": "探索中",
                    "occupation": "工程師",
                    "education": "大學",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "張小明"
            assert data["email"] == "zhang@example.com"
            assert data["gender"] == "男"
            assert data["phone"] == "0912345678"
            assert "id" in data
            assert "code" in data  # Auto-generated client code
            assert data["tenant_id"] == "career"

    def test_create_client_minimal_fields(self, db_session: Session, auth_headers):
        """Test creating client with only required fields"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clients",
                headers=auth_headers,
                json={
                    "name": "李小華",
                    "email": "lee@example.com",
                    "gender": "女",
                    "birth_date": "1995-06-20",
                    "phone": "0923456789",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "李小華"
            assert data["email"] == "lee@example.com"
            assert "id" in data
            assert "code" in data

    def test_create_client_unauthorized(self):
        """Test creating client without auth returns 403"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clients",
                json={"name": "Unauthorized Client"},
            )

            assert response.status_code == 403

    def test_list_clients_success(self, db_session: Session, auth_headers):
        """Test GET /api/v1/clients - List all clients"""
        from datetime import date

        # Create test clients
        counselor = (
            db_session.query(Counselor).filter_by(email="counselor@test.com").first()
        )

        client1 = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="客戶A",
            code="CLI001",
            email="clienta@example.com",
            gender="不透露",
            birth_date=date(1990, 1, 1),
            phone="0911111111",
            identity_option="其他",
            current_status="探索中",
        )
        client2 = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="客戶B",
            code="CLI002",
            email="clientb@example.com",
            gender="不透露",
            birth_date=date(1992, 2, 2),
            phone="0922222222",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add_all([client1, client2])
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/clients",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "total" in data
            assert "items" in data
            assert data["total"] >= 2
            assert len(data["items"]) >= 2

    def test_list_clients_with_search(self, db_session: Session, auth_headers):
        """Test GET /api/v1/clients?search=keyword - Search clients"""
        from datetime import date

        counselor = (
            db_session.query(Counselor).filter_by(email="counselor@test.com").first()
        )

        client1 = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="張小明",
            code="CLI003",
            email="zhang@example.com",
            gender="男",
            birth_date=date(1988, 5, 10),
            phone="0933333333",
            identity_option="在職者",
            current_status="探索中",
        )
        client2 = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="李小華",
            code="CLI004",
            email="li@example.com",
            gender="女",
            birth_date=date(1995, 8, 20),
            phone="0944444444",
            identity_option="學生",
            current_status="探索中",
        )
        db_session.add_all([client1, client2])
        db_session.commit()

        with TestClient(app) as client:
            # Search by name
            response = client.get(
                "/api/v1/clients?search=張小明",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] >= 1
            # Verify search result contains the searched name
            names = [item["name"] for item in data["items"]]
            assert "張小明" in names

    def test_get_client_success(self, db_session: Session, auth_headers):
        """Test GET /api/v1/clients/{id} - Get client details"""
        from datetime import date

        counselor = (
            db_session.query(Counselor).filter_by(email="counselor@test.com").first()
        )

        test_client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="測試客戶",
            code="CLI005",
            email="test005@example.com",
            gender="女",
            birth_date=date(1995, 3, 15),
            phone="0955555555",
            identity_option="社會新鮮人",
            current_status="探索中",
        )
        db_session.add(test_client)
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/clients/{test_client.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(test_client.id)
            assert data["name"] == "測試客戶"
            assert data["code"] == "CLI005"
            assert data["gender"] == "女"
            assert data["email"] == "test005@example.com"

    def test_get_client_not_found(self, db_session: Session, auth_headers):
        """Test getting non-existent client returns 404"""
        fake_id = uuid4()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/clients/{fake_id}",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_update_client_success(self, db_session: Session, auth_headers):
        """Test PATCH /api/v1/clients/{id} - Update client"""
        from datetime import date

        counselor = (
            db_session.query(Counselor).filter_by(email="counselor@test.com").first()
        )

        test_client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="原始姓名",
            code="CLI006",
            email="test006@example.com",
            gender="不透露",
            birth_date=date(1990, 1, 1),
            phone="0966666666",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(test_client)
        db_session.commit()

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/clients/{test_client.id}",
                headers=auth_headers,
                json={
                    "name": "更新後姓名",
                    "phone": "0987654321",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "更新後姓名"
            assert data["phone"] == "0987654321"

    def test_delete_client_success(self, db_session: Session, auth_headers):
        """Test DELETE /api/v1/clients/{id} - Soft delete client"""
        from datetime import date

        counselor = (
            db_session.query(Counselor).filter_by(email="counselor@test.com").first()
        )

        test_client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="待刪除客戶",
            code="CLI007",
            email="test007@example.com",
            gender="不透露",
            birth_date=date(1990, 1, 1),
            phone="0977777777",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(test_client)
        db_session.commit()

        with TestClient(app) as client:
            # Delete client
            response = client.delete(
                f"/api/v1/clients/{test_client.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data

            # Verify client no longer appears in list
            list_response = client.get(
                "/api/v1/clients",
                headers=auth_headers,
            )
            list_data = list_response.json()
            client_ids = [item["id"] for item in list_data["items"]]
            assert str(test_client.id) not in client_ids

    def test_delete_client_not_found(self, db_session: Session, auth_headers):
        """Test deleting non-existent client returns 404"""
        fake_id = uuid4()

        with TestClient(app) as client:
            response = client.delete(
                f"/api/v1/clients/{fake_id}",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_pagination(self, db_session: Session, auth_headers):
        """Test pagination parameters (skip, limit)"""
        from datetime import date

        counselor = (
            db_session.query(Counselor).filter_by(email="counselor@test.com").first()
        )

        # Create multiple clients
        for i in range(5):
            client_obj = Client(
                id=uuid4(),
                counselor_id=counselor.id,
                tenant_id="career",
                name=f"客戶{i}",
                code=f"CLIP{i:03d}",
                email=f"client{i}@example.com",
                gender="不透露",
                birth_date=date(1990, 1, 1),
                phone=f"098888888{i}",
                identity_option="其他",
                current_status="探索中",
            )
            db_session.add(client_obj)
        db_session.commit()

        with TestClient(app) as client:
            # Test limit
            response = client.get(
                "/api/v1/clients?limit=3",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 3

            # Test skip
            response = client.get(
                "/api/v1/clients?skip=2&limit=2",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 2
