"""
Integration tests for Cases API
TDD - Write tests first, then implement
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor


class TestCasesAPI:
    """Test Cases CRUD endpoints"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-cases@test.com",
            username="casescounselor",
            full_name="Cases Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "counselor-cases@test.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_client_obj(self, db_session: Session):
        """Create a test client for case tests"""
        from datetime import date

        counselor = (
            db_session.query(Counselor)
            .filter_by(email="counselor-cases@test.com")
            .first()
        )

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="測試客戶",
            code="TCLI001",
            email="testclient001@example.com",
            gender="不透露",
            birth_date=date(1995, 1, 1),
            phone="0912345678",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(client)
        db_session.commit()
        return client

    def test_create_case_success(
        self, db_session: Session, auth_headers, test_client_obj
    ):
        """Test POST /api/v1/cases - Create new case"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/cases",
                headers=auth_headers,
                json={
                    "client_id": str(test_client_obj.id),
                    "summary": "職涯諮商個案",
                    "goals": "協助個案探索職涯方向",
                    "problem_description": "對未來職涯感到迷惘",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["client_id"] == str(test_client_obj.id)
            assert data["summary"] == "職涯諮商個案"
            assert data["status"] == 0  # NOT_STARTED
            assert "case_number" in data
            assert "id" in data

    def test_create_case_minimal_fields(
        self, db_session: Session, auth_headers, test_client_obj
    ):
        """Test creating case with only required fields"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/cases",
                headers=auth_headers,
                json={
                    "client_id": str(test_client_obj.id),
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["client_id"] == str(test_client_obj.id)
            assert data["status"] == 0  # NOT_STARTED

    def test_create_case_unauthorized(self, auth_headers, test_client_obj):
        """Test creating case without auth returns 403"""
        # auth_headers dependency ensures counselor exists for test_client_obj
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/cases",
                json={"client_id": str(test_client_obj.id)},
            )

            assert response.status_code == 403

    def test_create_case_invalid_client(self, db_session: Session, auth_headers):
        """Test creating case with non-existent client returns 404"""
        fake_client_id = uuid4()

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/cases",
                headers=auth_headers,
                json={"client_id": str(fake_client_id)},
            )

            assert response.status_code == 404

    def test_list_cases_success(
        self, db_session: Session, auth_headers, test_client_obj
    ):
        """Test GET /api/v1/cases - List all cases"""
        counselor = (
            db_session.query(Counselor)
            .filter_by(email="counselor-cases@test.com")
            .first()
        )

        case1 = Case(
            id=uuid4(),
            case_number="CASE001",
            counselor_id=counselor.id,
            client_id=test_client_obj.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        case2 = Case(
            id=uuid4(),
            case_number="CASE002",
            counselor_id=counselor.id,
            client_id=test_client_obj.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add_all([case1, case2])
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/cases",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "total" in data
            assert "items" in data
            assert data["total"] >= 2

    def test_list_cases_filter_by_client(
        self, db_session: Session, auth_headers, test_client_obj
    ):
        """Test GET /api/v1/cases?client_id=xxx - Filter by client"""
        counselor = (
            db_session.query(Counselor)
            .filter_by(email="counselor-cases@test.com")
            .first()
        )

        # Create another client
        from datetime import date

        other_client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="另一個客戶",
            code="TCLI002",
            email="testclient002@example.com",
            gender="不透露",
            birth_date=date(1990, 1, 1),
            phone="0922334455",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(other_client)
        db_session.commit()

        # Create cases for both clients
        case1 = Case(
            id=uuid4(),
            case_number="CASE003",
            counselor_id=counselor.id,
            client_id=test_client_obj.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        case2 = Case(
            id=uuid4(),
            case_number="CASE004",
            counselor_id=counselor.id,
            client_id=other_client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add_all([case1, case2])
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/cases?client_id={test_client_obj.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            # All cases should belong to test_client_obj
            for item in data["items"]:
                assert item["client_id"] == str(test_client_obj.id)

    def test_get_case_success(self, db_session: Session, auth_headers, test_client_obj):
        """Test GET /api/v1/cases/{id} - Get case details"""
        counselor = (
            db_session.query(Counselor)
            .filter_by(email="counselor-cases@test.com")
            .first()
        )

        test_case = Case(
            id=uuid4(),
            case_number="CASE005",
            counselor_id=counselor.id,
            client_id=test_client_obj.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
            summary="測試個案摘要",
        )
        db_session.add(test_case)
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/cases/{test_case.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(test_case.id)
            assert data["case_number"] == "CASE005"
            assert data["summary"] == "測試個案摘要"

    def test_get_case_not_found(self, db_session: Session, auth_headers):
        """Test getting non-existent case returns 404"""
        fake_id = uuid4()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/cases/{fake_id}",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_update_case_success(
        self, db_session: Session, auth_headers, test_client_obj
    ):
        """Test PATCH /api/v1/cases/{id} - Update case"""
        counselor = (
            db_session.query(Counselor)
            .filter_by(email="counselor-cases@test.com")
            .first()
        )

        test_case = Case(
            id=uuid4(),
            case_number="CASE006",
            counselor_id=counselor.id,
            client_id=test_client_obj.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(test_case)
        db_session.commit()

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/cases/{test_case.id}",
                headers=auth_headers,
                json={
                    "summary": "更新後的摘要",
                    "goals": "新的諮商目標",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["summary"] == "更新後的摘要"
            assert data["goals"] == "新的諮商目標"

    def test_update_case_status(
        self, db_session: Session, auth_headers, test_client_obj
    ):
        """Test updating case status"""
        counselor = (
            db_session.query(Counselor)
            .filter_by(email="counselor-cases@test.com")
            .first()
        )

        test_case = Case(
            id=uuid4(),
            case_number="CASE007",
            counselor_id=counselor.id,
            client_id=test_client_obj.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(test_case)
        db_session.commit()

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/cases/{test_case.id}",
                headers=auth_headers,
                json={"status": 2},  # COMPLETED
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == 2  # COMPLETED

    def test_delete_case_success(
        self, db_session: Session, auth_headers, test_client_obj
    ):
        """Test DELETE /api/v1/cases/{id} - Soft delete case"""
        counselor = (
            db_session.query(Counselor)
            .filter_by(email="counselor-cases@test.com")
            .first()
        )

        test_case = Case(
            id=uuid4(),
            case_number="CASE008",
            counselor_id=counselor.id,
            client_id=test_client_obj.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(test_case)
        db_session.commit()

        with TestClient(app) as client:
            # Delete case
            response = client.delete(
                f"/api/v1/cases/{test_case.id}",
                headers=auth_headers,
            )

            assert response.status_code == 204

            # Verify case no longer appears in list
            list_response = client.get(
                "/api/v1/cases",
                headers=auth_headers,
            )
            list_data = list_response.json()
            case_ids = [item["id"] for item in list_data["items"]]
            assert str(test_case.id) not in case_ids

    def test_delete_case_not_found(self, db_session: Session, auth_headers):
        """Test deleting non-existent case returns 404"""
        fake_id = uuid4()

        with TestClient(app) as client:
            response = client.delete(
                f"/api/v1/cases/{fake_id}",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_pagination(self, db_session: Session, auth_headers, test_client_obj):
        """Test pagination parameters (skip, limit)"""
        counselor = (
            db_session.query(Counselor)
            .filter_by(email="counselor-cases@test.com")
            .first()
        )

        # Create multiple cases
        for i in range(5):
            case_obj = Case(
                id=uuid4(),
                case_number=f"CASEP{i:03d}",
                counselor_id=counselor.id,
                client_id=test_client_obj.id,
                tenant_id="career",
                status=CaseStatus.NOT_STARTED,
            )
            db_session.add(case_obj)
        db_session.commit()

        with TestClient(app) as client:
            # Test limit
            response = client.get(
                "/api/v1/cases?limit=3",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 3

            # Test skip
            response = client.get(
                "/api/v1/cases?skip=2&limit=2",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 2
