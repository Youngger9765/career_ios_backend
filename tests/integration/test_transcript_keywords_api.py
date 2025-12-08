"""Integration tests for real-time transcript keyword analysis API."""
import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor


class TestTranscriptKeywordsAPI:
    """Test suite for transcript keyword analysis endpoints"""

    @pytest.fixture(autouse=True)
    def mock_gemini_service(self):
        """Mock GeminiService for CI environment to avoid needing GCP credentials"""

        async def mock_generate_text(prompt, *args, **kwargs):
            # Return realistic mock response based on prompt content
            if "壓力" in prompt or "焦慮" in prompt:
                return json.dumps(
                    {
                        "keywords": ["壓力", "焦慮", "工作", "主管", "要求"],
                        "categories": ["情緒", "職場", "人際關係"],
                        "confidence": 0.85,
                        "counselor_insights": "案主出現明顯的工作壓力和焦慮情緒，建議探索壓力來源及應對策略。",
                    }
                )
            elif "天氣" in prompt:
                return json.dumps(
                    {
                        "keywords": ["天氣", "公園", "散步"],
                        "categories": ["日常生活", "休閒"],
                        "confidence": 0.7,
                        "counselor_insights": "案主提到日常休閒活動，可以探索生活品質和壓力調節。",
                    }
                )
            elif "成就感" in prompt or "轉職" in prompt:
                return json.dumps(
                    {
                        "keywords": ["成就感", "焦慮", "壓力", "轉職", "失敗"],
                        "categories": ["職涯發展", "情緒", "自我懷疑"],
                        "confidence": 0.9,
                        "counselor_insights": "案主對職涯轉換感到矛盾，同時存在對現狀的不滿和對改變的恐懼。建議探索職涯價值觀和轉職的真實動機。",
                    }
                )
            else:
                return json.dumps(
                    {
                        "keywords": ["測試", "關鍵字"],
                        "categories": ["一般"],
                        "confidence": 0.5,
                        "counselor_insights": "無特定洞見。",
                    }
                )

        # Patch at both import locations (analyze.py and keyword_analysis_service.py)
        with patch("app.api.analyze.GeminiService") as mock_analyze, patch(
            "app.services.keyword_analysis_service.GeminiService"
        ) as mock_kw_service:
            mock_analyze_instance = mock_analyze.return_value
            mock_analyze_instance.generate_text = mock_generate_text

            mock_kw_service_instance = mock_kw_service.return_value
            mock_kw_service_instance.generate_text = mock_generate_text

            yield mock_kw_service_instance

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-keywords@test.com",
            username="keywordscounselor",
            full_name="Keywords Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        # Login to get token (same approach as test_clients_api.py)
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "counselor-keywords@test.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    def test_analyze_transcript_keywords_with_context(
        self, db_session: Session, auth_headers
    ):
        """Test transcript keyword analysis with client and case context."""
        # First create a client
        with TestClient(app) as client_api:
            # Create test client with required fields
            client_response = client_api.post(
                "/api/v1/clients",
                headers=auth_headers,
                json={
                    "name": "測試案主",
                    "email": "test-keywords@example.com",
                    "gender": "男",
                    "birth_date": "1990-01-01",
                    "phone": "0912345678",
                    "identity_option": "在職者",
                    "current_status": "工作壓力大",
                    "notes": "工作壓力大，情緒困擾，焦慮、壓力",
                },
            )
            if client_response.status_code != 201:
                print(f"Client creation failed: {client_response.status_code}")
                print(f"Error: {client_response.json()}")
            assert client_response.status_code == 201
            client_data = client_response.json()
            client_id = client_data["id"]

            # Create test case
            case_response = client_api.post(
                "/api/v1/cases",
                headers=auth_headers,
                json={
                    "client_id": client_id,
                    "goals": "減輕工作壓力",
                    "problem_description": "學習壓力管理技巧",
                },
            )
            assert case_response.status_code == 201
            case_data = case_response.json()
            case_id = case_data["id"]

            # Test keyword analysis
            request_data = {
                "client_id": client_id,
                "case_id": case_id,
                "transcript_segment": "我最近在工作上遇到很多壓力，常常感到焦慮和無助。主管對我的要求越來越高，我不知道該如何應對。",
                "context": {
                    "include_client_profile": True,
                    "include_case_goals": True,
                },
            }

            response = client_api.post(
                "/api/v1/analyze/transcript-keywords",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "keywords" in data
            assert "categories" in data
            assert "confidence" in data
            assert "segment_id" in data

            # Verify data types
            assert isinstance(data["keywords"], list)
            assert isinstance(data["categories"], list)
            assert isinstance(data["confidence"], float)
            assert isinstance(data["segment_id"], str)

            # Verify keywords extraction
            assert len(data["keywords"]) > 0
            assert 0.0 <= data["confidence"] <= 1.0

            # Verify temporary segment_id format (UUID)
            try:
                from uuid import UUID

                UUID(data["segment_id"])
            except ValueError:
                pytest.fail("segment_id is not a valid UUID")

    def test_analyze_transcript_keywords_without_context(
        self, db_session: Session, auth_headers
    ):
        """Test transcript keyword analysis without client/case context."""
        with TestClient(app) as client_api:
            # Create test client and case first with required fields
            client_response = client_api.post(
                "/api/v1/clients",
                headers=auth_headers,
                json={
                    "name": "測試案主2",
                    "email": "test-keywords2@example.com",
                    "gender": "女",
                    "birth_date": "1985-05-15",
                    "phone": "0923456789",
                    "identity_option": "轉職者",
                    "current_status": "轉換跑道中",
                },
            )
            client_id = client_response.json()["id"]

            case_response = client_api.post(
                "/api/v1/cases", headers=auth_headers, json={"client_id": client_id}
            )
            case_id = case_response.json()["id"]

            request_data = {
                "client_id": client_id,
                "case_id": case_id,
                "transcript_segment": "今天天氣很好，我去公園散步了。",
                "context": {
                    "include_client_profile": False,
                    "include_case_goals": False,
                },
            }

            response = client_api.post(
                "/api/v1/analyze/transcript-keywords",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert "keywords" in data
            assert len(data["keywords"]) > 0

    def test_analyze_transcript_keywords_missing_client(
        self, db_session: Session, auth_headers
    ):
        """Test transcript keyword analysis with non-existent client."""
        with TestClient(app) as client_api:
            request_data = {
                "client_id": str(uuid4()),  # Non-existent client
                "case_id": str(uuid4()),
                "transcript_segment": "測試文字",
                "context": {
                    "include_client_profile": True,
                    "include_case_goals": False,
                },
            }

            response = client_api.post(
                "/api/v1/analyze/transcript-keywords",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 404
            assert "Client not found" in response.json()["detail"]

    def test_analyze_transcript_keywords_empty_segment(
        self, db_session: Session, auth_headers
    ):
        """Test transcript keyword analysis with empty transcript segment."""
        with TestClient(app) as client_api:
            # Create test client and case with required fields
            client_response = client_api.post(
                "/api/v1/clients",
                headers=auth_headers,
                json={
                    "name": "測試案主3",
                    "email": "test-keywords3@example.com",
                    "gender": "男",
                    "birth_date": "1995-12-20",
                    "phone": "0934567890",
                    "identity_option": "學生",
                    "current_status": "就學中",
                },
            )
            assert client_response.status_code == 201
            client_id = client_response.json()["id"]

            case_response = client_api.post(
                "/api/v1/cases", headers=auth_headers, json={"client_id": client_id}
            )
            case_id = case_response.json()["id"]

            request_data = {
                "client_id": client_id,
                "case_id": case_id,
                "transcript_segment": "",
                "context": {
                    "include_client_profile": True,
                    "include_case_goals": True,
                },
            }

            response = client_api.post(
                "/api/v1/analyze/transcript-keywords",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 422  # Validation error

    def test_analyze_transcript_keywords_unauthorized(self, db_session: Session):
        """Test transcript keyword analysis without authentication."""
        with TestClient(app) as client_api:
            request_data = {
                "client_id": str(uuid4()),
                "case_id": str(uuid4()),
                "transcript_segment": "測試文字",
                "context": {
                    "include_client_profile": True,
                    "include_case_goals": True,
                },
            }

            response = client_api.post(
                "/api/v1/analyze/transcript-keywords",
                json=request_data,
            )

            assert response.status_code == 403  # Returns 403 Forbidden without auth

    def test_analyze_session_keywords_restful(self, db_session: Session, auth_headers):
        """Test RESTful keyword analysis endpoint using session context."""
        with TestClient(app) as client_api:
            # Create test client
            client_response = client_api.post(
                "/api/v1/clients",
                headers=auth_headers,
                json={
                    "name": "RESTful 測試案主",
                    "email": "restful-test@example.com",
                    "gender": "女",
                    "birth_date": "1992-03-15",
                    "phone": "0945678901",
                    "identity_option": "在職者",
                    "current_status": "職涯轉換困擾",
                    "notes": "考慮轉職，對未來感到迷惘",
                },
            )
            assert client_response.status_code == 201
            client_id = client_response.json()["id"]

            # Create test case
            case_response = client_api.post(
                "/api/v1/cases",
                headers=auth_headers,
                json={
                    "client_id": client_id,
                    "goals": "釐清職涯方向，建立信心",
                    "problem_description": "對當前工作不滿意，想轉換跑道",
                },
            )
            assert case_response.status_code == 201
            case_id = case_response.json()["id"]

            # Create test session
            session_response = client_api.post(
                "/api/v1/sessions",
                headers=auth_headers,
                json={
                    "case_id": case_id,
                    "session_date": "2025-01-20",
                    "transcript": "諮詢師：今天想聊些什麼？\n案主：我最近對工作感到很迷惘...",
                    "notes": "第一次諮詢",
                },
            )
            assert session_response.status_code == 201
            session_id = session_response.json()["id"]

            # Test RESTful keyword analysis endpoint
            request_data = {
                "transcript_segment": "我覺得現在的工作沒有成就感，常常感到焦慮和壓力。我不確定是否該轉職，但又害怕失敗。"
            }

            response = client_api.post(
                f"/api/v1/sessions/{session_id}/analyze-keywords",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "keywords" in data
            assert "categories" in data
            assert "confidence" in data
            assert "counselor_insights" in data

            # Verify data types
            assert isinstance(data["keywords"], list)
            assert isinstance(data["categories"], list)
            assert isinstance(data["confidence"], float)
            assert isinstance(data["counselor_insights"], str)

            # Verify counselor insights are provided
            assert len(data["counselor_insights"]) > 0

            # Verify keywords extraction
            assert len(data["keywords"]) > 0
            assert 0.0 <= data["confidence"] <= 1.0

    def test_analyze_session_keywords_not_found(
        self, db_session: Session, auth_headers
    ):
        """Test RESTful keyword analysis with non-existent session."""
        with TestClient(app) as client_api:
            request_data = {"transcript_segment": "測試文字"}

            response = client_api.post(
                f"/api/v1/sessions/{uuid4()}/analyze-keywords",
                json=request_data,
                headers=auth_headers,
            )

            assert response.status_code == 404
            assert "Session not found" in response.json()["detail"]
