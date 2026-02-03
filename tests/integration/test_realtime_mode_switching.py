"""
Integration tests for Realtime Mode Switching and Risk Level Indicators
Migrated to use session-based endpoint: POST /api/v1/sessions/{session_id}/deep-analyze
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


class TestRealtimeModeSwitching:
    """Test mode switching (emergency vs practice) for realtime counseling"""

    @pytest.fixture
    def mock_gemini_service(self):
        """Mock GeminiService to return mode-appropriate responses"""

        async def mock_generate_text(prompt, *args, **kwargs):
            # Check for emergency mode indicators in prompt
            if "Emergency Mode" in prompt or "即時介入" in prompt:
                return json.dumps(
                    {
                        "safety_level": "yellow",
                        "display_text": "注意情緒",
                        "quick_suggestion": "深呼吸",
                    }
                )
            else:
                # Practice mode: more detailed response
                return json.dumps(
                    {
                        "safety_level": "green",
                        "display_text": "練習語氣溫和，持續觀察孩子的反應，可以嘗試更多同理心表達。這是一個很好的練習機會。",
                        "quick_suggestion": "你正在用心聆聽，繼續保持這樣的態度。孩子需要感受到被理解。",
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
            email="mode-switch-test@test.com",
            username="modeswitchcounselor",
            full_name="Mode Switch Test Counselor",
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
            code="MODE-TEST-001",
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
            case_number="MODE-CASE-001",
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
            transcript_text="家長：我要打死你！你給我滾出去！我受夠了！",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：我要打死你！你給我滾出去！我受夠了！",
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
                    "email": "mode-switch-test@test.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_emergency_mode_returns_simplified_response(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 1: Emergency mode should return ≤2 sentences per suggestion

        Scenario: Given session_mode="emergency"
        Expected: Each suggestion should be ≤2 sentences (simplified for urgent situations)
        """
        session_id = counselor_with_session["session"].id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "summary" in data
        assert "alerts" in data
        assert "suggestions" in data
        assert "safety_level" in data  # Risk level field

        # Verify suggestions are simplified (≤2 sentences each)
        for suggestion in data["suggestions"]:
            # Count sentences (simplified: count periods, question marks, exclamations)
            sentence_count = (
                suggestion.count("。") + suggestion.count("？") + suggestion.count("！")
            )
            assert (
                sentence_count <= 2
            ), f"Emergency mode suggestion too long: {suggestion}"

        # Verify summary is concise (≤2 sentences)
        summary_sentence_count = (
            data["summary"].count("。")
            + data["summary"].count("？")
            + data["summary"].count("！")
        )
        assert (
            summary_sentence_count <= 2
        ), f"Emergency mode summary too long: {data['summary']}"

    def test_practice_mode_returns_detailed_response(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 2: Practice mode should return detailed analysis

        Scenario: Given session_mode="practice" (or no mode = default)
        Expected: Detailed format with comprehensive suggestions
        """
        # Update session transcript for practice mode
        session = counselor_with_session["session"]
        session.transcript_text = (
            "家長：寶貝，我們一起想想怎麼做好嗎？我知道你也覺得很難。"
        )
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "家長：寶貝，我們一起想想怎麼做好嗎？我知道你也覺得很難。",
            }
        ]
        db_session.commit()

        session_id = session.id

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "summary" in data
        assert "alerts" in data
        assert "suggestions" in data
        assert "safety_level" in data

        # Verify detailed format (more comprehensive)
        # Practice mode should have at least some content
        assert len(data["summary"]) > 0, "Practice mode should have a summary"

    def test_default_mode_is_practice(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 3: Default mode should be 'practice' when mode is not specified

        Scenario: Given no mode query param in request
        Expected: Should default to practice mode with detailed analysis
        """
        # Update session transcript
        session = counselor_with_session["session"]
        session.transcript_text = "家長：我們今天學到很多，謝謝你的配合。"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "家長：我們今天學到很多，謝謝你的配合。",
            }
        ]
        db_session.commit()

        session_id = session.id

        with TestClient(app) as client:
            # No mode param - should default to practice
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Should return response (practice mode default)
        assert "summary" in data
        assert "suggestions" in data


class TestRiskLevelIndicators:
    """Test risk level assessment (red/yellow/green) for realtime counseling"""

    @pytest.fixture
    def mock_gemini_service_with_risk(self):
        """Mock GeminiService to return risk-level-appropriate responses based on transcript"""

        async def mock_generate_text(prompt, *args, **kwargs):
            # Detect violent language for red level
            if "打死" in prompt or "滾出去" in prompt or "受不了" in prompt:
                return json.dumps(
                    {
                        "safety_level": "red",
                        "display_text": "偵測到暴力語言，需要立即關注",
                        "quick_suggestion": "深呼吸，先離開現場",
                    }
                )
            # Detect escalating conflict for yellow level
            elif "氣死" in prompt or "不聽話" in prompt or "煩死" in prompt:
                return json.dumps(
                    {
                        "safety_level": "yellow",
                        "display_text": "情緒升高中，建議放慢節奏",
                        "quick_suggestion": "暫停一下，讓雙方冷靜",
                    }
                )
            # Positive interaction for green level
            else:
                return json.dumps(
                    {
                        "safety_level": "green",
                        "display_text": "溝通氣氛良好",
                        "quick_suggestion": "繼續保持這樣的態度",
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
            email="risk-level-test@test.com",
            username="risklevelcounselor",
            full_name="Risk Level Test Counselor",
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
            code="RISK-TEST-001",
            name="測試家長",
            email="parent-risk@test.com",
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
            case_number="RISK-CASE-001",
            goals="改善親子溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Create session with default transcript
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長：測試對話內容",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：測試對話內容",
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
                    "email": "risk-level-test@test.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_safety_level_red_for_violent_language(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service_with_risk,
    ):
        """Test 4: Violent language should trigger RED risk level

        Scenario: Transcript contains violent language: "我要打死你！滾出去！"
        Expected: safety_level == "red"
        """
        # Update transcript with violent language
        session = counselor_with_session["session"]
        session.transcript_text = "家長：我要打死你！你給我滾出去！我快受不了了！"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "家長：我要打死你！你給我滾出去！我快受不了了！",
            }
        ]
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify safety_level field exists
        assert "safety_level" in data

        # Should be RED for violent language
        assert (
            data["safety_level"] == "red"
        ), f"Expected 'red' but got '{data['safety_level']}'"

    def test_safety_level_yellow_for_escalating_conflict(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service_with_risk,
    ):
        """Test 5: Escalating conflict should trigger YELLOW risk level

        Scenario: Transcript shows escalating emotions: "你怎麼又不聽話！我快氣死了！"
        Expected: safety_level == "yellow"
        """
        # Update transcript with escalating conflict
        session = counselor_with_session["session"]
        session.transcript_text = "家長：你怎麼又把房間弄亂！你說謊！我快氣死了！"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "家長：你怎麼又把房間弄亂！你說謊！我快氣死了！",
            }
        ]
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify safety_level field exists
        assert "safety_level" in data

        # Should be YELLOW for escalating conflict
        assert (
            data["safety_level"] == "yellow"
        ), f"Expected 'yellow' but got '{data['safety_level']}'"

    def test_safety_level_green_for_positive_interaction(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service_with_risk,
    ):
        """Test 6: Positive interaction should trigger GREEN risk level

        Scenario: Transcript shows calm, positive interaction: "寶貝，我們一起收拾好嗎？"
        Expected: safety_level == "green"
        """
        # Update transcript with positive interaction
        session = counselor_with_session["session"]
        session.transcript_text = (
            "家長：寶貝，我們一起收拾好嗎？我知道你累了，我們慢慢來。"
        )
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "家長：寶貝，我們一起收拾好嗎？我知道你累了，我們慢慢來。",
            }
        ]
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify safety_level field exists
        assert "safety_level" in data

        # Should be GREEN for positive interaction
        assert (
            data["safety_level"] == "green"
        ), f"Expected 'green' but got '{data['safety_level']}'"

    def test_safety_level_red_for_extreme_emotions(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service_with_risk,
    ):
        """Test 7: Extreme emotions should trigger RED risk level

        Scenario: Multiple red flag keywords: "恨死", "受不了", "不想活"
        Expected: safety_level == "red"
        """
        # Update transcript with extreme emotions
        session = counselor_with_session["session"]
        session.transcript_text = "家長：我恨死這樣的生活了，我真的受不了了！"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "家長：我恨死這樣的生活了，我真的受不了了！",
            }
        ]
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        assert "safety_level" in data
        assert (
            data["safety_level"] == "red"
        ), f"Expected 'red' but got '{data['safety_level']}'"

    def test_safety_level_yellow_for_frustration(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service_with_risk,
    ):
        """Test 8: Frustration without violence should trigger YELLOW

        Scenario: Frustrated but not violent: "你不聽話", "煩死了"
        Expected: safety_level == "yellow"
        """
        # Update transcript with frustration
        session = counselor_with_session["session"]
        session.transcript_text = "家長：你怎麼又不聽話！我真的快煩死了！"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "家長：你怎麼又不聽話！我真的快煩死了！",
            }
        ]
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        assert "safety_level" in data
        assert (
            data["safety_level"] == "yellow"
        ), f"Expected 'yellow' but got '{data['safety_level']}'"


class TestSchemaValidation:
    """Test schema validation for mode and safety_level fields"""

    @pytest.fixture
    def mock_gemini_service(self):
        """Mock GeminiService to return valid responses"""

        async def mock_generate_text(prompt, *args, **kwargs):
            return json.dumps(
                {
                    "safety_level": "green",
                    "display_text": "分析完成",
                    "quick_suggestion": "繼續保持",
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
            email="schema-test@test.com",
            username="schemacounselor",
            full_name="Schema Test Counselor",
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
            code="SCHEMA-TEST-001",
            name="測試家長",
            email="parent-schema@test.com",
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
            case_number="SCHEMA-CASE-001",
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
            transcript_text="家長：今天天氣不錯。",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：今天天氣不錯。",
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
                    "email": "schema-test@test.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_schema_validation_mode_field_emergency(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 9: Verify mode field accepts 'emergency'

        Scenario: POST with session_mode="emergency"
        Expected: Should accept and process correctly
        """
        session = counselor_with_session["session"]
        session.transcript_text = "家長：我需要立即的建議！"
        session.recordings = [
            {"segment_number": 1, "transcript_text": "家長：我需要立即的建議！"}
        ]
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=emergency",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "safety_level" in data

    def test_schema_validation_mode_field_practice(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 10: Verify mode field accepts 'practice'

        Scenario: POST with session_mode="practice"
        Expected: Should accept and process correctly
        """
        session = counselor_with_session["session"]
        session.transcript_text = "家長：我想學習更好的親子溝通方式。"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "家長：我想學習更好的親子溝通方式。",
            }
        ]
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "safety_level" in data

    def test_schema_validation_invalid_mode_accepted(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 11: Verify invalid mode is handled gracefully

        NOTE: The endpoint accepts session_mode as a string query param without
        strict validation, so it will process with the provided value or default.
        This test verifies the endpoint doesn't crash with unusual mode values.
        """
        session = counselor_with_session["session"]
        session.transcript_text = "家長：測試"
        session.recordings = [{"segment_number": 1, "transcript_text": "家長：測試"}]
        db_session.commit()

        with TestClient(app) as client:
            # Invalid mode - should still process (mode is just a string param)
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=invalid_mode",
                headers=auth_headers,
            )

        # Should process without error (mode is not strictly validated at API level)
        assert response.status_code == 200

    def test_schema_validation_safety_level_in_response(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 12: Verify response includes safety_level field

        Scenario: Any valid POST request
        Expected: Response must include safety_level field with value in ["red", "yellow", "green"]
        """
        session = counselor_with_session["session"]

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify safety_level field exists
        assert "safety_level" in data, "Response missing 'safety_level' field"

        # Verify safety_level has valid value
        assert data["safety_level"] in [
            "red",
            "yellow",
            "green",
        ], f"Invalid safety_level: {data['safety_level']}"

    def test_complete_response_schema(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service,
    ):
        """Test 13: Verify complete response schema with all new fields

        Scenario: Verify response includes all required fields including new ones
        Expected: Response should have summary, alerts, suggestions, safety_level, etc.
        """
        session = counselor_with_session["session"]
        session.transcript_text = "家長：我快受不了了！"
        session.recordings = [
            {"segment_number": 1, "transcript_text": "家長：我快受不了了！"}
        ]
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=emergency",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
        required_fields = [
            "summary",
            "alerts",
            "suggestions",
            "time_range",
            "timestamp",
            "safety_level",
        ]

        for field in required_fields:
            assert field in data, f"Response missing required field: {field}"

        # Verify types
        assert isinstance(data["summary"], str)
        assert isinstance(data["alerts"], list)
        assert isinstance(data["suggestions"], list)
        assert isinstance(data["safety_level"], str)
        assert data["safety_level"] in ["red", "yellow", "green"]


class TestModeSwitchingWithRiskLevel:
    """Test interaction between mode switching and risk level"""

    @pytest.fixture
    def mock_gemini_service_combined(self):
        """Mock GeminiService to return mode and risk-appropriate responses"""

        async def mock_generate_text(prompt, *args, **kwargs):
            is_emergency = "Emergency Mode" in prompt or "即時介入" in prompt

            # Check for violent language
            if "打死" in prompt or "滾開" in prompt or "受夠" in prompt:
                if is_emergency:
                    return json.dumps(
                        {
                            "safety_level": "red",
                            "display_text": "需要冷靜",
                            "quick_suggestion": "深呼吸",
                        }
                    )
                else:
                    return json.dumps(
                        {
                            "safety_level": "red",
                            "display_text": "偵測到高風險語言，需要立即關注",
                            "quick_suggestion": "建議先離開現場冷靜，等情緒平復後再繼續",
                        }
                    )
            else:
                if is_emergency:
                    return json.dumps(
                        {
                            "safety_level": "green",
                            "display_text": "氣氛良好",
                            "quick_suggestion": "繼續",
                        }
                    )
                else:
                    return json.dumps(
                        {
                            "safety_level": "green",
                            "display_text": "溝通氣氛良好，展現同理心和耐心，值得肯定",
                            "quick_suggestion": "你正在用心聆聽孩子，這是很棒的親子互動方式",
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
            email="combined-test@test.com",
            username="combinedcounselor",
            full_name="Combined Test Counselor",
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
            code="COMBINED-TEST-001",
            name="測試家長",
            email="parent-combined@test.com",
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
            case_number="COMBINED-CASE-001",
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
            transcript_text="家長：測試內容",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：測試內容",
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
                    "email": "combined-test@test.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_emergency_mode_with_red_safety_level(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service_combined,
    ):
        """Test 14: Emergency mode + RED risk should provide urgent, simplified guidance

        Scenario: session_mode="emergency" + violent language (red risk)
        Expected: Simplified response with high urgency
        """
        session = counselor_with_session["session"]
        session.transcript_text = "家長：我要打死他！我受夠了！滾開！"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "家長：我要打死他！我受夠了！滾開！",
            }
        ]
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=emergency",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Should be RED risk
        assert data["safety_level"] == "red"

        # Should have simplified emergency response
        for suggestion in data["suggestions"]:
            sentence_count = (
                suggestion.count("。") + suggestion.count("？") + suggestion.count("！")
            )
            assert sentence_count <= 2

    def test_practice_mode_with_green_safety_level(
        self,
        db_session: Session,
        auth_headers,
        counselor_with_session,
        mock_gemini_service_combined,
    ):
        """Test 15: Practice mode + GREEN risk should provide detailed learning guidance

        Scenario: session_mode="practice" + positive interaction (green risk)
        Expected: Detailed response with learning focus
        """
        session = counselor_with_session["session"]
        session.transcript_text = "家長：寶貝，我們一起想想怎麼解決這個問題好嗎？"
        session.recordings = [
            {
                "segment_number": 1,
                "transcript_text": "家長：寶貝，我們一起想想怎麼解決這個問題好嗎？",
            }
        ]
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Should be GREEN risk
        assert data["safety_level"] == "green"

        # Should have detailed practice response (suggestions should have content)
        assert len(data["suggestions"]) >= 1
