"""Integration tests for analysis logs CRUD operations."""
import json
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session as SessionModel


class TestAnalysisLogsCRUD:
    """Test suite for analysis logs CRUD endpoints"""

    @pytest.fixture(autouse=True)
    def mock_gemini_service(self):
        """Mock GeminiService for CI environment"""

        async def mock_generate_text(prompt, *args, **kwargs):
            return json.dumps(
                {
                    "keywords": ["測試", "關鍵字", "分析"],
                    "categories": ["測試分類"],
                    "confidence": 0.85,
                    "counselor_insights": "測試洞見",
                }
            )

        with patch(
            "app.services.keyword_analysis_service.GeminiService"
        ) as mock_kw_service:
            mock_kw_service_instance = mock_kw_service.return_value
            mock_kw_service_instance.generate_text = mock_generate_text
            yield mock_kw_service_instance

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-logs@test.com",
            username="logscounselor",
            full_name="Logs Test Counselor",
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
                    "email": "counselor-logs@test.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}, counselor

    @pytest.fixture
    def test_session(self, db_session: Session, auth_headers):
        """Create test client, case, and session"""
        headers, counselor = auth_headers

        # Create client (with all required fields)
        from datetime import date

        client = Client(
            id=uuid4(),
            code="LOGS-001",
            name="分析日誌測試案主",
            email="logs-test@example.com",
            gender="不透露",
            birth_date=date(1990, 1, 1),
            phone="0912345678",
            identity_option="在職者",
            current_status="探索中",
            counselor_id=counselor.id,
            tenant_id="career",
            other_info={},
            tags=[],
        )
        db_session.add(client)

        # Create case
        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="career",
            case_number="1",  # String, not int
            status=1,  # CaseStatus.IN_PROGRESS
        )
        db_session.add(case)

        # Create session with some transcript
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="測試逐字稿內容",
            analysis_logs=[],  # Start with empty logs
        )
        db_session.add(session)
        db_session.commit()

        return session.id, headers

    def test_create_and_read_analysis_logs(self, test_session):
        """Test creating analysis logs via analyze-keywords and reading them"""
        session_id, headers = test_session

        with TestClient(app) as client:
            # CREATE: Analyze keywords (should save log)
            response1 = client.post(
                f"/api/v1/sessions/{session_id}/analyze-keywords",
                headers=headers,
                json={"transcript_segment": "我感到很焦慮和壓力"},
            )
            assert response1.status_code == 200
            result1 = response1.json()
            assert "keywords" in result1
            assert "categories" in result1

            # READ: Get analysis logs
            response2 = client.get(
                f"/api/v1/sessions/{session_id}/analysis-logs",
                headers=headers,
            )
            assert response2.status_code == 200
            logs_response = response2.json()
            assert logs_response["total"] == 1
            assert len(logs_response["items"]) == 1

            # Verify log content
            log = logs_response["items"][0]
            assert "analyzed_at" in log
            assert log["transcript"] == "我感到很焦慮和壓力"
            assert log["analysis_result"]["keywords"] == result1["keywords"]
            assert log["analysis_result"]["categories"] == result1["categories"]
            assert log["analysis_result"]["confidence"] == result1["confidence"]
            assert (
                log["analysis_result"]["counselor_insights"]
                == result1["counselor_insights"]
            )
            assert "counselor_id" in log
            # fallback is optional in analysis_result
            assert log["analysis_result"].get("fallback", False) is False

            # CREATE another log
            response3 = client.post(
                f"/api/v1/sessions/{session_id}/analyze-keywords",
                headers=headers,
                json={"transcript_segment": "我對未來感到迷惘"},
            )
            assert response3.status_code == 200

            # READ again - should have 2 logs now
            response4 = client.get(
                f"/api/v1/sessions/{session_id}/analysis-logs",
                headers=headers,
            )
            assert response4.status_code == 200
            logs_response = response4.json()
            assert logs_response["total"] == 2
            assert len(logs_response["items"]) == 2

            # Verify items exist (order may be DESC by analyzed_at)
            transcripts = [item["transcript"] for item in logs_response["items"]]
            assert "我感到很焦慮和壓力" in transcripts
            assert "我對未來感到迷惘" in transcripts

    def test_delete_analysis_log(self, test_session):
        """Test deleting a specific analysis log entry"""
        session_id, headers = test_session

        with TestClient(app) as client:
            # Create 3 logs
            for segment in ["第一次分析", "第二次分析", "第三次分析"]:
                response = client.post(
                    f"/api/v1/sessions/{session_id}/analyze-keywords",
                    headers=headers,
                    json={"transcript_segment": segment},
                )
                assert response.status_code == 200

            # Verify 3 logs exist
            response = client.get(
                f"/api/v1/sessions/{session_id}/analysis-logs",
                headers=headers,
            )
            logs_response = response.json()
            assert logs_response["total"] == 3

            # Get log IDs
            log_ids = [item["id"] for item in logs_response["items"]]
            assert len(log_ids) == 3

            # DELETE: Remove one log
            response = client.delete(
                f"/api/v1/sessions/{session_id}/analysis-logs/{log_ids[0]}",
                headers=headers,
            )
            assert response.status_code == 204

            # READ: Verify only 2 logs remain
            response = client.get(
                f"/api/v1/sessions/{session_id}/analysis-logs",
                headers=headers,
            )
            logs_response = response.json()
            assert logs_response["total"] == 2

            # DELETE: Remove another log
            response = client.delete(
                f"/api/v1/sessions/{session_id}/analysis-logs/{log_ids[1]}",
                headers=headers,
            )
            assert response.status_code == 204

            # READ: Verify only 1 log remains
            response = client.get(
                f"/api/v1/sessions/{session_id}/analysis-logs",
                headers=headers,
            )
            logs_response = response.json()
            assert logs_response["total"] == 1

    def test_delete_invalid_log_index(self, test_session):
        """Test deleting with invalid log ID"""
        session_id, headers = test_session

        with TestClient(app) as client:
            # Create 1 log
            client.post(
                f"/api/v1/sessions/{session_id}/analyze-keywords",
                headers=headers,
                json={"transcript_segment": "測試"},
            )

            # Try to delete with non-existent log ID
            fake_log_id = uuid4()
            response = client.delete(
                f"/api/v1/sessions/{session_id}/analysis-logs/{fake_log_id}",
                headers=headers,
            )
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]

    def test_empty_analysis_logs(self, test_session):
        """Test reading analysis logs when none exist"""
        session_id, headers = test_session

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/sessions/{session_id}/analysis-logs",
                headers=headers,
            )
            assert response.status_code == 200
            logs_response = response.json()
            assert logs_response["total"] == 0
            assert logs_response["items"] == []

    def test_unauthorized_access(self, test_session, db_session: Session):
        """Test that counselors can't access other counselors' session logs"""
        session_id, _ = test_session

        # Create another counselor
        other_counselor = Counselor(
            id=uuid4(),
            email="other@test.com",
            username="other",
            full_name="Other Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(other_counselor)
        db_session.commit()

        # Login as other counselor
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "other@test.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            other_token = login_response.json()["access_token"]
            other_headers = {"Authorization": f"Bearer {other_token}"}

            # Try to access logs - should fail
            response = client.get(
                f"/api/v1/sessions/{session_id}/analysis-logs",
                headers=other_headers,
            )
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

            # Try to delete logs - should fail (use fake log ID)
            fake_log_id = uuid4()
            response = client.delete(
                f"/api/v1/sessions/{session_id}/analysis-logs/{fake_log_id}",
                headers=other_headers,
            )
            assert response.status_code == 404
