"""
Integration tests for Sessions API
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


class TestSessionsAPI:
    """Test Sessions CRUD and special endpoints"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-sessions@test.com",
            username="sessionscounselor",
            full_name="Sessions Test Counselor",
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
                json={"email": "counselor-sessions@test.com", "password": "password123", "tenant_id": "career"},
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_case_obj(self, db_session: Session):
        """Create a test case for session tests"""
        counselor = db_session.query(Counselor).filter_by(email="counselor-sessions@test.com").first()

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="會談測試客戶",
            code="SCLI001",
        )
        db_session.add(client)
        db_session.commit()

        case = Case(
            id=uuid4(),
            case_number="SCASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(case)
        db_session.commit()

        return case

    def test_create_session_success(self, db_session: Session, auth_headers, test_case_obj):
        """Test POST /api/v1/sessions - Create new session"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/sessions",
                headers=auth_headers,
                json={
                    "case_id": str(test_case_obj.id),
                    "session_date": "2025-01-15",
                    "start_time": "2025-01-15 10:00",
                    "end_time": "2025-01-15 11:00",
                    "transcript": "這是一段會談逐字稿內容。",
                    "notes": "會談筆記",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["case_id"] == str(test_case_obj.id)
            assert "session_number" in data
            assert "id" in data

    def test_create_session_with_recordings(self, db_session: Session, auth_headers, test_case_obj):
        """Test creating session with recordings array"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/sessions",
                headers=auth_headers,
                json={
                    "case_id": str(test_case_obj.id),
                    "session_date": "2025-01-15",
                    "recordings": [
                        {
                            "segment_number": 1,
                            "start_time": "2025-01-15 10:00",
                            "end_time": "2025-01-15 10:30",
                            "duration_seconds": 1800,
                            "transcript_text": "第一段逐字稿",
                        },
                        {
                            "segment_number": 2,
                            "start_time": "2025-01-15 10:30",
                            "end_time": "2025-01-15 11:00",
                            "duration_seconds": 1800,
                            "transcript_text": "第二段逐字稿",
                        },
                    ],
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["recordings"]) == 2
            # Transcript should be auto-aggregated
            assert "第一段逐字稿" in (data["transcript_text"] or "")
            assert "第二段逐字稿" in (data["transcript_text"] or "")

    def test_create_session_minimal_fields(self, db_session: Session, auth_headers, test_case_obj):
        """Test creating session with only required fields"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/sessions",
                headers=auth_headers,
                json={
                    "case_id": str(test_case_obj.id),
                    "session_date": "2025-01-15",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["case_id"] == str(test_case_obj.id)

    def test_create_session_unauthorized(self, test_case_obj):
        """Test creating session without auth returns 403"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/sessions",
                json={
                    "case_id": str(test_case_obj.id),
                    "session_date": "2025-01-15",
                },
            )

            assert response.status_code == 403

    def test_list_sessions_success(self, db_session: Session, auth_headers, test_case_obj):
        """Test GET /api/v1/sessions - List all sessions"""
        # Create test sessions
        session1 = SessionModel(
            id=uuid4(),
            case_id=test_case_obj.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
        )
        session2 = SessionModel(
            id=uuid4(),
            case_id=test_case_obj.id,
            tenant_id="career",
            session_number=2,
            session_date=datetime.now(timezone.utc),
        )
        db_session.add_all([session1, session2])
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/sessions",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "total" in data
            assert "items" in data
            assert data["total"] >= 2

    def test_list_sessions_filter_by_client(self, db_session: Session, auth_headers, test_case_obj):
        """Test GET /api/v1/sessions?client_id=xxx - Filter by client"""
        counselor = db_session.query(Counselor).filter_by(email="counselor-sessions@test.com").first()

        # Get the client from test_case_obj
        client_obj = db_session.query(Client).filter_by(id=test_case_obj.client_id).first()

        session = SessionModel(
            id=uuid4(),
            case_id=test_case_obj.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
        )
        db_session.add(session)
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/sessions?client_id={client_obj.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            # All sessions should belong to the specified client
            for item in data["items"]:
                assert item["client_id"] == str(client_obj.id)

    def test_get_session_success(self, db_session: Session, auth_headers, test_case_obj):
        """Test GET /api/v1/sessions/{id} - Get session details"""
        test_session = SessionModel(
            id=uuid4(),
            case_id=test_case_obj.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="測試逐字稿",
        )
        db_session.add(test_session)
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/sessions/{test_session.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == str(test_session.id)
            assert data["session_number"] == 1
            assert data["transcript_text"] == "測試逐字稿"

    def test_get_session_not_found(self, db_session: Session, auth_headers):
        """Test getting non-existent session returns 404"""
        fake_id = uuid4()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/sessions/{fake_id}",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_update_session_success(self, db_session: Session, auth_headers, test_case_obj):
        """Test PATCH /api/v1/sessions/{id} - Update session"""
        test_session = SessionModel(
            id=uuid4(),
            case_id=test_case_obj.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
        )
        db_session.add(test_session)
        db_session.commit()

        with TestClient(app) as client:
            response = client.patch(
                f"/api/v1/sessions/{test_session.id}",
                headers=auth_headers,
                json={
                    "notes": "更新後的會談筆記",
                    "transcript": "更新後的逐字稿",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["notes"] == "更新後的會談筆記"

    def test_delete_session_success(self, db_session: Session, auth_headers, test_case_obj):
        """Test DELETE /api/v1/sessions/{id} - Soft delete session"""
        test_session = SessionModel(
            id=uuid4(),
            case_id=test_case_obj.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
        )
        db_session.add(test_session)
        db_session.commit()

        with TestClient(app) as client:
            # Delete session
            response = client.delete(
                f"/api/v1/sessions/{test_session.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data

            # Verify session no longer appears in list
            list_response = client.get(
                "/api/v1/sessions",
                headers=auth_headers,
            )
            list_data = list_response.json()
            session_ids = [item["id"] for item in list_data["items"]]
            assert str(test_session.id) not in session_ids

    def test_delete_session_not_found(self, db_session: Session, auth_headers):
        """Test deleting non-existent session returns 404"""
        fake_id = uuid4()

        with TestClient(app) as client:
            response = client.delete(
                f"/api/v1/sessions/{fake_id}",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_get_client_timeline_success(self, db_session: Session, auth_headers, test_case_obj):
        """Test GET /api/v1/sessions/timeline?client_id=xxx - Get client timeline"""
        # Create multiple sessions
        for i in range(3):
            session = SessionModel(
                id=uuid4(),
                case_id=test_case_obj.id,
                tenant_id="career",
                session_number=i + 1,
                session_date=datetime.now(timezone.utc),
                summary=f"第{i+1}次會談摘要",
            )
            db_session.add(session)
        db_session.commit()

        client_obj = db_session.query(Client).filter_by(id=test_case_obj.client_id).first()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/sessions/timeline?client_id={client_obj.id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "client_id" in data
            assert "sessions" in data
            assert len(data["sessions"]) == 3

    def test_get_reflection_success(self, db_session: Session, auth_headers, test_case_obj):
        """Test GET /api/v1/sessions/{id}/reflection - Get reflection"""
        test_session = SessionModel(
            id=uuid4(),
            case_id=test_case_obj.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            reflection={"key_insights": "個案顯示出積極態度", "next_steps": "繼續探索職涯選項"},
        )
        db_session.add(test_session)
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/sessions/{test_session.id}/reflection",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "reflection" in data
            assert data["reflection"]["key_insights"] == "個案顯示出積極態度"

    def test_update_reflection_success(self, db_session: Session, auth_headers, test_case_obj):
        """Test PUT /api/v1/sessions/{id}/reflection - Update reflection"""
        test_session = SessionModel(
            id=uuid4(),
            case_id=test_case_obj.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
        )
        db_session.add(test_session)
        db_session.commit()

        with TestClient(app) as client:
            response = client.put(
                f"/api/v1/sessions/{test_session.id}/reflection",
                headers=auth_headers,
                json={
                    "reflection": {
                        "key_insights": "新的反思洞察",
                        "challenges": "個案面臨的挑戰",
                    }
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["reflection"]["key_insights"] == "新的反思洞察"

    def test_pagination(self, db_session: Session, auth_headers, test_case_obj):
        """Test pagination parameters (skip, limit)"""
        # Create multiple sessions
        for i in range(5):
            session = SessionModel(
                id=uuid4(),
                case_id=test_case_obj.id,
                tenant_id="career",
                session_number=i + 1,
                session_date=datetime.now(timezone.utc),
            )
            db_session.add(session)
        db_session.commit()

        with TestClient(app) as client:
            # Test limit
            response = client.get(
                "/api/v1/sessions?limit=3",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 3

            # Test skip
            response = client.get(
                "/api/v1/sessions?skip=2&limit=2",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["items"]) <= 2
