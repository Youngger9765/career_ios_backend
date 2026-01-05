"""
Integration Tests for Realtime API GBQ Persistence (Phase 1.3)
TDD RED PHASE - Tests written FIRST to define expected behavior

These tests validate that realtime analysis results are persisted to BigQuery.
Now uses session-based endpoints (POST /api/v1/sessions/{session_id}/deep-analyze).
"""
import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch
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


# Skip these tests if Google Cloud credentials are not available
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


class TestRealtimeGBQPersistence:
    """Test GBQ persistence for Realtime API analysis results

    Expected behavior (TDD RED - will fail until implemented):
    1. After successful analysis, data is written to BigQuery asynchronously
    2. GBQ write failures do not block API response
    3. Data format matches the schema defined in Parents_RAG_refine.md
    4. tenant_id is always "island_parents" for web version
    5. session_id is properly associated with analysis
    """

    @pytest.fixture
    def mock_gemini_service(self):
        """Mock GeminiService to avoid needing GCP credentials in CI"""

        async def mock_generate_text(prompt, *args, **kwargs):
            # Default response for deep analyze
            return json.dumps(
                {
                    "safety_level": "green",
                    "display_text": "分析完成，溝通良好",
                    "quick_suggestion": "持續保持良好溝通",
                }
            )

        with patch(
            "app.services.keyword_analysis_service.GeminiService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.generate_text = AsyncMock(side_effect=mock_generate_text)
            yield mock_instance

    @pytest.fixture
    def counselor_with_session(self, db_session: Session):
        """Create counselor with client, case, and session for testing"""
        # Create counselor
        counselor = Counselor(
            id=uuid4(),
            email="gbq-persistence-test@test.com",
            username="gbqpersistencecounselor",
            full_name="GBQ Persistence Test Counselor",
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
            code="GBQ-TEST-001",
            name="GBQ Test Parent",
            email="gbqparent@test.com",
            gender="female",
            birth_date=date(1985, 1, 1),
            phone="0912345678",
            identity_option="parent",
            current_status="testing",
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
            case_number="GBQ-CASE-001",
            goals="Test GBQ persistence",
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
            transcript_text="家長：你今天在學校過得如何？\n孩子：還不錯，老師稱讚我了。",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：你今天在學校過得如何？",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "segment_number": 2,
                    "transcript_text": "孩子：還不錯，老師稱讚我了。",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat(),
                },
            ],
            session_mode="emergency",
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
                    "email": "gbq-persistence-test@test.com",
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @skip_without_gcp
    def test_realtime_analysis_writes_to_gbq_async(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Realtime analysis should write results to BigQuery asynchronously

        Expected behavior (RED - will fail until implemented):
        - API returns immediately (not blocked by GBQ write)
        - GBQ write happens in background
        - Data includes all required fields from schema
        """
        session_id = counselor_with_session["session"].id

        with patch(
            "app.api.session_analysis._log_analysis_background"
        ) as mock_log_background:
            # Configure mock to capture the call
            mock_log_background.return_value = None

            with TestClient(app) as client:
                response = client.post(
                    f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency",
                    headers=auth_headers,
                )

            # API should return immediately (200 OK)
            assert response.status_code == 200

            # Verify background logging was called
            assert (
                mock_log_background.called
            ), "Background logging function should be called"

            # Extract the call arguments
            call_kwargs = mock_log_background.call_args[1]

            # Validate logged data structure
            assert "session_id" in call_kwargs
            assert call_kwargs["session_id"] == session_id
            assert "tenant_id" in call_kwargs
            assert call_kwargs["tenant_id"] == "island_parents"
            assert "counselor_id" in call_kwargs
            assert "transcript_segment" in call_kwargs
            assert "result_data" in call_kwargs
            assert "token_usage_data" in call_kwargs

            # Validate result_data structure
            result_data = call_kwargs["result_data"]
            assert "analysis_type" in result_data
            assert result_data["analysis_type"] == "deep_analyze"
            assert "safety_level" in result_data
            assert result_data["safety_level"] in ["green", "yellow", "red"]

            # Validate token_usage_data structure
            token_usage_data = call_kwargs["token_usage_data"]
            assert "prompt_tokens" in token_usage_data
            assert "completion_tokens" in token_usage_data
            assert "total_tokens" in token_usage_data

    @skip_without_gcp
    def test_gbq_write_failure_does_not_block_api_response(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """GBQ write failures should not prevent API from returning success

        Expected behavior (RED - will fail until implemented):
        - If GBQ write fails, API still returns 200
        - Error is logged but not raised
        - User gets analysis results despite GBQ failure
        """
        session_id = counselor_with_session["session"].id

        with patch(
            "app.services.keyword_analysis_service.KeywordAnalysisService.save_analysis_log_and_usage"
        ) as mock_save_log:
            # Simulate log save failure
            mock_save_log.side_effect = Exception("GBQ unavailable")

            with TestClient(app) as client:
                # API should still return 200 despite logging failure
                # (logging happens in background task AFTER response)
                response = client.post(
                    f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency",
                    headers=auth_headers,
                )

            assert response.status_code == 200

            # Response should contain analysis results
            data = response.json()
            assert "safety_level" in data
            assert "suggestions" in data

    @skip_without_gcp
    def test_practice_mode_writes_correct_analysis_type_to_log(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Practice mode should write analysis_type='deep_analyze' with practice mode in metadata

        Expected behavior (RED - will fail until implemented):
        - analysis_type is 'deep_analyze'
        - session_mode in metadata reflects 'practice'
        """
        session_id = counselor_with_session["session"].id

        with patch(
            "app.api.session_analysis._log_analysis_background"
        ) as mock_log_background:
            mock_log_background.return_value = None

            with TestClient(app) as client:
                response = client.post(
                    f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=practice",
                    headers=auth_headers,
                )

            assert response.status_code == 200

            # Verify logged data
            call_kwargs = mock_log_background.call_args[1]
            result_data = call_kwargs["result_data"]

            assert result_data["analysis_type"] == "deep_analyze"
            assert result_data["_metadata"]["session_mode"] == "practice"

    @skip_without_gcp
    def test_log_data_includes_response_time_metric(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Logged data should include API response time for performance monitoring

        Expected behavior (RED - will fail until implemented):
        - latency_ms is calculated and included in metadata
        - Value is positive integer/float in milliseconds
        """
        session_id = counselor_with_session["session"].id

        with patch(
            "app.api.session_analysis._log_analysis_background"
        ) as mock_log_background:
            mock_log_background.return_value = None

            with TestClient(app) as client:
                response = client.post(
                    f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency",
                    headers=auth_headers,
                )

            assert response.status_code == 200

            # Verify response time is recorded in metadata
            call_kwargs = mock_log_background.call_args[1]
            result_data = call_kwargs["result_data"]

            assert "_metadata" in result_data
            assert "latency_ms" in result_data["_metadata"]
            assert isinstance(result_data["_metadata"]["latency_ms"], (int, float))
            assert (
                result_data["_metadata"]["latency_ms"] >= 0
            ), "Latency should be non-negative"

    @skip_without_gcp
    def test_log_errors_are_handled_gracefully(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
        caplog,
    ):
        """Log errors should be handled gracefully without failing the API

        Expected behavior (RED - will fail until implemented):
        - Errors during the KeywordAnalysisService.save_analysis_log_and_usage are caught
        - API response is not affected by logging errors
        - Error is logged for debugging

        Note: The actual _log_analysis_background function has error handling built in,
        so we test that the inner save function errors don't propagate.
        """
        import logging

        session_id = counselor_with_session["session"].id

        # Mock the inner save function to raise an exception
        # The _log_analysis_background function catches this and logs an error
        with patch(
            "app.services.keyword_analysis_service.KeywordAnalysisService.save_analysis_log_and_usage"
        ) as mock_save:
            mock_save.side_effect = Exception("BigQuery API error: quota exceeded")

            with caplog.at_level(logging.ERROR):
                with TestClient(app) as client:
                    # The API should still succeed even if background logging fails
                    # The _log_analysis_background function catches exceptions internally
                    response = client.post(
                        f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency",
                        headers=auth_headers,
                    )

            # API should return success regardless of background task issues
            assert response.status_code == 200

            # Response should contain valid analysis results
            data = response.json()
            assert "safety_level" in data
            assert "summary" in data
            assert "suggestions" in data

            # Verify error was logged
            error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
            assert len(error_logs) > 0, "Error should be logged when save fails"
            assert any(
                "deep_analyze" in r.message.lower() or "background" in r.message.lower()
                for r in error_logs
            ), "Error log should mention the analysis type"

    @skip_without_gcp
    def test_analysis_log_includes_session_context(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Analysis log should include full session context for debugging

        Expected behavior:
        - Session ID is included
        - Counselor ID is included
        - Tenant ID is included
        - Transcript segment is included
        """
        session_id = counselor_with_session["session"].id
        counselor_id = counselor_with_session["counselor"].id

        with patch(
            "app.api.session_analysis._log_analysis_background"
        ) as mock_log_background:
            mock_log_background.return_value = None

            with TestClient(app) as client:
                response = client.post(
                    f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency",
                    headers=auth_headers,
                )

            assert response.status_code == 200

            # Verify all context is included
            call_kwargs = mock_log_background.call_args[1]

            assert call_kwargs["session_id"] == session_id
            assert call_kwargs["counselor_id"] == counselor_id
            assert call_kwargs["tenant_id"] == "island_parents"
            assert len(call_kwargs["transcript_segment"]) > 0
            assert call_kwargs["analysis_type"] == "deep_analyze"
