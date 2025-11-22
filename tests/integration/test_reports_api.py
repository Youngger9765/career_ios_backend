"""
Integration tests for Reports API
TDD - Write tests first, then implement
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone

from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor
from app.models.client import Client
from app.models.case import Case, CaseStatus
from app.models.session import Session as SessionModel
from app.models.report import Report, ReportStatus


class TestReportsAPI:
    """Test Reports CRUD and generation endpoints"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-reports@test.com",
            username="reportscounselor",
            full_name="Reports Test Counselor",
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
                json={"email": "counselor-reports@test.com", "password": "password123", "tenant_id": "career"},
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_session_obj(self, db_session: Session):
        """Create a test session for report tests"""
        counselor = db_session.query(Counselor).filter_by(email="counselor-reports@test.com").first()

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="報告測試客戶",
            code="RCLI001",
        )
        db_session.add(client)
        db_session.commit()

        case = Case(
            id=uuid4(),
            case_number="RCASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(case)
        db_session.commit()

        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="這是一段完整的會談逐字稿內容，用於測試報告生成功能。",
        )
        db_session.add(session)
        db_session.commit()

        return session

    def test_list_reports_success(self, db_session: Session, auth_headers, test_session_obj):
        """Test GET /api/v1/reports - List all reports"""
        # Create test reports
        report1 = Report(
            id=uuid4(),
            session_id=test_session_obj.id,
            content_json={},
            formatted_markdown="# 報告1",
            status=ReportStatus.DRAFT,
        )
        report2 = Report(
            id=uuid4(),
            session_id=test_session_obj.id,
            content_json={},
            formatted_markdown="# 報告2",
            status=ReportStatus.FINAL,
        )
        db_session.add_all([report1, report2])
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/reports",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "total" in data
            assert "items" in data
            assert data["total"] >= 2

    def test_list_reports_filter_by_session(self, db_session: Session, auth_headers, test_session_obj):
        """Test GET /api/v1/reports?session_id=xxx - Filter by session"""
        report = Report(
            id=uuid4(),
            session_id=test_session_obj.id,
            content_json={},
            formatted_markdown="# 測試報告",
            status=ReportStatus.DRAFT,
        )
        db_session.add(report)
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/reports?session_id={test_session_obj.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            # All reports should belong to the specified session
            for item in data["items"]:
                assert item["session_id"] == str(test_session_obj.id)

    def test_get_report_success(self, db_session: Session, auth_headers, test_session_obj):
        """Test GET /api/v1/reports/{id} - Get report details"""
        test_report = Report(
            id=uuid4(),
            session_id=test_session_obj.id,
            content_json={"summary": "報告摘要"},
            formatted_markdown="# 完整報告內容",
            status=ReportStatus.FINAL,
        )
        db_session.add(test_report)
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/reports/{test_report.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(test_report.id)
            assert data["status"] == "final"
            assert "formatted_markdown" in data

    def test_get_report_not_found(self, db_session: Session, auth_headers):
        """Test getting non-existent report returns 404"""
        fake_id = uuid4()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/reports/{fake_id}",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_update_report_success(self, db_session: Session, auth_headers, test_session_obj):
        """Test PATCH /api/v1/reports/{id} - Update report (iOS only)"""
        test_report = Report(
            id=uuid4(),
            session_id=test_session_obj.id,
            content_json={"summary": "原始摘要"},
            formatted_markdown="# 原始內容",
            status=ReportStatus.DRAFT,
        )
        db_session.add(test_report)
        db_session.commit()

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/reports/{test_report.id}",
                headers=auth_headers,
                json={
                    "edited_content_json": {
                        "summary": "更新後的摘要",
                        "key_points": ["要點1", "要點2"],
                    }
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "edited_at" in data
            assert data["edit_count"] >= 1

    def test_update_report_not_found(self, db_session: Session, auth_headers):
        """Test updating non-existent report returns 404"""
        fake_id = uuid4()

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/reports/{fake_id}",
                headers=auth_headers,
                json={"edited_content_json": {}},
            )

            assert response.status_code == 404

    def test_pagination(self, db_session: Session, auth_headers, test_session_obj):
        """Test pagination parameters (skip, limit)"""
        # Create multiple reports
        for i in range(5):
            report = Report(
                id=uuid4(),
                session_id=test_session_obj.id,
                content_json={},
                formatted_markdown=f"# 報告{i}",
                status=ReportStatus.DRAFT,
            )
            db_session.add(report)
        db_session.commit()

        with TestClient(app) as client:
            # Test limit
            response = client.get(
                "/api/v1/reports?limit=3",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 3

            # Test skip
            response = client.get(
                "/api/v1/reports?skip=2&limit=2",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 2
