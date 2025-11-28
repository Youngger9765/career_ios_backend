"""Integration tests for real-time transcript keyword analysis API."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.counselor import Counselor


class TestTranscriptKeywordsAPI:
    """Test suite for transcript keyword analysis endpoints"""

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

        # Create token directly
        token_data = {"sub": str(counselor.id), "tenant": counselor.tenant_id}
        token = create_access_token(token_data)
        return {"Authorization": f"Bearer {token}"}

    def test_analyze_transcript_keywords_with_context(
        self, db_session: Session, auth_headers
    ):
        """Test transcript keyword analysis with client and case context."""
        # First create a client
        with TestClient(app) as client_api:
            # Create test client
            client_response = client_api.post(
                "/api/v1/clients",
                headers=auth_headers,
                json={
                    "name": "測試案主",
                    "background": "工作壓力大，情緒困擾",
                    "main_issues": "焦慮、壓力",
                },
            )
            assert client_response.status_code == 201
            client_data = client_response.json()
            client_id = client_data["id"]

            # Create test case
            case_response = client_api.post(
                "/api/v1/cases",
                headers=auth_headers,
                json={
                    "client_id": client_id,
                    "goal": "減輕工作壓力",
                    "expectations": "學習壓力管理技巧",
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
            # Create test client and case first
            client_response = client_api.post(
                "/api/v1/clients", headers=auth_headers, json={"name": "測試案主2"}
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
            # Create test client and case
            client_response = client_api.post(
                "/api/v1/clients", headers=auth_headers, json={"name": "測試案主3"}
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
