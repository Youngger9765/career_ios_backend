"""Integration tests for session analysis API (quick-feedback, deep-analyze, report)."""
import json
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


class TestSessionDeepAnalyzeAPI:
    """Test suite for deep-analyze endpoint (optimized - 1 Gemini call)"""

    @pytest.fixture
    def mock_gemini_service(self):
        """Mock GeminiService to avoid needing GCP credentials in CI"""

        async def mock_generate_text(prompt, *args, **kwargs):
            # Check for practice mode indicators in prompt
            if "Practice Mode" in prompt or "單人練習" in prompt:
                # Practice mode: evaluate parent's speaking technique
                return json.dumps(
                    {
                        "safety_level": "green",
                        "display_text": "練習語氣溫和，同理心表達恰當",
                        "quick_suggestion": "你正在聽，而不是急著回",
                    }
                )
            elif "Emergency Mode" in prompt or "即時介入" in prompt:
                # Emergency mode: evaluate real parent-child interaction
                return json.dumps(
                    {
                        "safety_level": "yellow",
                        "display_text": "溝通略顯緊張，建議放慢速度",
                        "quick_suggestion": "孩子的感受還沒被接住",
                    }
                )
            else:
                # Default response
                return json.dumps(
                    {
                        "safety_level": "green",
                        "display_text": "分析完成",
                        "quick_suggestion": "持續保持良好溝通",
                    }
                )

        with patch(
            "app.services.keyword_analysis_service.GeminiService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.generate_text = mock_generate_text
            yield mock_instance

    @pytest.fixture
    def counselor_with_session(self, db_session: Session):
        """Create counselor with client, case, and session for testing"""
        # Create counselor
        counselor = Counselor(
            id=uuid4(),
            email="deep-analyze-test@test.com",
            username="deepanalyzecounselor",
            full_name="Deep Analyze Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
            available_credits=100.0,
        )
        db_session.add(counselor)
        db_session.flush()

        # Create client
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="DEEP-TEST-001",
            name="測試家長",
            email="parent@test.com",
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
            case_number="DEEP-CASE-001",
            goals="改善親子溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Create session with recordings
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長: 我今天想練習一下怎麼跟孩子說話",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長: 我看到你現在很生氣，我想了解發生什麼事了",
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
                    "email": "deep-analyze-test@test.com",
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_deep_analyze_practice_mode_success(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test deep analyze in practice mode returns parent skill evaluation"""
        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "safety_level" in data
        assert "summary" in data  # This is display_text
        assert "suggestions" in data
        assert "provider_metadata" in data

        # Verify safety level is valid
        assert data["safety_level"] in ["green", "yellow", "red"]

        # Verify practice mode: should NOT mention child's emotions
        assert "孩子正處於" not in data["summary"]
        assert "練習" in data["summary"] or "語氣" in data["summary"]

    def test_deep_analyze_emergency_mode_success(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test deep analyze in emergency mode returns interaction evaluation"""
        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=emergency",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "safety_level" in data
        assert "summary" in data
        assert "suggestions" in data

    def test_deep_analyze_session_not_found(
        self, db_session: Session, auth_headers, mock_gemini_service
    ):
        """Test deep analyze with non-existent session returns 404"""
        fake_session_id = uuid4()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{fake_session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 404

    def test_deep_analyze_no_recordings(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test deep analyze with session that has no recordings returns 400"""
        # Create session without recordings
        session_no_recordings = SessionModel(
            id=uuid4(),
            case_id=counselor_with_session["case"].id,
            tenant_id="island_parents",
            session_number=2,
            session_date=datetime.now(timezone.utc),
            recordings=[],  # No recordings
        )
        db_session.add(session_no_recordings)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_no_recordings.id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 400
        assert "no recordings" in response.json()["detail"].lower()

    def test_deep_analyze_unauthorized(
        self, db_session: Session, counselor_with_session
    ):
        """Test deep analyze without auth returns 403"""
        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
            )

        assert response.status_code == 403

    def test_deep_analyze_latency_metadata(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test that latency metadata is included in response"""
        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify provider metadata
        assert "provider_metadata" in data
        assert "latency_ms" in data["provider_metadata"]
        assert data["provider_metadata"]["latency_ms"] >= 0


class TestSessionQuickFeedbackAPI:
    """Test suite for quick-feedback endpoint"""

    @pytest.fixture
    def mock_gemini_service(self):
        """Mock GeminiService for quick feedback"""

        async def mock_generate_text(prompt, *args, **kwargs):
            if "Practice Mode" in prompt:
                return "🟢 練習語氣溫和，同理心充足，繼續保持"
            else:
                return "🟢 對話氣氛良好，繼續保持同理回應"

        with patch("app.services.quick_feedback_service.GeminiService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.generate_text = AsyncMock(side_effect=mock_generate_text)
            # Mock the text property on the response
            mock_response = MagicMock()
            mock_response.text = "🟢 練習語氣溫和，同理心充足"
            mock_instance.generate_text.return_value = mock_response
            yield mock_instance

    @pytest.fixture
    def counselor_with_session(self, db_session: Session):
        """Create counselor with client, case, and session for testing"""
        # Create counselor
        counselor = Counselor(
            id=uuid4(),
            email="quick-feedback-test@test.com",
            username="quickfeedbackcounselor",
            full_name="Quick Feedback Test Counselor",
            hashed_password=hash_password("password123"),
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
            code="QUICK-TEST-001",
            name="測試家長2",
            email="parent2@test.com",
            gender="男",
            birth_date=date(1980, 1, 1),
            phone="0923456789",
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
            case_number="QUICK-CASE-001",
        )
        db_session.add(case)
        db_session.flush()

        # Create session with recordings
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長: 我看到你現在很難過",
                }
            ],
        )
        db_session.add(session)
        db_session.commit()

        return {
            "counselor": counselor,
            "session": session,
        }

    @pytest.fixture
    def auth_headers(self, db_session: Session, counselor_with_session):
        """Login and return auth headers"""
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "quick-feedback-test@test.com",
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_quick_feedback_practice_mode_success(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test quick feedback in practice mode"""
        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/quick-feedback?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "message" in data
        assert "type" in data
        assert "timestamp" in data
        assert "latency_ms" in data

    def test_quick_feedback_session_not_found(
        self, db_session: Session, auth_headers, mock_gemini_service
    ):
        """Test quick feedback with non-existent session returns 404"""
        fake_session_id = uuid4()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{fake_session_id}/quick-feedback?mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 404
