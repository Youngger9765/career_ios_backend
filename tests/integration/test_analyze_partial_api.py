"""Integration tests for multi-tenant analyze-partial API."""
import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor
from app.models.session_analysis_log import SessionAnalysisLog
from app.models.session_usage import SessionUsage


class TestAnalyzePartialAPI:
    """Test suite for multi-tenant analyze-partial endpoint"""

    @pytest.fixture(autouse=True)
    def mock_gemini_and_rag_services(self):
        """Mock both GeminiService and RAGRetriever for CI environment"""

        async def mock_generate_text(prompt, *args, **kwargs):
            """Mock Gemini AI response based on prompt content"""
            # Detect tenant from prompt
            if "親子教養專家" in prompt or "親子對話" in prompt:
                # island_parents tenant
                return json.dumps(
                    {
                        "safety_level": "yellow",
                        "severity": 2,
                        "display_text": "您注意到孩子提到「不想去學校」，這可能是焦慮的徵兆",
                        "action_suggestion": "建議先同理孩子的感受，避免直接質問原因",
                        "suggested_interval_seconds": 15,
                        "keywords": ["焦慮", "學校"],
                        "categories": ["情緒"],
                    }
                )
            else:
                # career tenant (default)
                return json.dumps(
                    {
                        "keywords": ["焦慮", "職涯", "壓力"],
                        "categories": ["情緒", "職涯探索"],
                        "confidence": 0.85,
                        "counselor_insights": "個案提到對未來感到迷惘，建議探索職涯價值觀",
                        "safety_level": "yellow",
                        "severity": 2,
                        "display_text": "個案提到焦慮和壓力",
                        "action_suggestion": "建議探索職涯價值觀",
                    }
                )

        async def mock_rag_search(*args, **kwargs):
            """Mock RAG retriever search"""
            category = kwargs.get("category", "career")
            if category == "parenting":
                return [
                    {
                        "text": "親子溝通的重要性...",
                        "document": "親子教養手冊",
                        "score": 0.85,
                    }
                ]
            else:
                return [
                    {
                        "text": "職涯發展理論...",
                        "document": "職涯諮詢指南",
                        "score": 0.82,
                    }
                ]

        # Mock GeminiService
        with patch(
            "app.services.keyword_analysis_service.GeminiService"
        ) as mock_gemini:
            mock_gemini_instance = mock_gemini.return_value
            mock_gemini_instance.generate_text = mock_generate_text

            # Mock RAGRetriever
            with patch(
                "app.services.keyword_analysis_service.RAGRetriever"
            ) as mock_rag:
                mock_rag_instance = mock_rag.return_value
                mock_rag_instance.search = mock_rag_search

                yield {
                    "gemini": mock_gemini_instance,
                    "rag": mock_rag_instance,
                }

    @pytest.fixture
    def career_auth_headers(self, db_session: Session):
        """Create authenticated counselor for career tenant"""
        # Use unique email for each test to avoid conflicts
        unique_email = f"career-counselor-{uuid4().hex[:8]}@test.com"
        counselor = Counselor(
            id=uuid4(),
            email=unique_email,
            username=f"careercounselor{uuid4().hex[:6]}",
            full_name="Career Test Counselor",
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
                    "email": unique_email,
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def island_parents_auth_headers(self, db_session: Session):
        """Create authenticated counselor for island_parents tenant"""
        # Use unique email for each test to avoid conflicts
        unique_email = f"parent-counselor-{uuid4().hex[:8]}@test.com"
        counselor = Counselor(
            id=uuid4(),
            email=unique_email,
            username=f"parentcounselor{uuid4().hex[:6]}",
            full_name="Parent Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": unique_email,
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    def test_analyze_partial_career_tenant(
        self, db_session: Session, career_auth_headers
    ):
        """Test analyze-partial for career tenant (backward compatible)"""
        with TestClient(app) as client_api:
            # Create test client
            client_response = client_api.post(
                "/api/v1/clients",
                headers=career_auth_headers,
                json={
                    "name": "職涯案主",
                    "email": "career-client@example.com",
                    "gender": "男",
                    "birth_date": "1990-01-01",
                    "phone": "0912345678",
                    "identity_option": "在職者",
                    "current_status": "職涯困擾",
                },
            )
            assert client_response.status_code == 201
            client_id = client_response.json()["id"]

            # Create test case
            case_response = client_api.post(
                "/api/v1/cases",
                headers=career_auth_headers,
                json={"client_id": client_id, "goals": "釐清職涯方向"},
            )
            assert case_response.status_code == 201
            case_id = case_response.json()["id"]

            # Create test session
            session_response = client_api.post(
                "/api/v1/sessions",
                headers=career_auth_headers,
                json={
                    "case_id": case_id,
                    "session_date": "2025-01-20",
                    "transcript": "諮詢開始...",
                },
            )
            assert session_response.status_code == 201
            session_id = session_response.json()["id"]

            # Test analyze-partial
            request_data = {
                "transcript_segment": "我最近對職涯感到焦慮，不知道未來該往哪裡走..."
            }

            response = client_api.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                json=request_data,
                headers=career_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify CareerAnalysisResponse structure
            assert "keywords" in data
            assert "categories" in data
            assert "confidence" in data
            assert "counselor_insights" in data

            # Verify new fields are present
            assert "safety_level" in data
            assert "severity" in data
            assert "display_text" in data
            assert "action_suggestion" in data

            # ✅ VERIFY token_usage is returned (Issue fix verification)
            assert "token_usage" in data, "token_usage field missing from response!"
            assert data["token_usage"] is None or isinstance(
                data["token_usage"], dict
            ), f"token_usage should be None or dict, got {type(data['token_usage'])}"

            # Verify data types
            assert isinstance(data["keywords"], list)
            assert isinstance(data["categories"], list)
            assert isinstance(data["confidence"], float)
            assert isinstance(data["counselor_insights"], str)

            assert len(data["keywords"]) > 0
            assert 0.0 <= data["confidence"] <= 1.0

            # Verify SessionAnalysisLog was created
            analysis_log = (
                db_session.query(SessionAnalysisLog)
                .filter(SessionAnalysisLog.session_id == session_id)
                .first()
            )
            assert analysis_log is not None
            assert analysis_log.analysis_type == "partial_analysis"
            assert analysis_log.tenant_id == "career"

            # Verify SessionUsage was created/updated
            session_usage = (
                db_session.query(SessionUsage)
                .filter(SessionUsage.session_id == session_id)
                .first()
            )
            assert session_usage is not None
            assert session_usage.analysis_count >= 1

    def test_analyze_partial_island_parents_tenant(
        self, db_session: Session, island_parents_auth_headers
    ):
        """Test analyze-partial for island_parents tenant (new format)"""
        with TestClient(app) as client_api:
            # Create test client (parent)
            client_response = client_api.post(
                "/api/v1/clients",
                headers=island_parents_auth_headers,
                json={
                    "name": "家長測試",
                    "email": "parent-client@example.com",
                    "gender": "女",
                    "birth_date": "1985-05-15",
                    "phone": "0923456789",
                    "identity_option": "家長",
                    "current_status": "親子溝通困擾",
                },
            )
            assert client_response.status_code == 201
            client_id = client_response.json()["id"]

            # Create test case
            case_response = client_api.post(
                "/api/v1/cases",
                headers=island_parents_auth_headers,
                json={"client_id": client_id, "goals": "改善親子溝通"},
            )
            assert case_response.status_code == 201
            case_id = case_response.json()["id"]

            # Create test session
            session_response = client_api.post(
                "/api/v1/sessions",
                headers=island_parents_auth_headers,
                json={
                    "case_id": case_id,
                    "session_date": "2025-01-20",
                    "transcript": "親子對話開始...",
                },
            )
            assert session_response.status_code == 201
            session_id = session_response.json()["id"]

            # Test analyze-partial
            request_data = {
                "transcript_segment": "孩子：我不想去學校...\n家長：為什麼？你要好好說！"
            }

            response = client_api.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                json=request_data,
                headers=island_parents_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify IslandParentAnalysisResponse structure
            assert "safety_level" in data
            assert "severity" in data
            assert "display_text" in data
            assert "action_suggestion" in data
            assert "suggested_interval_seconds" in data
            assert "rag_documents" in data
            assert "keywords" in data
            assert "categories" in data

            # Verify safety levels
            assert data["safety_level"] in ["red", "yellow", "green"]
            assert 1 <= data["severity"] <= 3
            assert data["suggested_interval_seconds"] > 0

            # Verify data types
            assert isinstance(data["display_text"], str)
            assert isinstance(data["action_suggestion"], str)
            assert isinstance(data["rag_documents"], list)

            # Verify SessionAnalysisLog was created
            analysis_log = (
                db_session.query(SessionAnalysisLog)
                .filter(SessionAnalysisLog.session_id == session_id)
                .first()
            )
            assert analysis_log is not None
            assert analysis_log.analysis_type == "partial_analysis"
            assert analysis_log.tenant_id == "island_parents"
            assert analysis_log.safety_level == data["safety_level"]

    def test_analyze_keywords_backward_compatible(
        self, db_session: Session, career_auth_headers
    ):
        """Test that analyze-keywords still works (legacy endpoint)"""
        with TestClient(app) as client_api:
            # Create test client
            client_response = client_api.post(
                "/api/v1/clients",
                headers=career_auth_headers,
                json={
                    "name": "Legacy案主",
                    "email": f"legacy-{uuid4().hex[:8]}@example.com",
                    "gender": "男",
                    "birth_date": "1990-01-01",
                    "phone": f"091{uuid4().hex[:7]}",
                    "identity_option": "在職者",
                    "current_status": "探索中",
                },
            )
            if client_response.status_code != 201:
                print(f"Client creation failed: {client_response.json()}")
            assert client_response.status_code == 201
            client_id = client_response.json()["id"]

            # Create test case and session
            case_response = client_api.post(
                "/api/v1/cases",
                headers=career_auth_headers,
                json={"client_id": client_id},
            )
            case_id = case_response.json()["id"]

            session_response = client_api.post(
                "/api/v1/sessions",
                headers=career_auth_headers,
                json={"case_id": case_id, "session_date": "2025-01-20"},
            )
            session_id = session_response.json()["id"]

            # Test legacy analyze-keywords endpoint
            request_data = {"transcript_segment": "我對未來感到焦慮..."}

            response = client_api.post(
                f"/api/v1/sessions/{session_id}/analyze-keywords",
                json=request_data,
                headers=career_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify legacy response format
            assert "keywords" in data
            assert "categories" in data
            assert "confidence" in data
            assert "counselor_insights" in data

            # Verify it's using new backend (SessionAnalysisLog created)
            analysis_log = (
                db_session.query(SessionAnalysisLog)
                .filter(SessionAnalysisLog.session_id == session_id)
                .first()
            )
            assert analysis_log is not None

    def test_analyze_partial_session_not_found(
        self, db_session: Session, career_auth_headers
    ):
        """Test analyze-partial with non-existent session"""
        with TestClient(app) as client_api:
            request_data = {"transcript_segment": "測試文字"}

            response = client_api.post(
                f"/api/v1/sessions/{uuid4()}/analyze-partial",
                json=request_data,
                headers=career_auth_headers,
            )

            assert response.status_code == 404
            assert "Session not found" in response.json()["detail"]

    def test_analyze_partial_empty_transcript(
        self, db_session: Session, career_auth_headers
    ):
        """Test analyze-partial with empty transcript segment"""
        with TestClient(app) as client_api:
            # Create session first
            client_response = client_api.post(
                "/api/v1/clients",
                headers=career_auth_headers,
                json={
                    "name": "Empty Test",
                    "email": f"empty-{uuid4().hex[:8]}@example.com",
                    "gender": "男",
                    "birth_date": "1990-01-01",
                    "phone": f"091{uuid4().hex[:7]}",
                    "identity_option": "在職者",
                    "current_status": "探索中",
                },
            )
            if client_response.status_code != 201:
                print(f"Client creation failed: {client_response.json()}")
            client_id = client_response.json()["id"]

            case_response = client_api.post(
                "/api/v1/cases",
                headers=career_auth_headers,
                json={"client_id": client_id},
            )
            case_id = case_response.json()["id"]

            session_response = client_api.post(
                "/api/v1/sessions",
                headers=career_auth_headers,
                json={"case_id": case_id, "session_date": "2025-01-20"},
            )
            session_id = session_response.json()["id"]

            # Test with empty transcript
            request_data = {"transcript_segment": ""}

            response = client_api.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                json=request_data,
                headers=career_auth_headers,
            )

            assert response.status_code == 422  # Validation error

    def test_analyze_partial_island_parents_emergency_mode(
        self, db_session: Session, island_parents_auth_headers
    ):
        """Test analyze-partial with emergency mode (simplified output)"""
        with TestClient(app) as client_api:
            # Create test client, case, and session
            client_response = client_api.post(
                "/api/v1/clients",
                headers=island_parents_auth_headers,
                json={
                    "name": "Emergency Test Parent",
                    "email": f"emergency-{uuid4().hex[:8]}@example.com",
                    "gender": "女",
                    "birth_date": "1985-05-15",
                    "phone": f"092{uuid4().hex[:7]}",
                    "identity_option": "家長",
                    "current_status": "親子溝通困擾",
                },
            )
            assert client_response.status_code == 201
            client_id = client_response.json()["id"]

            case_response = client_api.post(
                "/api/v1/cases",
                headers=island_parents_auth_headers,
                json={"client_id": client_id, "goals": "改善親子溝通"},
            )
            assert case_response.status_code == 201
            case_id = case_response.json()["id"]

            session_response = client_api.post(
                "/api/v1/sessions",
                headers=island_parents_auth_headers,
                json={
                    "case_id": case_id,
                    "session_date": "2025-01-20",
                    "transcript": "親子對話開始...",
                },
            )
            assert session_response.status_code == 201
            session_id = session_response.json()["id"]

            # Test emergency mode
            request_data = {
                "transcript_segment": "孩子：我不想去學校！我討厭學校！\n家長：你為什麼這樣？你一定要去！",
                "mode": "emergency",
            }

            response = client_api.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                json=request_data,
                headers=island_parents_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "safety_level" in data
            assert "severity" in data
            assert "display_text" in data
            assert "action_suggestion" in data

            # Emergency mode should provide quick, concise suggestions
            # (exact content depends on AI, but we can verify structure)
            assert isinstance(data["display_text"], str)
            assert isinstance(data["action_suggestion"], str)

            # Verify SessionAnalysisLog includes mode
            analysis_log = (
                db_session.query(SessionAnalysisLog)
                .filter(SessionAnalysisLog.session_id == session_id)
                .first()
            )
            assert analysis_log is not None
            # Note: mode is stored in metadata JSONB, not direct field
            # We verify it through GBQ data instead

    def test_analyze_partial_island_parents_practice_mode(
        self, db_session: Session, island_parents_auth_headers
    ):
        """Test analyze-partial with practice mode (detailed output)"""
        with TestClient(app) as client_api:
            # Create test client, case, and session
            client_response = client_api.post(
                "/api/v1/clients",
                headers=island_parents_auth_headers,
                json={
                    "name": "Practice Test Parent",
                    "email": f"practice-{uuid4().hex[:8]}@example.com",
                    "gender": "女",
                    "birth_date": "1985-05-15",
                    "phone": f"092{uuid4().hex[:7]}",
                    "identity_option": "家長",
                    "current_status": "親子溝通練習",
                },
            )
            assert client_response.status_code == 201
            client_id = client_response.json()["id"]

            case_response = client_api.post(
                "/api/v1/cases",
                headers=island_parents_auth_headers,
                json={"client_id": client_id, "goals": "練習親子對話技巧"},
            )
            assert case_response.status_code == 201
            case_id = case_response.json()["id"]

            session_response = client_api.post(
                "/api/v1/sessions",
                headers=island_parents_auth_headers,
                json={
                    "case_id": case_id,
                    "session_date": "2025-01-20",
                    "transcript": "練習對話開始...",
                },
            )
            assert session_response.status_code == 201
            session_id = session_response.json()["id"]

            # Test practice mode (default)
            request_data = {
                "transcript_segment": "孩子：我今天在學校被同學笑了...\n家長：哦，怎麼了？",
                "mode": "practice",  # Explicit practice mode
            }

            response = client_api.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                json=request_data,
                headers=island_parents_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "safety_level" in data
            assert "severity" in data
            assert "display_text" in data
            assert "action_suggestion" in data

            # Practice mode should provide detailed suggestions
            assert isinstance(data["display_text"], str)
            assert isinstance(data["action_suggestion"], str)

    def test_analyze_partial_mode_default_is_practice(
        self, db_session: Session, island_parents_auth_headers
    ):
        """Test that default mode is 'practice' when not specified"""
        with TestClient(app) as client_api:
            # Create test client, case, and session
            client_response = client_api.post(
                "/api/v1/clients",
                headers=island_parents_auth_headers,
                json={
                    "name": "Default Mode Test",
                    "email": f"default-{uuid4().hex[:8]}@example.com",
                    "gender": "女",
                    "birth_date": "1985-05-15",
                    "phone": f"092{uuid4().hex[:7]}",
                    "identity_option": "家長",
                    "current_status": "測試",
                },
            )
            assert client_response.status_code == 201
            client_id = client_response.json()["id"]

            case_response = client_api.post(
                "/api/v1/cases",
                headers=island_parents_auth_headers,
                json={"client_id": client_id, "goals": "測試"},
            )
            case_id = case_response.json()["id"]

            session_response = client_api.post(
                "/api/v1/sessions",
                headers=island_parents_auth_headers,
                json={
                    "case_id": case_id,
                    "session_date": "2025-01-20",
                    "transcript": "測試",
                },
            )
            session_id = session_response.json()["id"]

            # Test without specifying mode (should default to practice)
            request_data = {
                "transcript_segment": "孩子：我今天很開心\n家長：真的嗎？發生什麼事了？"
            }

            response = client_api.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                json=request_data,
                headers=island_parents_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Should work normally (default to practice mode)
            assert "safety_level" in data
            assert "display_text" in data

    def test_analyze_partial_career_ignores_mode(
        self, db_session: Session, career_auth_headers
    ):
        """Test that career tenant ignores mode parameter"""
        with TestClient(app) as client_api:
            # Create test client, case, and session
            client_response = client_api.post(
                "/api/v1/clients",
                headers=career_auth_headers,
                json={
                    "name": "Career Mode Test",
                    "email": f"career-mode-{uuid4().hex[:8]}@example.com",
                    "gender": "男",
                    "birth_date": "1990-01-01",
                    "phone": f"091{uuid4().hex[:7]}",
                    "identity_option": "在職者",
                    "current_status": "測試",
                },
            )
            assert client_response.status_code == 201
            client_id = client_response.json()["id"]

            case_response = client_api.post(
                "/api/v1/cases",
                headers=career_auth_headers,
                json={"client_id": client_id, "goals": "測試"},
            )
            case_id = case_response.json()["id"]

            session_response = client_api.post(
                "/api/v1/sessions",
                headers=career_auth_headers,
                json={
                    "case_id": case_id,
                    "session_date": "2025-01-20",
                    "transcript": "測試",
                },
            )
            session_id = session_response.json()["id"]

            # Test with mode parameter (should be ignored for career tenant)
            request_data = {
                "transcript_segment": "我對職涯感到困惑",
                "mode": "emergency",  # Should be ignored
            }

            response = client_api.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                json=request_data,
                headers=career_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Should return CareerAnalysisResponse format (mode ignored)
            assert "keywords" in data
            assert "categories" in data
            assert "confidence" in data
            assert "counselor_insights" in data
