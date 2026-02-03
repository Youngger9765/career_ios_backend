"""
Integration tests for RAG integration with Realtime Analysis API
Migrated to use session-based endpoint: POST /api/v1/sessions/{session_id}/deep-analyze

Tests verify that deep-analyze API returns proper response structure including rag_sources field.
Note: The simplified deep-analyze endpoint doesn't use RAG by default (use_rag=False),
but the response schema still includes rag_sources (empty list) for compatibility.
"""

import json
from datetime import date, datetime, timezone
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


class TestRealtimeRAGIntegration:
    """Test RAG integration with session-based deep-analyze API"""

    @pytest.fixture
    def mock_gemini_service(self):
        """Mock GeminiService to avoid needing GCP credentials in CI"""

        async def mock_generate_text(prompt, *args, **kwargs):
            # Return a mock response that matches the expected format
            return json.dumps(
                {
                    "safety_level": "green",
                    "display_text": "家長展現了積極的溝通態度，願意了解孩子的想法",
                    "quick_suggestion": "繼續保持開放態度，多用「我看到」「我感覺到」的語句",
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
            email="rag-integration-test@test.com",
            username="ragintegrationcounselor",
            full_name="RAG Integration Test Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
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
            code="RAG-TEST-001",
            name="測試家長",
            email="rag-parent@test.com",
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
            case_number="RAG-CASE-001",
            goals="改善親子溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Create session with parenting-related transcript
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="諮詢師：你和孩子的關係如何？\n案主：我不知道怎麼和他溝通。",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "諮詢師：你和孩子的關係如何？\n案主：我不知道怎麼和他溝通。",
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
                    "email": "rag-integration-test@test.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_rag_query_triggered_with_parenting_keywords(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 1: Deep-analyze with parenting keywords returns proper response structure

        Scenario: Given a session with parenting-related keywords (親子, 孩子)
        Expected: API should return response with rag_sources field (empty list in simplified mode)
        """
        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

            # Should return 200 OK
            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "summary" in data
            assert "alerts" in data
            assert "suggestions" in data
            assert "rag_sources" in data  # RAG sources field (empty in simplified mode)

            # Verify rag_sources is present and has valid structure
            assert isinstance(data["rag_sources"], list)

            # In simplified mode, rag_sources is always empty list
            # If use_rag=True is enabled in future, this would contain actual sources
            # The schema validation is still important for API compatibility

    def test_rag_results_integrated_in_suggestions(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 2: Deep-analyze returns suggestions for parenting issues

        Scenario: Given session with transcript about parenting issues
        Expected: AI suggestions should be returned in response
        """
        # Update session with specific parenting content
        session = counselor_with_session["session"]
        session.transcript_text = (
            "案主：我的孩子很叛逆，不知道怎麼管教，也不知道怎麼和他溝通。"
        )
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "案主：我的孩子很叛逆，不知道怎麼管教，也不知道怎麼和他溝通。",
            }
        ]
        db_session.commit()

        session_id = session.id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify suggestions are provided
            assert "suggestions" in data
            assert isinstance(data["suggestions"], list)

            # Verify RAG sources field exists (empty in simplified mode)
            assert "rag_sources" in data
            assert isinstance(data["rag_sources"], list)

    def test_rag_fallback_when_no_relevant_knowledge(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 3: Fallback gracefully when RAG finds no relevant content

        Scenario: Given session with non-parenting topic
        Expected: API should still work, rag_sources can be empty, no crash
        """
        # Update session with non-parenting content
        session = counselor_with_session["session"]
        session.transcript_text = "諮詢師：今天天氣如何？\n案主：天氣很好。"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "諮詢師：今天天氣如何？\n案主：天氣很好。",
            }
        ]
        db_session.commit()

        session_id = session.id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

            # Should still return 200 OK (no crash)
            assert response.status_code == 200
            data = response.json()

            # Should have all required fields
            assert "summary" in data
            assert "alerts" in data
            assert "suggestions" in data
            assert "rag_sources" in data

            # RAG sources can be empty for non-parenting topics
            assert isinstance(data["rag_sources"], list)

    def test_keyword_detection_triggers_analysis(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 4: Deep-analyze works with various parenting keywords

        Scenario: Test multiple parenting keywords: 親子, 孩子, 教養, 溝通, 情緒, 管教
        Expected: All these keywords should be analyzed successfully
        """
        keywords_to_test = [
            ("親子", "我和孩子的親子關係有問題。"),
            ("孩子", "我的孩子不聽話。"),
            ("教養", "教養方式應該如何調整？"),
        ]

        session = counselor_with_session["session"]
        session_id = session.id

        for keyword, text in keywords_to_test:
            # Update session with keyword-specific content
            session.transcript_text = f"案主：{text}"
            session.recordings = [
                {
                    "segment_number": 1,
                    "transcript_text": f"案主：{text}",
                }
            ]
            db_session.commit()

            with TestClient(app) as client:
                response = client.post(
                    f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                    headers=auth_headers,
                )

                assert response.status_code == 200, f"Failed for keyword: {keyword}"
                data = response.json()

                # Should have rag_sources field
                assert (
                    "rag_sources" in data
                ), f"Missing rag_sources for keyword: {keyword}"

                # Should be a list (can be empty if no match, but field must exist)
                assert isinstance(
                    data["rag_sources"], list
                ), f"rag_sources not a list for keyword: {keyword}"

    def test_rag_response_schema_validation(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 5: Validate deep-analyze response schema

        Scenario: Verify response has correct structure
        Expected: Response should include summary, alerts, suggestions, rag_sources, etc.
        """
        session = counselor_with_session["session"]
        session.transcript_text = "案主：我的孩子很叛逆，需要學習親子溝通和管教技巧。"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "案主：我的孩子很叛逆，需要學習親子溝通和管教技巧。",
            }
        ]
        db_session.commit()

        session_id = session.id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify complete response schema
            assert "summary" in data
            assert "alerts" in data
            assert "suggestions" in data
            assert "time_range" in data
            assert "timestamp" in data
            assert "rag_sources" in data
            assert "safety_level" in data
            assert "provider_metadata" in data

            # Verify rag_sources schema
            assert isinstance(data["rag_sources"], list)

            # Verify safety_level is valid
            assert data["safety_level"] in ["green", "yellow", "red"]

            # Verify provider_metadata structure
            assert "latency_ms" in data["provider_metadata"]
            assert data["provider_metadata"]["latency_ms"] >= 0

    def test_deep_analyze_performance(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 6: Verify API performance with deep-analyze

        Scenario: Deep-analyze should respond quickly (mocked)
        Expected: API should respond within reasonable time
        """
        import time

        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            start_time = time.time()

            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

            elapsed_time = time.time() - start_time

            assert response.status_code == 200

            # With mocked service, should be very fast
            # In real scenario with GCP, allow up to 5 seconds
            assert elapsed_time < 5.0, f"API too slow: {elapsed_time:.2f}s"

            data = response.json()
            assert "rag_sources" in data
            assert "provider_metadata" in data
            assert "latency_ms" in data["provider_metadata"]

    def test_rag_sources_always_list(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 7: Verify rag_sources is always a list

        Scenario: rag_sources should always be a list (empty in simplified mode)
        Expected: rag_sources should be an empty list in simplified mode
        """
        session = counselor_with_session["session"]
        session.transcript_text = (
            "案主：我想了解親子溝通、教養方式、情緒管理、管教技巧等所有相關知識。"
        )
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "案主：我想了解親子溝通、教養方式、情緒管理、管教技巧等所有相關知識。",
            }
        ]
        db_session.commit()

        session_id = session.id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert "rag_sources" in data
            assert isinstance(data["rag_sources"], list)

            # In simplified mode (use_rag=False by default), rag_sources is empty
            # This test validates the schema, not RAG functionality

    def test_deep_analyze_safety_level_response(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 8: Verify deep-analyze returns valid safety level

        Scenario: Response should include safety_level field
        Expected: safety_level should be one of: green, yellow, red
        """
        session = counselor_with_session["session"]
        session.transcript_text = "案主：我的孩子很叛逆，需要親子溝通技巧。"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "案主：我的孩子很叛逆，需要親子溝通技巧。",
            }
        ]
        db_session.commit()

        session_id = session.id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?mode=practice",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert "safety_level" in data
            assert data["safety_level"] in ["green", "yellow", "red"]

            # Verify rag_sources exists
            assert "rag_sources" in data
            assert isinstance(data["rag_sources"], list)
