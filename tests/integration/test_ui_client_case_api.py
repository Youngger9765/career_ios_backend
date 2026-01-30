"""
Integration tests for UI Client-Case CRUD APIs
TDD - Write tests first, then implement
"""
from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor


class TestUIClientCaseAPI:
    """Test UI Client-Case CRUD endpoints"""

    @pytest.fixture
    def test_client(self, db_session: Session):
        """Create TestClient that uses the test database session"""
        # The db_session fixture already overrides get_db dependency
        # So any TestClient created here will use the test database
        return TestClient(app)

    @pytest.fixture
    def counselor(self, db_session: Session):
        """Create and return authenticated counselor"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-ui@test.com",
            username="uicounselor",
            full_name="UI Test Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()
        db_session.refresh(counselor)
        return counselor

    @pytest.fixture
    def auth_headers(self, test_client: TestClient, counselor: Counselor):
        """Return auth headers with JWT token"""
        login_response = test_client.post(
            "/api/auth/login",
            json={
                "email": counselor.email,
                "password": "ValidP@ssw0rd123",
                "tenant_id": counselor.tenant_id,
            },
        )
        print(f"\n[DEBUG] Login status: {login_response.status_code}")
        print(f"[DEBUG] Login response: {login_response.text}")
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    # ==================== UI-3: List Client-Cases ====================
    def test_list_client_cases_success(
        self,
        test_client: TestClient,
        db_session: Session,
        counselor: Counselor,
        auth_headers,
    ):
        """Test GET /api/v1/ui/client-case-list - List all client-cases"""
        # Create test client and case
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="UI測試客戶",
            code="UIC001",
            email="ui-test@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0912345678",
            identity_option="轉職者",
            current_status="求職中",
        )
        db_session.add(client)
        db_session.commit()

        case = Case(
            id=uuid4(),
            case_number="UICASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(case)
        db_session.commit()

        response = test_client.get(
            "/api/v1/ui/client-case-list?skip=0&limit=20",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

        # Verify item structure
        item = data["items"][0]
        assert "client_id" in item
        assert "case_id" in item
        assert "client_name" in item
        assert "client_code" in item
        assert "client_email" in item
        assert "case_number" in item
        assert "case_status" in item
        assert "case_status_label" in item
        assert "total_sessions" in item

    def test_list_client_cases_unauthorized(self, test_client: TestClient):
        """Test listing client-cases without auth returns 403"""
        response = test_client.get("/api/v1/ui/client-case-list")
        assert response.status_code == 403

    def test_list_client_cases_pagination(
        self,
        test_client: TestClient,
        db_session: Session,
        counselor: Counselor,
        auth_headers,
    ):
        """Test pagination parameters"""

        # Create multiple client-cases
        for i in range(5):
            client = Client(
                id=uuid4(),
                counselor_id=counselor.id,
                tenant_id="career",
                name=f"客戶{i}",
                code=f"UIC{i:03d}",
                email=f"client{i}@example.com",
                gender="男",
                birth_date=date(1990, 1, 1),
                phone=f"091234567{i}",
                identity_option="在職者",
                current_status="穩定就業",
            )
            db_session.add(client)
            db_session.flush()

            case = Case(
                id=uuid4(),
                case_number=f"UICASE{i:03d}",
                counselor_id=counselor.id,
                client_id=client.id,
                tenant_id="career",
                status=CaseStatus.NOT_STARTED,
            )
            db_session.add(case)

        db_session.commit()

        # Test limit
        response = test_client.get(
            "/api/v1/ui/client-case-list?skip=0&limit=3",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 3

    # ==================== UI-4: Create Client-Case ====================
    def test_create_client_case_success(
        self, test_client: TestClient, counselor: Counselor, auth_headers
    ):
        """Test POST /api/v1/ui/client-case - Create client and case together"""
        response = test_client.post(
            "/api/v1/ui/client-case",
            headers=auth_headers,
            json={
                "name": "新客戶",
                "email": "new-client@example.com",
                "gender": "女",
                "birth_date": "1995-05-15",
                "phone": "0987654321",
                "identity_option": "學生",
                "current_status": "在學中",
                "nickname": "小新",
                "education": "研究所",
                "occupation": "學生",
                "location": "台北市",
                "case_summary": "生涯探索諮詢",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["client_name"] == "新客戶"
        assert data["client_email"] == "new-client@example.com"
        assert "client_id" in data
        assert "client_code" in data  # Auto-generated
        assert "case_id" in data
        assert "case_number" in data  # Auto-generated
        assert data["case_status"] == 0  # NOT_STARTED
        assert data["message"] == "客戶與個案建立成功"

    def test_create_client_case_minimal_fields(
        self, test_client: TestClient, counselor: Counselor, auth_headers
    ):
        """Test creating client-case with only required fields"""
        response = test_client.post(
            "/api/v1/ui/client-case",
            headers=auth_headers,
            json={
                "name": "最小欄位客戶",
                "email": "minimal@example.com",
                "gender": "男",
                "birth_date": "1992-01-01",
                "phone": "0911111111",
                "identity_option": "其他",
                "current_status": "待業中",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["client_name"] == "最小欄位客戶"

    def test_create_client_case_duplicate_email(
        self,
        test_client: TestClient,
        db_session: Session,
        counselor: Counselor,
        auth_headers,
    ):
        """Test creating client-case with duplicate email returns 400"""

        # Create existing client
        existing_client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="既有客戶",
            code="EXIST001",
            email="duplicate@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0900000000",
            identity_option="在職者",
            current_status="工作中",
        )
        db_session.add(existing_client)
        db_session.commit()

        response = test_client.post(
            "/api/v1/ui/client-case",
            headers=auth_headers,
            json={
                "name": "重複客戶",
                "email": "duplicate@example.com",  # Duplicate
                "gender": "女",
                "birth_date": "1995-01-01",
                "phone": "0911111111",
                "identity_option": "轉職者",
                "current_status": "求職中",
            },
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_client_case_unauthorized(self, test_client: TestClient):
        """Test creating client-case without auth returns 403"""
        response = test_client.post(
            "/api/v1/ui/client-case",
            json={"name": "Unauthorized Client"},
        )
        assert response.status_code == 403

    # ==================== UI-4: Get Client-Case Detail ====================
    def test_get_client_case_detail_success(
        self,
        test_client: TestClient,
        db_session: Session,
        counselor: Counselor,
        auth_headers,
    ):
        """Test GET /api/v1/ui/client-case/{id} - Get single client-case detail"""

        # Create test client and case
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="詳情測試客戶",
            code="DETAIL001",
            email="detail@example.com",
            gender="女",
            birth_date=date(1992, 6, 15),
            phone="0955555555",
            identity_option="轉職者",
            current_status="面試準備中",
            nickname="小明",
            education="大學",
            occupation="工程師",
            location="台北市",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            case_number="DETAILCASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.IN_PROGRESS,
            summary="職涯轉換諮詢",
            goals="成功轉職到科技業",
            problem_description="對目前工作不滿意，想轉換跑道",
        )
        db_session.add(case)
        db_session.commit()

        response = test_client.get(
            f"/api/v1/ui/client-case/{case.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify client fields
        assert data["client_id"] == str(client.id)
        assert data["client_name"] == "詳情測試客戶"
        assert data["client_code"] == "DETAIL001"
        assert data["client_email"] == "detail@example.com"
        assert data["gender"] == "女"
        assert data["birth_date"] == "1992-06-15"
        assert data["phone"] == "0955555555"
        assert data["identity_option"] == "轉職者"
        assert data["current_status"] == "面試準備中"
        assert data["nickname"] == "小明"
        assert data["education"] == "大學"
        assert data["occupation"] == "工程師"
        assert data["location"] == "台北市"

        # Verify case fields
        assert data["case_id"] == str(case.id)
        assert data["case_number"] == "DETAILCASE001"
        assert data["case_status"] == 1  # IN_PROGRESS
        assert data["case_status_label"] == "進行中"
        assert data["case_summary"] == "職涯轉換諮詢"
        assert data["case_goals"] == "成功轉職到科技業"
        assert data["problem_description"] == "對目前工作不滿意，想轉換跑道"

    def test_get_client_case_detail_not_found(
        self, test_client: TestClient, counselor: Counselor, auth_headers
    ):
        """Test getting non-existent case returns 404"""
        fake_id = uuid4()

        response = test_client.get(
            f"/api/v1/ui/client-case/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_client_case_detail_unauthorized(self, test_client: TestClient):
        """Test getting detail without auth returns 403"""
        fake_id = uuid4()

        response = test_client.get(f"/api/v1/ui/client-case/{fake_id}")

        assert response.status_code == 403

    # ==================== UI-5: Update Client-Case ====================
    def test_update_client_case_success(
        self,
        test_client: TestClient,
        db_session: Session,
        counselor: Counselor,
        auth_headers,
    ):
        """Test PATCH /api/v1/ui/client-case/{id} - Update client and case"""

        # Create test client and case
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="原始姓名",
            code="UPD001",
            email="update-test@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0900000000",
            identity_option="在職者",
            current_status="穩定就業",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            case_number="UPDCASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
            summary="原始摘要",
        )
        db_session.add(case)
        db_session.commit()

        with TestClient(app) as test_client:
            response = test_client.patch(
                f"/api/v1/ui/client-case/{case.id}",
                headers=auth_headers,
                json={
                    "name": "更新後姓名",
                    "phone": "0987654321",
                    "current_status": "已轉職",
                    "case_status": "2",  # COMPLETED (sent as string but will be parsed)
                    "case_summary": "成功協助轉職",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["client_name"] == "更新後姓名"
        assert data["case_status"] == 2  # COMPLETED
        assert data["message"] == "客戶與個案更新成功"

    def test_update_client_case_partial_fields(
        self,
        test_client: TestClient,
        db_session: Session,
        counselor: Counselor,
        auth_headers,
    ):
        """Test updating only some fields"""

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="部分更新客戶",
            code="PART001",
            email="partial@example.com",
            gender="女",
            birth_date=date(1995, 1, 1),
            phone="0911111111",
            identity_option="學生",
            current_status="在學中",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            case_number="PARTCASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(case)
        db_session.commit()

        # Only update case_status
        response = test_client.patch(
            f"/api/v1/ui/client-case/{case.id}",
            headers=auth_headers,
            json={
                "case_status": "1"
            },  # IN_PROGRESS (sent as string but will be parsed)
        )

        assert response.status_code == 200
        data = response.json()
        assert data["case_status"] == 1  # IN_PROGRESS
        assert data["client_name"] == "部分更新客戶"  # Unchanged

    def test_update_client_case_not_found(
        self, test_client: TestClient, counselor: Counselor, auth_headers
    ):
        """Test updating non-existent case returns 404"""
        fake_id = uuid4()

        response = test_client.patch(
            f"/api/v1/ui/client-case/{fake_id}",
            headers=auth_headers,
            json={"name": "Should Fail"},
        )

        assert response.status_code == 404

    def test_update_client_case_invalid_status(
        self,
        test_client: TestClient,
        db_session: Session,
        counselor: Counselor,
        auth_headers,
    ):
        """Test updating with invalid case_status returns 400"""

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="Invalid Status Test",
            code="INV001",
            email="invalid@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0900000000",
            identity_option="在職者",
            current_status="工作中",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            case_number="INVCASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(case)
        db_session.commit()

        response = test_client.patch(
            f"/api/v1/ui/client-case/{case.id}",
            headers=auth_headers,
            json={"case_status": "invalid_status"},
        )

        assert response.status_code == 400
        assert "Invalid case_status" in response.json()["detail"]

    # ==================== UI-6: Delete Client-Case ====================
    def test_delete_client_case_success(
        self,
        test_client: TestClient,
        db_session: Session,
        counselor: Counselor,
        auth_headers,
    ):
        """Test DELETE /api/v1/ui/client-case/{id} - Soft delete case"""

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="待刪除客戶",
            code="DEL001",
            email="delete@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0900000000",
            identity_option="在職者",
            current_status="工作中",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            case_number="DELCASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(case)
        db_session.commit()

        case_id = case.id

        response = test_client.delete(
            f"/api/v1/ui/client-case/{case_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Case deleted successfully"
        assert data["case_number"] == "DELCASE001"
        assert "deleted_at" in data

        # Verify case is soft-deleted (has deleted_at timestamp)
        deleted_case = db_session.query(Case).filter_by(id=case_id).first()
        assert deleted_case.deleted_at is not None

        # Verify client is NOT deleted
        client_still_exists = db_session.query(Client).filter_by(id=client.id).first()
        assert client_still_exists is not None
        assert client_still_exists.deleted_at is None

    def test_delete_client_case_not_found(
        self, test_client: TestClient, counselor: Counselor, auth_headers
    ):
        """Test deleting non-existent case returns 404"""
        fake_id = uuid4()

        response = test_client.delete(
            f"/api/v1/ui/client-case/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_delete_client_case_unauthorized(
        self,
        test_client: TestClient,
        db_session: Session,
        counselor: Counselor,
        auth_headers,
    ):
        """Test deleting another counselor's case returns 403"""
        # Create another counselor
        other_counselor = Counselor(
            id=uuid4(),
            email="other-counselor@test.com",
            username="othercounselor",
            full_name="Other Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(other_counselor)
        db_session.commit()

        # Create client and case owned by other counselor
        client = Client(
            id=uuid4(),
            counselor_id=other_counselor.id,
            tenant_id="career",
            name="Other's Client",
            code="OTHER001",
            email="other@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0900000000",
            identity_option="在職者",
            current_status="工作中",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            case_number="OTHERCASE001",
            counselor_id=other_counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(case)
        db_session.commit()

        # Try to delete with original auth headers (different counselor)
        response = test_client.delete(
            f"/api/v1/ui/client-case/{case.id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "only delete your own cases" in response.json()["detail"]

    def test_delete_client_case_admin_can_delete_any(
        self, test_client: TestClient, db_session: Session
    ):
        """Test admin can delete any case in their tenant"""
        # Create admin user
        admin = Counselor(
            id=uuid4(),
            email="admin@test.com",
            username="admin",
            full_name="Admin User",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="admin",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()

        # Create another counselor
        other_counselor = Counselor(
            id=uuid4(),
            email="other-counselor2@test.com",
            username="othercounselor2",
            full_name="Other Counselor 2",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(other_counselor)
        db_session.commit()

        # Create client and case owned by other counselor
        client = Client(
            id=uuid4(),
            counselor_id=other_counselor.id,
            tenant_id="career",
            name="Other's Client",
            code="ADMINTEST001",
            email="admintest@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0933333333",
            identity_option="在職者",
            current_status="工作中",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            case_number="ADMINCASE001",
            counselor_id=other_counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(case)
        db_session.commit()

        # Login as admin
        login_response = test_client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "ValidP@ssw0rd123",
                "tenant_id": "career",
            },
        )
        admin_token = login_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Admin should be able to delete other counselor's case
        response = test_client.delete(
            f"/api/v1/ui/client-case/{case.id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Case deleted successfully"
        assert data["case_number"] == "ADMINCASE001"

        # Verify case is soft-deleted
        deleted_case = db_session.query(Case).filter_by(id=case.id).first()
        assert deleted_case.deleted_at is not None

    # ==================== Multi-Tenant Isolation Test ====================
    def test_multi_tenant_isolation(
        self,
        test_client: TestClient,
        db_session: Session,
    ):
        """Test that users from different tenants cannot see each other's data"""
        # Create counselor for tenant "career"
        career_counselor = Counselor(
            id=uuid4(),
            email="career@test.com",
            username="careercounselor",
            full_name="Career Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(career_counselor)
        db_session.flush()

        # Create counselor for tenant "island"
        island_counselor = Counselor(
            id=uuid4(),
            email="island@test.com",
            username="islandcounselor",
            full_name="Island Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="island",
            role="counselor",
            is_active=True,
        )
        db_session.add(island_counselor)
        db_session.flush()

        # Create client and case for "career" tenant
        career_client = Client(
            id=uuid4(),
            counselor_id=career_counselor.id,
            tenant_id="career",
            name="Career Client",
            code="CAREER001",
            email="career-client@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0911111111",
            identity_option="在職者",
            current_status="工作中",
        )
        db_session.add(career_client)
        db_session.flush()

        career_case = Case(
            id=uuid4(),
            case_number="CAREERCASE001",
            counselor_id=career_counselor.id,
            client_id=career_client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(career_case)
        db_session.flush()

        # Create client and case for "island" tenant
        island_client = Client(
            id=uuid4(),
            counselor_id=island_counselor.id,
            tenant_id="island",
            name="Island Client",
            code="ISLAND001",
            email="island-client@example.com",
            gender="女",
            birth_date=date(1992, 1, 1),
            phone="0922222222",
            identity_option="學生",
            current_status="在學中",
        )
        db_session.add(island_client)
        db_session.flush()

        island_case = Case(
            id=uuid4(),
            case_number="ISLANDCASE001",
            counselor_id=island_counselor.id,
            client_id=island_client.id,
            tenant_id="island",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(island_case)
        db_session.commit()

        # Login as career counselor
        career_login = test_client.post(
            "/api/auth/login",
            json={
                "email": "career@test.com",
                "password": "ValidP@ssw0rd123",
                "tenant_id": "career",
            },
        )
        assert career_login.status_code == 200
        career_token = career_login.json()["access_token"]
        career_headers = {"Authorization": f"Bearer {career_token}"}

        # Login as island counselor
        island_login = test_client.post(
            "/api/auth/login",
            json={
                "email": "island@test.com",
                "password": "ValidP@ssw0rd123",
                "tenant_id": "island",
            },
        )
        assert island_login.status_code == 200
        island_token = island_login.json()["access_token"]
        island_headers = {"Authorization": f"Bearer {island_token}"}

        # Career counselor should only see career data
        career_response = test_client.get(
            "/api/v1/ui/client-case-list",
            headers=career_headers,
        )
        assert career_response.status_code == 200
        career_data = career_response.json()
        assert career_data["total"] == 1
        assert len(career_data["items"]) == 1
        assert career_data["items"][0]["client_name"] == "Career Client"
        assert career_data["items"][0]["case_number"] == "CAREERCASE001"

        # Island counselor should only see island data
        island_response = test_client.get(
            "/api/v1/ui/client-case-list",
            headers=island_headers,
        )
        assert island_response.status_code == 200
        island_data = island_response.json()
        assert island_data["total"] == 1
        assert len(island_data["items"]) == 1
        assert island_data["items"][0]["client_name"] == "Island Client"
        assert island_data["items"][0]["case_number"] == "ISLANDCASE001"

        # Verify cross-tenant access is blocked
        # Career counselor should NOT be able to access island case
        career_detail_response = test_client.get(
            f"/api/v1/ui/client-case/{island_case.id}",
            headers=career_headers,
        )
        assert career_detail_response.status_code == 404  # Not found (tenant isolation)

        # Island counselor should NOT be able to access career case
        island_detail_response = test_client.get(
            f"/api/v1/ui/client-case/{career_case.id}",
            headers=island_headers,
        )
        assert island_detail_response.status_code == 404  # Not found (tenant isolation)

    def test_multi_tenant_isolation_sessions(
        self,
        test_client: TestClient,
        db_session: Session,
    ):
        """Test that sessions are properly isolated by tenant"""
        from datetime import datetime, timezone

        # Create counselors for different tenants
        career_counselor = Counselor(
            id=uuid4(),
            email="career-sessions@test.com",
            username="careersessions",
            full_name="Career Sessions Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        island_counselor = Counselor(
            id=uuid4(),
            email="island-sessions@test.com",
            username="islandsessions",
            full_name="Island Sessions Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="island",
            role="counselor",
            is_active=True,
        )
        db_session.add_all([career_counselor, island_counselor])
        db_session.flush()

        # Create clients and cases
        career_client = Client(
            id=uuid4(),
            counselor_id=career_counselor.id,
            tenant_id="career",
            name="Career Sessions Client",
            code="CSESS001",
            email="career-sessions@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0911111111",
            identity_option="在職者",
            current_status="工作中",
        )
        career_case = Case(
            id=uuid4(),
            case_number="CSESSCASE001",
            counselor_id=career_counselor.id,
            client_id=career_client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add_all([career_client, career_case])
        db_session.flush()

        island_client = Client(
            id=uuid4(),
            counselor_id=island_counselor.id,
            tenant_id="island",
            name="Island Sessions Client",
            code="ISESS001",
            email="island-sessions@example.com",
            gender="女",
            birth_date=date(1992, 1, 1),
            phone="0922222222",
            identity_option="學生",
            current_status="在學中",
        )
        island_case = Case(
            id=uuid4(),
            case_number="ISESSCASE001",
            counselor_id=island_counselor.id,
            client_id=island_client.id,
            tenant_id="island",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add_all([island_client, island_case])
        db_session.flush()

        # Create sessions for both tenants
        from app.models.session import Session as SessionModel

        career_session = SessionModel(
            id=uuid4(),
            case_id=career_case.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="Career session transcript",
        )
        island_session = SessionModel(
            id=uuid4(),
            case_id=island_case.id,
            tenant_id="island",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="Island session transcript",
        )
        db_session.add_all([career_session, island_session])
        db_session.commit()

        # Login as career counselor
        career_login = test_client.post(
            "/api/auth/login",
            json={
                "email": "career-sessions@test.com",
                "password": "ValidP@ssw0rd123",
                "tenant_id": "career",
            },
        )
        career_token = career_login.json()["access_token"]
        career_headers = {"Authorization": f"Bearer {career_token}"}

        # Login as island counselor
        island_login = test_client.post(
            "/api/auth/login",
            json={
                "email": "island-sessions@test.com",
                "password": "ValidP@ssw0rd123",
                "tenant_id": "island",
            },
        )
        island_token = island_login.json()["access_token"]
        island_headers = {"Authorization": f"Bearer {island_token}"}

        # Career counselor should only see career sessions
        career_sessions = test_client.get(
            "/api/v1/sessions",
            headers=career_headers,
        )
        assert career_sessions.status_code == 200
        career_sessions_data = career_sessions.json()
        assert career_sessions_data["total"] == 1
        assert len(career_sessions_data["items"]) == 1
        assert career_sessions_data["items"][0]["id"] == str(career_session.id)

        # Island counselor should only see island sessions
        island_sessions = test_client.get(
            "/api/v1/sessions",
            headers=island_headers,
        )
        assert island_sessions.status_code == 200
        island_sessions_data = island_sessions.json()
        assert island_sessions_data["total"] == 1
        assert len(island_sessions_data["items"]) == 1
        assert island_sessions_data["items"][0]["id"] == str(island_session.id)

        # Career counselor should NOT be able to access island session
        career_session_detail = test_client.get(
            f"/api/v1/sessions/{island_session.id}",
            headers=career_headers,
        )
        assert career_session_detail.status_code == 404  # Not found (tenant isolation)

        # Island counselor should NOT be able to access career session
        island_session_detail = test_client.get(
            f"/api/v1/sessions/{career_session.id}",
            headers=island_headers,
        )
        assert island_session_detail.status_code == 404  # Not found (tenant isolation)

    def test_multi_tenant_isolation_clients_and_cases(
        self,
        test_client: TestClient,
        db_session: Session,
    ):
        """Test that clients and cases APIs are properly isolated by tenant"""
        # Create counselors
        career_counselor = Counselor(
            id=uuid4(),
            email="career-crud@test.com",
            username="careercrud",
            full_name="Career CRUD Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        island_counselor = Counselor(
            id=uuid4(),
            email="island-crud@test.com",
            username="islandcrud",
            full_name="Island CRUD Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="island",
            role="counselor",
            is_active=True,
        )
        db_session.add_all([career_counselor, island_counselor])
        db_session.flush()

        # Create clients for both tenants
        career_client = Client(
            id=uuid4(),
            counselor_id=career_counselor.id,
            tenant_id="career",
            name="Career CRUD Client",
            code="CCRUD001",
            email="career-crud@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0911111111",
            identity_option="在職者",
            current_status="工作中",
        )
        island_client = Client(
            id=uuid4(),
            counselor_id=island_counselor.id,
            tenant_id="island",
            name="Island CRUD Client",
            code="ICRUD001",
            email="island-crud@example.com",
            gender="女",
            birth_date=date(1992, 1, 1),
            phone="0922222222",
            identity_option="學生",
            current_status="在學中",
        )
        db_session.add_all([career_client, island_client])
        db_session.flush()

        # Create cases
        career_case = Case(
            id=uuid4(),
            case_number="CCRUDCASE001",
            counselor_id=career_counselor.id,
            client_id=career_client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        island_case = Case(
            id=uuid4(),
            case_number="ICRUDCASE001",
            counselor_id=island_counselor.id,
            client_id=island_client.id,
            tenant_id="island",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add_all([career_case, island_case])
        db_session.commit()

        # Login
        career_login = test_client.post(
            "/api/auth/login",
            json={
                "email": "career-crud@test.com",
                "password": "ValidP@ssw0rd123",
                "tenant_id": "career",
            },
        )
        career_headers = {
            "Authorization": f"Bearer {career_login.json()['access_token']}"
        }

        island_login = test_client.post(
            "/api/auth/login",
            json={
                "email": "island-crud@test.com",
                "password": "ValidP@ssw0rd123",
                "tenant_id": "island",
            },
        )
        island_headers = {
            "Authorization": f"Bearer {island_login.json()['access_token']}"
        }

        # Test Clients API isolation
        career_clients = test_client.get("/api/v1/clients", headers=career_headers)
        assert career_clients.status_code == 200
        career_clients_data = career_clients.json()
        assert career_clients_data["total"] == 1
        assert career_clients_data["items"][0]["id"] == str(career_client.id)

        island_clients = test_client.get("/api/v1/clients", headers=island_headers)
        assert island_clients.status_code == 200
        island_clients_data = island_clients.json()
        assert island_clients_data["total"] == 1
        assert island_clients_data["items"][0]["id"] == str(island_client.id)

        # Test Cases API isolation
        career_cases = test_client.get("/api/v1/cases", headers=career_headers)
        assert career_cases.status_code == 200
        career_cases_data = career_cases.json()
        assert career_cases_data["total"] == 1
        assert career_cases_data["items"][0]["id"] == str(career_case.id)

        island_cases = test_client.get("/api/v1/cases", headers=island_headers)
        assert island_cases.status_code == 200
        island_cases_data = island_cases.json()
        assert island_cases_data["total"] == 1
        assert island_cases_data["items"][0]["id"] == str(island_case.id)

        # Test cross-tenant access blocked
        career_get_island_client = test_client.get(
            f"/api/v1/clients/{island_client.id}",
            headers=career_headers,
        )
        assert career_get_island_client.status_code == 404

        island_get_career_case = test_client.get(
            f"/api/v1/cases/{career_case.id}",
            headers=island_headers,
        )
        assert island_get_career_case.status_code == 404

    def test_counselor_isolation_same_tenant(
        self,
        test_client: TestClient,
        db_session: Session,
    ):
        """Test that counselors in the same tenant cannot see each other's data"""
        # Create two counselors in the same tenant "career"
        counselor_a = Counselor(
            id=uuid4(),
            email="counselor-a@test.com",
            username="counselora",
            full_name="Counselor A",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        counselor_b = Counselor(
            id=uuid4(),
            email="counselor-b@test.com",
            username="counselorb",
            full_name="Counselor B",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add_all([counselor_a, counselor_b])
        db_session.flush()

        # Create clients and cases for counselor A
        client_a = Client(
            id=uuid4(),
            counselor_id=counselor_a.id,
            tenant_id="career",
            name="Counselor A Client",
            code="COUNSELORA001",
            email="counselor-a-client@example.com",
            gender="男",
            birth_date=date(1990, 1, 1),
            phone="0911111111",
            identity_option="在職者",
            current_status="工作中",
        )
        case_a = Case(
            id=uuid4(),
            case_number="CASE_A001",
            counselor_id=counselor_a.id,
            client_id=client_a.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add_all([client_a, case_a])
        db_session.flush()

        # Create clients and cases for counselor B
        client_b = Client(
            id=uuid4(),
            counselor_id=counselor_b.id,
            tenant_id="career",
            name="Counselor B Client",
            code="COUNSELORB001",
            email="counselor-b-client@example.com",
            gender="女",
            birth_date=date(1992, 1, 1),
            phone="0922222222",
            identity_option="學生",
            current_status="在學中",
        )
        case_b = Case(
            id=uuid4(),
            case_number="CASE_B001",
            counselor_id=counselor_b.id,
            client_id=client_b.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add_all([client_b, case_b])
        db_session.commit()

        # Login as counselor A
        login_a = test_client.post(
            "/api/auth/login",
            json={
                "email": "counselor-a@test.com",
                "password": "ValidP@ssw0rd123",
                "tenant_id": "career",
            },
        )
        headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

        # Login as counselor B
        login_b = test_client.post(
            "/api/auth/login",
            json={
                "email": "counselor-b@test.com",
                "password": "ValidP@ssw0rd123",
                "tenant_id": "career",
            },
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        # Counselor A should only see their own client-case list
        response_a = test_client.get(
            "/api/v1/ui/client-case-list",
            headers=headers_a,
        )
        assert response_a.status_code == 200
        data_a = response_a.json()
        assert data_a["total"] == 1
        assert data_a["items"][0]["client_name"] == "Counselor A Client"
        assert data_a["items"][0]["case_number"] == "CASE_A001"

        # Counselor B should only see their own client-case list
        response_b = test_client.get(
            "/api/v1/ui/client-case-list",
            headers=headers_b,
        )
        assert response_b.status_code == 200
        data_b = response_b.json()
        assert data_b["total"] == 1
        assert data_b["items"][0]["client_name"] == "Counselor B Client"
        assert data_b["items"][0]["case_number"] == "CASE_B001"

        # Counselor A should NOT be able to access counselor B's case
        detail_a_try_b = test_client.get(
            f"/api/v1/ui/client-case/{case_b.id}",
            headers=headers_a,
        )
        assert detail_a_try_b.status_code == 404  # Not found (counselor isolation)

        # Counselor B should NOT be able to access counselor A's case
        detail_b_try_a = test_client.get(
            f"/api/v1/ui/client-case/{case_a.id}",
            headers=headers_b,
        )
        assert detail_b_try_a.status_code == 404  # Not found (counselor isolation)

        # Test Cases API isolation
        cases_a = test_client.get("/api/v1/cases", headers=headers_a)
        assert cases_a.status_code == 200
        cases_a_data = cases_a.json()
        assert cases_a_data["total"] == 1
        assert cases_a_data["items"][0]["id"] == str(case_a.id)

        cases_b = test_client.get("/api/v1/cases", headers=headers_b)
        assert cases_b.status_code == 200
        cases_b_data = cases_b.json()
        assert cases_b_data["total"] == 1
        assert cases_b_data["items"][0]["id"] == str(case_b.id)

        # Test Clients API isolation
        clients_a = test_client.get("/api/v1/clients", headers=headers_a)
        assert clients_a.status_code == 200
        clients_a_data = clients_a.json()
        assert clients_a_data["total"] == 1
        assert clients_a_data["items"][0]["id"] == str(client_a.id)

        clients_b = test_client.get("/api/v1/clients", headers=headers_b)
        assert clients_b.status_code == 200
        clients_b_data = clients_b.json()
        assert clients_b_data["total"] == 1
        assert clients_b_data["items"][0]["id"] == str(client_b.id)
