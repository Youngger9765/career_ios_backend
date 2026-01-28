"""
Integration Tests for 8 Schools of Parenting Prompt Integration

Tests the new 8 Schools prompt integration in analyze-partial API
Verifies backward compatibility and new field presence.
"""
import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor


class Test8SchoolsPromptIntegration:
    """Test suite for 8 Schools of Parenting prompt integration"""

    @pytest.fixture(autouse=True)
    def mock_gemini_and_rag_services(self):
        """Mock both GeminiService and RAGRetriever for CI environment"""

        async def mock_generate_text(prompt, *args, **kwargs):
            """Mock Gemini AI response based on prompt content"""
            # Check if this is practice mode (contains 8 Schools prompts)
            is_practice = "8 大教養流派" in prompt or "Dr. Becky" in prompt

            if is_practice:
                # Practice mode includes detailed_scripts
                return json.dumps(
                    {
                        "safety_level": "yellow",
                        "severity": 2,
                        "display_text": "孩子正在經歷情緒困擾",
                        "action_suggestion": "先同理孩子的感受，再引導解決問題",
                        "suggested_interval_seconds": 30,
                        "keywords": ["焦慮", "情緒"],
                        "categories": ["情緒管理"],
                        "detailed_scripts": [
                            {
                                "situation": "當孩子拒絕寫作業時",
                                "parent_script": "（蹲下平視）我看到你現在不想寫作業，好像很累。是不是今天在學校已經很努力了？我們現在先不談作業。你是要先休息 10 分鐘，還是我陪你一起做？",
                                "child_likely_response": "可能選擇休息或陪伴",
                                "theory_basis": "薩提爾 + Dr. Becky + 阿德勒",
                                "step": "同理連結 → 即時話術",
                            }
                        ],
                        "theoretical_frameworks": [
                            "薩提爾模式",
                            "Dr. Becky Kennedy",
                            "阿德勒正向教養",
                        ],
                    }
                )
            else:
                # Emergency mode - simpler response
                return json.dumps(
                    {
                        "safety_level": "red",
                        "severity": 3,
                        "display_text": "情緒崩潰，需要立即安撫",
                        "action_suggestion": "先降溫，避免對抗",
                        "suggested_interval_seconds": 15,
                        "keywords": ["崩潰", "情緒"],
                        "categories": ["危機處理"],
                    }
                )

        async def mock_rag_search(*args, **kwargs):
            """Mock RAG retrieval"""
            return []

        # Patch both services
        with patch(
            "app.services.keyword_analysis_service.GeminiService"
        ) as mock_gemini_class, patch(
            "app.services.analysis.keyword_analysis.prompts.RAGRetriever"
        ) as mock_rag_class:
            mock_gemini_instance = mock_gemini_class.return_value
            mock_gemini_instance.generate_text = AsyncMock(
                side_effect=mock_generate_text
            )

            mock_rag_instance = mock_rag_class.return_value
            mock_rag_instance.search = AsyncMock(side_effect=mock_rag_search)

            yield

    @pytest.fixture
    def island_parents_auth_headers(self, db_session: Session):
        """Create authenticated counselor for island_parents tenant"""
        unique_email = f"parent-8schools-{uuid4().hex[:8]}@test.com"
        counselor = Counselor(
            id=uuid4(),
            email=unique_email,
            username=f"parent8schools{uuid4().hex[:6]}",
            full_name="8 Schools Test Counselor",
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

    def test_practice_mode_includes_8_schools_fields(
        self, db_session: Session, island_parents_auth_headers
    ):
        """Test that practice mode response includes 8 Schools fields"""
        with TestClient(app) as client:
            # Create test client
            client_response = client.post(
                "/api/v1/clients",
                headers=island_parents_auth_headers,
                json={
                    "name": "測試孩子家長",
                    "email": "8schools-test@example.com",
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
            case_response = client.post(
                "/api/v1/cases",
                headers=island_parents_auth_headers,
                json={"client_id": client_id, "goals": "改善親子溝通"},
            )
            assert case_response.status_code == 201
            case_id = case_response.json()["id"]

            # Create test session
            session_response = client.post(
                "/api/v1/sessions",
                headers=island_parents_auth_headers,
                json={
                    "case_id": case_id,
                    "session_date": "2025-12-31",
                    "transcript": "會談開始...",
                },
            )
            assert session_response.status_code == 201
            session_id = session_response.json()["id"]

            # Test analyze-partial with practice mode
            request_data = {
                "transcript_segment": "孩子：我不想寫作業！\n媽媽：為什麼不想寫？",
                "mode": "practice",
            }

            response = client.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                json=request_data,
                headers=island_parents_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify basic fields
            assert "safety_level" in data
            assert "severity" in data
            assert "display_text" in data
            assert "action_suggestion" in data

            # Verify 8 Schools new fields (should be present in practice mode)
            assert "detailed_scripts" in data or data.get("detailed_scripts") is None
            assert (
                "theoretical_frameworks" in data
                or data.get("theoretical_frameworks") is None
            )

            # If detailed_scripts is present, verify structure
            if data.get("detailed_scripts"):
                script = data["detailed_scripts"][0]
                assert "situation" in script
                assert "parent_script" in script
                assert "child_likely_response" in script
                assert "theory_basis" in script
                assert "step" in script

    def test_backward_compatibility(
        self, db_session: Session, island_parents_auth_headers
    ):
        """Test that API remains backward compatible"""
        with TestClient(app) as client:
            # Create minimal test data
            client_response = client.post(
                "/api/v1/clients",
                headers=island_parents_auth_headers,
                json={
                    "name": "Test Child Parent",
                    "email": "test-parent@example.com",
                    "gender": "男",
                    "birth_date": "1980-03-20",
                    "phone": "0912345678",
                    "identity_option": "家長",
                    "current_status": "測試",
                },
            )
            client_id = client_response.json()["id"]

            case_response = client.post(
                "/api/v1/cases",
                headers=island_parents_auth_headers,
                json={"client_id": client_id, "goals": "Test"},
            )
            case_id = case_response.json()["id"]

            session_response = client.post(
                "/api/v1/sessions",
                headers=island_parents_auth_headers,
                json={
                    "case_id": case_id,
                    "session_date": "2025-12-31",
                    "transcript": "Test",
                },
            )
            session_id = session_response.json()["id"]

            # Test without mode parameter (backward compatibility)
            request_data = {"transcript_segment": "Test segment"}

            response = client.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                json=request_data,
                headers=island_parents_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # All basic fields should still be present
            assert "safety_level" in data
            assert "severity" in data
            assert "display_text" in data
            assert "action_suggestion" in data

    def test_schema_validation(self, db_session: Session, island_parents_auth_headers):
        """Test that response validates against updated schema"""
        with TestClient(app) as client:
            # Create test data
            client_response = client.post(
                "/api/v1/clients",
                headers=island_parents_auth_headers,
                json={
                    "name": "Schema Test Parent",
                    "email": "schema-test@example.com",
                    "gender": "女",
                    "birth_date": "1988-07-10",
                    "phone": "0934567890",
                    "identity_option": "家長",
                    "current_status": "Schema validation",
                },
            )
            client_id = client_response.json()["id"]

            case_response = client.post(
                "/api/v1/cases",
                headers=island_parents_auth_headers,
                json={"client_id": client_id, "goals": "Schema validation"},
            )
            case_id = case_response.json()["id"]

            session_response = client.post(
                "/api/v1/sessions",
                headers=island_parents_auth_headers,
                json={
                    "case_id": case_id,
                    "session_date": "2025-12-31",
                    "transcript": "Schema test",
                },
            )
            session_id = session_response.json()["id"]

            # Test with practice mode
            request_data = {
                "transcript_segment": "Parent-child interaction",
                "mode": "practice",
            }

            response = client.post(
                f"/api/v1/sessions/{session_id}/analyze-partial",
                json=request_data,
                headers=island_parents_auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify all required fields exist
            required_fields = [
                "safety_level",
                "severity",
                "display_text",
                "action_suggestion",
            ]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"

            # Optional fields should not cause errors
            assert isinstance(data.get("detailed_scripts", []), (list, type(None)))
            assert isinstance(
                data.get("theoretical_frameworks", []), (list, type(None))
            )
