"""
Integration tests for Quick Feedback API
Tests the /api/v1/sessions/{session_id}/quick-feedback endpoint
"""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
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


# Skip tests if Google Cloud credentials are not available
def _check_gcp_credentials():
    """Check if valid GCP credentials are available"""
    try:
        from google.auth import default
        from google.auth.exceptions import DefaultCredentialsError, RefreshError

        try:
            credentials, project = default()
            from google.auth.transport.requests import Request

            credentials.refresh(Request())
            return True
        except (DefaultCredentialsError, RefreshError, Exception):
            return False
    except ImportError:
        return False


HAS_VALID_GCP_CREDENTIALS = _check_gcp_credentials()

skip_without_gcp = pytest.mark.skipif(
    not HAS_VALID_GCP_CREDENTIALS,
    reason="Valid Google Cloud credentials not available (run: gcloud auth application-default login)",
)


class TestQuickFeedbackAPI:
    """Test Quick Feedback API endpoints"""

    @pytest.fixture
    def mock_gemini_service(self):
        """Mock GeminiService for quick feedback"""

        async def mock_generate_text(prompt, *args, **kwargs):
            if "Practice Mode" in prompt:
                return "練習語氣溫和，同理心充足，繼續保持"
            else:
                return "對話氣氛良好，繼續保持同理回應"

        with patch(
            "app.services.core.quick_feedback_service.GeminiService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.generate_text = AsyncMock(side_effect=mock_generate_text)
            # Mock the text property on the response
            mock_response = MagicMock()
            mock_response.text = "練習語氣溫和，同理心充足"
            mock_instance.generate_text.return_value = mock_response
            yield mock_instance

    @pytest.fixture
    def counselor_with_session(self, db_session: Session):
        """Create counselor with client, case, and session for testing"""
        # Create counselor
        counselor = Counselor(
            id=uuid4(),
            email="quick-feedback-api-test@test.com",
            username="quickfeedbackapitest",
            full_name="Quick Feedback API Test Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.flush()

        # Create client
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="QFAPI-TEST-001",
            name="測試家長",
            email="qfapi-parent@test.com",
            gender="女",
            birth_date=date(1985, 1, 1),
            phone="0912345678",
            identity_option="家長",
            current_status="親子溝通困擾",
            tenant_id="island_parents",
        )
        db_session.add(client)
        db_session.flush()

        # Create case
        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="island_parents",
            case_number="QFAPI-CASE-001",
            goals="改善親子溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Create session with transcript
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長：你再這樣我就生氣了！\n孩子：我不是故意的...",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：你再這樣我就生氣了！\n孩子：我不是故意的...",
                    "end_time": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        db_session.add(session)
        db_session.commit()

        return {
            "counselor": counselor,
            "client": client,
            "case": case,
            "session": session,
        }

    @pytest.fixture
    def auth_headers(self, db_session: Session, counselor_with_session):
        """Login and return auth headers"""
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "quick-feedback-api-test@test.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @skip_without_gcp
    def test_quick_feedback_success(
        self, db_session: Session, auth_headers, counselor_with_session
    ):
        """Test POST /api/v1/sessions/{session_id}/quick-feedback - Success case with valid transcript"""
        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/quick-feedback",
                headers=auth_headers,
            )

            assert response.status_code == 200

            data = response.json()

            # Verify response structure
            assert "message" in data
            assert "type" in data
            assert "timestamp" in data
            assert "latency_ms" in data

            # Verify data types
            assert isinstance(data["message"], str)
            assert isinstance(data["type"], str)
            assert isinstance(data["timestamp"], str)
            assert isinstance(data["latency_ms"], int)

            # Verify content
            assert len(data["message"]) > 0
            assert data["type"] in ["ai_generated", "fallback", "fallback_error"]
            assert data["latency_ms"] >= 0

    def test_quick_feedback_session_not_found(
        self, db_session: Session, auth_headers, mock_gemini_service
    ):
        """Test validation returns 404 for non-existent session"""
        fake_session_id = uuid4()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{fake_session_id}/quick-feedback",
                headers=auth_headers,
            )

            assert response.status_code == 404

    def test_quick_feedback_no_transcript(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test validation rejects session with empty transcript"""
        # Create session without transcript
        session_no_transcript = SessionModel(
            id=uuid4(),
            case_id=counselor_with_session["case"].id,
            tenant_id="island_parents",
            session_number=2,
            session_date=datetime.now(timezone.utc),
            transcript_text="",  # Empty transcript
            recordings=[],
        )
        db_session.add(session_no_transcript)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_no_transcript.id}/quick-feedback",
                headers=auth_headers,
            )

            assert response.status_code == 400
            data = response.json()
            assert "no transcript" in data["detail"].lower()

    def test_quick_feedback_unauthorized(
        self, db_session: Session, counselor_with_session
    ):
        """Test quick feedback without auth returns 403"""
        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/quick-feedback",
            )

            assert response.status_code == 403

    @skip_without_gcp
    def test_quick_feedback_performance_latency(
        self, db_session: Session, auth_headers, counselor_with_session
    ):
        """Test latency is reasonable (< 5 seconds for integration test)"""
        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/quick-feedback",
                headers=auth_headers,
            )

            assert response.status_code == 200

            data = response.json()

            # Latency should be reasonable
            # Note: In production target is < 2s, but integration tests may be slower
            # Network latency + Gemini API response time can exceed 5s in some cases
            assert data["latency_ms"] < 8000  # 8 seconds max for integration tests

    @skip_without_gcp
    def test_quick_feedback_message_quality(
        self, db_session: Session, auth_headers, counselor_with_session
    ):
        """Test message is concise and appropriate"""
        # Create a session with positive transcript
        positive_session = SessionModel(
            id=uuid4(),
            case_id=counselor_with_session["case"].id,
            tenant_id="island_parents",
            session_number=3,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長：你做得很好！\n孩子：謝謝媽媽",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：你做得很好！\n孩子：謝謝媽媽",
                    "end_time": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        db_session.add(positive_session)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{positive_session.id}/quick-feedback",
                headers=auth_headers,
            )

            assert response.status_code == 200

            data = response.json()

            # Message should exist and not be empty
            assert len(data["message"]) > 0

            # Message MUST be <= 15 chars (server-side truncation enforced)
            assert (
                len(data["message"]) <= 15
            ), f"Message exceeds 15-char limit: {len(data['message'])} chars - '{data['message']}'"

    @skip_without_gcp
    def test_quick_feedback_dangerous_transcript(
        self, db_session: Session, auth_headers, counselor_with_session
    ):
        """Test response to potentially dangerous conversation"""
        # Create a session with dangerous transcript
        dangerous_session = SessionModel(
            id=uuid4(),
            case_id=counselor_with_session["case"].id,
            tenant_id="island_parents",
            session_number=4,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長：你再這樣我就打死你！\n孩子：我害怕...",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：你再這樣我就打死你！\n孩子：我害怕...",
                    "end_time": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        db_session.add(dangerous_session)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{dangerous_session.id}/quick-feedback",
                headers=auth_headers,
            )

            assert response.status_code == 200

            data = response.json()

            # Should still provide feedback (possibly calming message)
            assert len(data["message"]) > 0
            assert data["type"] in ["ai_generated", "fallback", "fallback_error"]

    @skip_without_gcp
    def test_quick_feedback_question_transcript(
        self, db_session: Session, auth_headers, counselor_with_session
    ):
        """Test response to question-based interaction"""
        # Create a session with question transcript
        question_session = SessionModel(
            id=uuid4(),
            case_id=counselor_with_session["case"].id,
            tenant_id="island_parents",
            session_number=5,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長：你今天在學校開心嗎？\n孩子：很開心",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：你今天在學校開心嗎？\n孩子：很開心",
                    "end_time": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        db_session.add(question_session)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{question_session.id}/quick-feedback",
                headers=auth_headers,
            )

            assert response.status_code == 200

            data = response.json()

            # Should provide encouraging feedback
            assert len(data["message"]) > 0

    @skip_without_gcp
    def test_quick_feedback_long_transcript(
        self, db_session: Session, auth_headers, counselor_with_session
    ):
        """Test handling of longer transcript (still within 10s window)"""
        long_transcript = "\n".join(
            [
                "家長：今天在學校怎麼樣？",
                "孩子：很好啊",
                "家長：有什麼開心的事嗎？",
                "孩子：我跟小明一起玩",
                "家長：那很棒啊",
                "孩子：對啊",
            ]
        )

        # Create a session with long transcript
        long_session = SessionModel(
            id=uuid4(),
            case_id=counselor_with_session["case"].id,
            tenant_id="island_parents",
            session_number=6,
            session_date=datetime.now(timezone.utc),
            transcript_text=long_transcript,
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": long_transcript,
                    "end_time": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )
        db_session.add(long_session)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{long_session.id}/quick-feedback",
                headers=auth_headers,
            )

            assert response.status_code == 200

            data = response.json()
            assert len(data["message"]) > 0
