"""Integration tests for AI-powered safety assessment

TDD RED Phase - These tests are EXPECTED TO FAIL initially
"""
import pytest
from uuid import uuid4
from datetime import date, datetime
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.counselor import Counselor
from app.models.client import Client
from app.models.case import Case, CaseStatus
from app.models.session import Session as SessionModel
from app.core.security import hash_password


class TestSafetyAssessmentAI:
    """Test AI-powered safety assessment - TDD Style"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="ai-safety-test@test.com",
            username="aisafetytester",
            full_name="AI Safety Tester",
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
                    "email": "ai-safety-test@test.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_case_obj(self, db_session: Session, auth_headers):
        """Create a test case with client"""
        counselor = (
            db_session.query(Counselor)
            .filter_by(email="ai-safety-test@test.com")
            .first()
        )

        # Create client
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="AI安全測試客戶",
            code="AISAFE001",
            email="aisafe@example.com",
            gender="不透露",
            birth_date=date(2015, 1, 1),
            phone="0987654321",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(client)
        db_session.commit()

        # Create case
        case = Case(
            id=uuid4(),
            case_number="AI_SAFE_CASE_001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)
        db_session.commit()

        return case

    def test_safe_conversation_returns_green_level(
        self, db_session: Session, auth_headers, test_case_obj
    ):
        """Test safe conversation returns GREEN safety level"""
        # Create safe conversation transcript
        safe_messages = [
            "counselor: 你今天好嗎？",
            "client: 我很好，謝謝。",
            "counselor: 有什麼想分享的嗎？",
            "client: 我今天很開心，學校很順利。",
        ]
        transcript_text = "\n".join(safe_messages)

        # Create session with transcript
        session = SessionModel(
            id=uuid4(),
            case_id=test_case_obj.id,
            tenant_id="career",
            session_mode="practice",
            session_number=1,
            session_date=date.today(),
            transcript_text=transcript_text,  # Add transcript directly
        )
        db_session.add(session)
        db_session.commit()

        with TestClient(app) as client:
            # Call deep-analyze endpoint
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze",
                headers=auth_headers
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()

            # Check required fields (RealtimeAnalyzeResponse schema)
            assert "safety_level" in data
            assert "summary" in data
            assert "alerts" in data
            assert "suggestions" in data

            # Check field values
            assert data["safety_level"] in ["green", "yellow", "red"]
            assert isinstance(data["summary"], str)
            assert len(data["summary"]) > 0
            assert isinstance(data["alerts"], list)
            assert isinstance(data["suggestions"], list)

            # Verify GREEN level for safe conversation
            assert data["safety_level"] == "green", f"Expected GREEN but got {data['safety_level']}"
