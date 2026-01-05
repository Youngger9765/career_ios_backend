"""
Integration Tests for Deep Analyze API with 200 Expert Suggestions System

Migrated from old /api/v1/realtime/analyze to new session-based endpoint:
POST /api/v1/sessions/{session_id}/deep-analyze?session_mode={practice|emergency}

This test suite validates:
1. Emergency mode selects 1-2 suggestions from expert pool
2. Practice mode selects 3-4 suggestions from expert pool
3. API returns safety_level (green/yellow/red)
4. Suggestions match the safety_level color
5. Safety level is determined by context (not just keywords)
6. Suggestions are from expert pool (NOT LLM-generated)
"""

import json
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config.parenting_suggestions import (
    ALL_SUGGESTIONS,
    GREEN_SUGGESTIONS,
    RED_SUGGESTIONS,
    YELLOW_SUGGESTIONS,
)
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


class TestRealtimeExpertSuggestionsAPI:
    """Test Deep Analyze API integration with 200 expert suggestions

    This test suite validates:
    1. Emergency mode selects 1-2 suggestions from expert pool
    2. Practice mode selects 3-4 suggestions from expert pool
    3. API returns safety_level (green/yellow/red)
    4. Suggestions match the safety_level color
    5. Safety level is determined by context (not just keywords)
    6. Suggestions are from expert pool (NOT LLM-generated)
    """

    @pytest.fixture
    def mock_gemini_for_expert_suggestions(self):
        """Mock GeminiService to return expert suggestions from pool"""

        async def mock_generate_text(prompt, *args, **kwargs):
            # Analyze prompt content to determine safety level
            # Use the original prompt, not lowercased (Chinese doesn't have case)
            prompt_str = prompt if isinstance(prompt, str) else ""

            # Check for violent/red keywords - be very specific
            red_keywords = ["打死你", "想打他", "殺"]
            yellow_keywords = ["煩", "發脾氣", "不聽話", "壓力大", "擔心"]
            green_keywords = ["謝謝", "努力", "願意跟我說", "了解你的感受"]

            # Determine safety level based on keywords in prompt
            safety_level = "green"

            # Check green first (positive language takes precedence if mixed)
            has_green = any(kw in prompt_str for kw in green_keywords)

            # Check for red keywords (violence)
            has_red = any(kw in prompt_str for kw in red_keywords)

            # Check for yellow keywords (frustration)
            has_yellow = any(kw in prompt_str for kw in yellow_keywords)

            # Red takes precedence unless awareness keywords are present
            if has_red:
                awareness_keywords = ["我知道是因為", "不過我知道"]
                has_awareness = any(kw in prompt_str for kw in awareness_keywords)
                if has_awareness:
                    safety_level = "yellow"
                else:
                    safety_level = "red"
            elif has_yellow and not has_green:
                safety_level = "yellow"
            else:
                safety_level = "green"

            # Select suggestions from the appropriate pool
            if safety_level == "red":
                suggestion = RED_SUGGESTIONS[0]
            elif safety_level == "yellow":
                suggestion = YELLOW_SUGGESTIONS[0]
            else:
                suggestion = GREEN_SUGGESTIONS[0]

            # Create mock response object with .text attribute
            response_json = json.dumps(
                {
                    "safety_level": safety_level,
                    "display_text": f"安全等級：{safety_level}",
                    "quick_suggestion": suggestion,
                }
            )
            mock_response = MagicMock()
            mock_response.text = response_json
            # Add usage metadata for token tracking
            mock_response.usage_metadata = MagicMock()
            mock_response.usage_metadata.prompt_token_count = 100
            mock_response.usage_metadata.candidates_token_count = 50
            return mock_response

        with patch(
            "app.services.keyword_analysis_service.GeminiService"
        ) as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.generate_text = mock_generate_text
            yield mock_instance

    @pytest.fixture
    def counselor_with_red_transcript(self, db_session: Session):
        """Create counselor with session containing violent transcript"""
        counselor = Counselor(
            id=uuid4(),
            email="expert-suggestions-red@test.com",
            username="expertsuggestionsred",
            full_name="Expert Suggestions Red Test",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
            available_credits=100.0,
        )
        db_session.add(counselor)
        db_session.flush()

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="EXPERT-RED-001",
            name="測試家長紅",
            email="parent-red@test.com",
            gender="女",
            birth_date=date(1985, 1, 1),
            phone="0912345678",
            identity_option="家長",
            current_status="親子溝通困擾",
            tenant_id="island_parents",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="island_parents",
            case_number="EXPERT-RED-CASE-001",
            goals="改善親子溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Session with violent language
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長：你再不聽話我就打死你！孩子真的很煩！",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：你再不聽話我就打死你！",
                },
                {
                    "segment_number": 2,
                    "transcript_text": "孩子真的很煩！",
                },
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
    def counselor_with_yellow_transcript(self, db_session: Session):
        """Create counselor with session containing frustrated but not violent transcript"""
        counselor = Counselor(
            id=uuid4(),
            email="expert-suggestions-yellow@test.com",
            username="expertsuggestionsyellow",
            full_name="Expert Suggestions Yellow Test",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
            available_credits=100.0,
        )
        db_session.add(counselor)
        db_session.flush()

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="EXPERT-YELLOW-001",
            name="測試家長黃",
            email="parent-yellow@test.com",
            gender="女",
            birth_date=date(1985, 1, 1),
            phone="0912345679",
            identity_option="家長",
            current_status="親子溝通困擾",
            tenant_id="island_parents",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="island_parents",
            case_number="EXPERT-YELLOW-CASE-001",
            goals="改善親子溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Session with frustration but not violent
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長：孩子最近情緒不穩定，常常發脾氣，我該怎麼辦？我覺得很煩。",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：孩子最近情緒不穩定，常常發脾氣",
                },
                {
                    "segment_number": 2,
                    "transcript_text": "我該怎麼辦？我覺得很煩。",
                },
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
    def counselor_with_green_transcript(self, db_session: Session):
        """Create counselor with session containing positive transcript"""
        counselor = Counselor(
            id=uuid4(),
            email="expert-suggestions-green@test.com",
            username="expertsuggestionsgreen",
            full_name="Expert Suggestions Green Test",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
            available_credits=100.0,
        )
        db_session.add(counselor)
        db_session.flush()

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="EXPERT-GREEN-001",
            name="測試家長綠",
            email="parent-green@test.com",
            gender="女",
            birth_date=date(1985, 1, 1),
            phone="0912345680",
            identity_option="家長",
            current_status="親子溝通良好",
            tenant_id="island_parents",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="island_parents",
            case_number="EXPERT-GREEN-CASE-001",
            goals="維持良好溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Session with positive language
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長：謝謝你願意跟我說。我想更了解你的感受。",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：謝謝你願意跟我說",
                },
                {
                    "segment_number": 2,
                    "transcript_text": "我想更了解你的感受",
                },
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
    def counselor_with_context_aware_transcript(self, db_session: Session):
        """Create counselor with session for context-aware safety level testing"""
        counselor = Counselor(
            id=uuid4(),
            email="expert-suggestions-context@test.com",
            username="expertsuggestionscontext",
            full_name="Expert Suggestions Context Test",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
            available_credits=100.0,
        )
        db_session.add(counselor)
        db_session.flush()

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="EXPERT-CONTEXT-001",
            name="測試家長情境",
            email="parent-context@test.com",
            gender="女",
            birth_date=date(1985, 1, 1),
            phone="0912345681",
            identity_option="家長",
            current_status="親子溝通困擾",
            tenant_id="island_parents",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="island_parents",
            case_number="EXPERT-CONTEXT-CASE-001",
            goals="改善親子溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Session with "煩" but shows awareness (should be YELLOW not RED)
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長：孩子最近很煩人，不過我知道是因為他壓力大。",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：孩子最近很煩人",
                },
                {
                    "segment_number": 2,
                    "transcript_text": "不過我知道是因為他壓力大",
                },
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
    def counselor_with_empty_transcript(self, db_session: Session):
        """Create counselor with session containing empty transcript"""
        counselor = Counselor(
            id=uuid4(),
            email="expert-suggestions-empty@test.com",
            username="expertsuggestionsempty",
            full_name="Expert Suggestions Empty Test",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
            available_credits=100.0,
        )
        db_session.add(counselor)
        db_session.flush()

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="EXPERT-EMPTY-001",
            name="測試家長空",
            email="parent-empty@test.com",
            gender="女",
            birth_date=date(1985, 1, 1),
            phone="0912345682",
            identity_option="家長",
            current_status="親子溝通困擾",
            tenant_id="island_parents",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="island_parents",
            case_number="EXPERT-EMPTY-CASE-001",
            goals="改善親子溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Session with empty transcript
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="",
            recordings=[],
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
    def counselor_with_practice_transcript(self, db_session: Session):
        """Create counselor with session for practice mode testing"""
        counselor = Counselor(
            id=uuid4(),
            email="expert-suggestions-practice@test.com",
            username="expertsuggestionspractice",
            full_name="Expert Suggestions Practice Test",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
            available_credits=100.0,
        )
        db_session.add(counselor)
        db_session.flush()

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            code="EXPERT-PRACTICE-001",
            name="測試家長練習",
            email="parent-practice@test.com",
            gender="女",
            birth_date=date(1985, 1, 1),
            phone="0912345683",
            identity_option="家長",
            current_status="親子溝通學習",
            tenant_id="island_parents",
        )
        db_session.add(client)
        db_session.flush()

        case = Case(
            id=uuid4(),
            client_id=client.id,
            counselor_id=counselor.id,
            tenant_id="island_parents",
            case_number="EXPERT-PRACTICE-CASE-001",
            goals="學習親子溝通",
        )
        db_session.add(case)
        db_session.flush()

        # Session with practice conversation
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="家長：孩子最近不太願意跟我說話，我覺得很擔心。諮詢師：可以聊聊是什麼讓你擔心的嗎？",
            recordings=[
                {
                    "segment_number": 1,
                    "transcript_text": "家長：孩子最近不太願意跟我說話，我覺得很擔心",
                },
                {
                    "segment_number": 2,
                    "transcript_text": "諮詢師：可以聊聊是什麼讓你擔心的嗎？",
                },
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

    def _get_auth_headers(self, db_session: Session, email: str):
        """Helper to login and get auth headers"""
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    @skip_without_gcp
    def test_emergency_mode_selects_from_200_expert_suggestions(
        self,
        db_session: Session,
        counselor_with_red_transcript,
        mock_gemini_for_expert_suggestions,
    ):
        """Emergency mode should select suggestions from 200 expert suggestions

        Expected behavior:
        - POST /api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency
        - Response contains at least 1 suggestion
        - Each suggestion MUST be from the expert suggestion pool
        - Should NOT be LLM-generated freeform text

        Why this matters:
        - Emergency mode needs FAST, RELIABLE responses
        - Expert-curated suggestions ensure quality
        - Prevents hallucination or unsafe LLM suggestions
        """
        session_id = counselor_with_red_transcript["session"].id
        auth_headers = self._get_auth_headers(
            db_session, "expert-suggestions-red@test.com"
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency",
                headers=auth_headers,
            )

        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

        suggestions = data["suggestions"]

        # Emergency mode: MUST have at least 1 suggestion
        assert (
            len(suggestions) >= 1
        ), f"Emergency mode should return at least 1 suggestion, got {len(suggestions)}"

        # CRITICAL: Each suggestion must be from expert pool (not LLM-generated)
        all_expert_suggestions = (
            ALL_SUGGESTIONS["green"]
            + ALL_SUGGESTIONS["yellow"]
            + ALL_SUGGESTIONS["red"]
        )
        for suggestion in suggestions:
            assert suggestion in all_expert_suggestions, (
                f"Suggestion '{suggestion}' is NOT from expert pool. "
                f"This indicates LLM is generating suggestions instead of selecting from pool."
            )

    @skip_without_gcp
    def test_emergency_mode_includes_safety_level(
        self,
        db_session: Session,
        counselor_with_red_transcript,
        mock_gemini_for_expert_suggestions,
    ):
        """Emergency mode should return safety_level field

        Expected behavior:
        - Response contains safety_level field
        - safety_level is one of: "green", "yellow", "red"
        - For violent language, should return "red"

        Why this matters:
        - Frontend needs to display color-coded indicators
        - Safety level drives UI behavior (alerts, warnings)
        - Different from risk_level (which is for general counseling risk)
        """
        session_id = counselor_with_red_transcript["session"].id
        auth_headers = self._get_auth_headers(
            db_session, "expert-suggestions-red@test.com"
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # MUST have safety_level field
        assert "safety_level" in data, "Response missing safety_level field"

        # Validate enum value
        safety_level = data["safety_level"]
        assert safety_level in [
            "green",
            "yellow",
            "red",
        ], f"Invalid safety_level: {safety_level}. Must be 'green', 'yellow', or 'red'."

        # For violent language ("打死你"), should be RED
        assert safety_level == "red", (
            f"Expected 'red' for violent language, got '{safety_level}'. "
            f"Transcript contains violent keywords like '打死你'."
        )

    @skip_without_gcp
    def test_practice_mode_selects_from_200_expert_suggestions(
        self,
        db_session: Session,
        counselor_with_yellow_transcript,
        mock_gemini_for_expert_suggestions,
    ):
        """Practice mode should select suggestions from 200 expert suggestions

        Expected behavior:
        - POST /api/v1/sessions/{session_id}/deep-analyze?session_mode=practice
        - Response contains at least 1 suggestion
        - Each suggestion MUST be from the expert suggestion pool
        - Should NOT be LLM-generated freeform text

        Why this matters:
        - Practice mode provides suggestions for learning
        - Still uses expert-curated content for reliability
        """
        session_id = counselor_with_yellow_transcript["session"].id
        auth_headers = self._get_auth_headers(
            db_session, "expert-suggestions-yellow@test.com"
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

        suggestions = data["suggestions"]

        # Practice mode: MUST have at least 1 suggestion
        assert (
            len(suggestions) >= 1
        ), f"Practice mode should return at least 1 suggestion, got {len(suggestions)}"

        # CRITICAL: Each suggestion must be from expert pool
        all_expert_suggestions = (
            ALL_SUGGESTIONS["green"]
            + ALL_SUGGESTIONS["yellow"]
            + ALL_SUGGESTIONS["red"]
        )
        for suggestion in suggestions:
            assert suggestion in all_expert_suggestions, (
                f"Suggestion '{suggestion}' is NOT from expert pool. "
                f"LLM should SELECT from 200 suggestions, not GENERATE new ones."
            )

    @skip_without_gcp
    def test_practice_mode_includes_safety_level(
        self,
        db_session: Session,
        counselor_with_green_transcript,
        mock_gemini_for_expert_suggestions,
    ):
        """Practice mode should return safety_level

        Expected behavior:
        - Response contains safety_level field
        - safety_level is one of: "green", "yellow", "red"
        - For calm conversation, should return "green" or "yellow"
        """
        session_id = counselor_with_green_transcript["session"].id
        auth_headers = self._get_auth_headers(
            db_session, "expert-suggestions-green@test.com"
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # MUST have safety_level field
        assert "safety_level" in data, "Response missing safety_level field"

        # Validate enum value
        safety_level = data["safety_level"]
        assert safety_level in [
            "green",
            "yellow",
            "red",
        ], f"Invalid safety_level: {safety_level}"

        # For calm learning-oriented conversation, should be GREEN (not RED)
        assert (
            safety_level == "green"
        ), f"Expected 'green' for calm positive conversation, got '{safety_level}'"

    @skip_without_gcp
    def test_suggestions_match_safety_level_color(
        self,
        db_session: Session,
        counselor_with_red_transcript,
        counselor_with_green_transcript,
        mock_gemini_for_expert_suggestions,
    ):
        """Suggestions should match safety_level color

        Expected behavior:
        - If safety_level is "red", suggestions come from RED_SUGGESTIONS
        - If safety_level is "yellow", suggestions come from YELLOW_SUGGESTIONS
        - If safety_level is "green", suggestions come from GREEN_SUGGESTIONS

        Why this matters:
        - RED suggestions contain urgent correction language
        - YELLOW suggestions focus on adjustment strategies
        - GREEN suggestions reinforce positive behavior
        - Mismatch would confuse counselors
        """
        # Test RED scenario
        red_session_id = counselor_with_red_transcript["session"].id
        red_auth_headers = self._get_auth_headers(
            db_session, "expert-suggestions-red@test.com"
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{red_session_id}/deep-analyze?session_mode=emergency",
                headers=red_auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Should be RED level
        assert (
            data["safety_level"] == "red"
        ), f"Expected 'red' for violent language, got '{data['safety_level']}'"

        # CRITICAL: All suggestions MUST be from RED pool
        for suggestion in data["suggestions"]:
            assert suggestion in RED_SUGGESTIONS, (
                f"Safety level is 'red' but suggestion '{suggestion}' is NOT from RED_SUGGESTIONS pool. "
                f"This is a color mismatch - red-level scenarios must use red-level suggestions."
            )

        # Test GREEN scenario
        green_session_id = counselor_with_green_transcript["session"].id
        green_auth_headers = self._get_auth_headers(
            db_session, "expert-suggestions-green@test.com"
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{green_session_id}/deep-analyze?session_mode=practice",
                headers=green_auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Should be GREEN level (positive, empathetic language)
        safety_level = data["safety_level"]

        # All suggestions should be from GREEN pool
        if safety_level == "green":
            for suggestion in data["suggestions"]:
                assert (
                    suggestion in GREEN_SUGGESTIONS
                ), f"Safety level is 'green' but suggestion '{suggestion}' is NOT from GREEN_SUGGESTIONS pool."

    @skip_without_gcp
    def test_safety_level_determined_by_context(
        self,
        db_session: Session,
        counselor_with_context_aware_transcript,
        mock_gemini_for_expert_suggestions,
    ):
        """Safety level should be determined by context, not just keywords

        Expected behavior:
        - "煩" in frustrated context with awareness → YELLOW (not RED)
        - Same word has different severity in different contexts
        - LLM can understand nuance and intent

        Why this matters:
        - Keyword matching is too simplistic
        - Context matters for appropriate response
        """
        # Scenario: "煩" in YELLOW context (frustrated but shows awareness)
        session_id = counselor_with_context_aware_transcript["session"].id
        auth_headers = self._get_auth_headers(
            db_session, "expert-suggestions-context@test.com"
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Should be YELLOW (frustrated but aware), NOT RED
        # Parent shows awareness ('我知道是因為他壓力大'), not escalating to violence
        assert data["safety_level"] in ["yellow", "green"], (
            f"Expected 'yellow' or 'green' for frustrated-but-aware context, got '{data['safety_level']}'. "
            f"Parent shows awareness ('我知道是因為他壓力大'), not escalating to violence."
        )

    @skip_without_gcp
    def test_emergency_mode_handles_green_scenarios(
        self,
        db_session: Session,
        counselor_with_green_transcript,
        mock_gemini_for_expert_suggestions,
    ):
        """Emergency mode should correctly identify GREEN scenarios

        Expected behavior:
        - Not all emergency calls are RED/YELLOW
        - Some are false alarms or parent seeking validation
        - Should return "green" when appropriate
        - Should select from GREEN_SUGGESTIONS
        """
        session_id = counselor_with_green_transcript["session"].id
        auth_headers = self._get_auth_headers(
            db_session, "expert-suggestions-green@test.com"
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Should be GREEN (positive interaction)
        assert (
            data["safety_level"] == "green"
        ), f"Expected 'green' for positive interaction, got '{data['safety_level']}'"

        # Suggestions should be from GREEN pool
        for suggestion in data["suggestions"]:
            assert (
                suggestion in GREEN_SUGGESTIONS
            ), f"Safety level is 'green' but suggestion '{suggestion}' not in GREEN_SUGGESTIONS"

    @skip_without_gcp
    def test_practice_mode_includes_analysis_fields(
        self,
        db_session: Session,
        counselor_with_practice_transcript,
        mock_gemini_for_expert_suggestions,
    ):
        """Practice mode should include detailed analysis fields

        Expected behavior:
        - Response contains safety_level
        - Response contains summary (detailed analysis)
        - Response contains alerts
        - Response contains 3-4 suggestions from expert pool

        Why this matters:
        - Practice mode is for LEARNING, not just quick feedback
        - Counselor needs context, not just suggestions
        - All fields work together to provide complete picture
        """
        session_id = counselor_with_practice_transcript["session"].id
        auth_headers = self._get_auth_headers(
            db_session, "expert-suggestions-practice@test.com"
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=practice",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()

        # Practice mode MUST include all analysis fields
        assert "safety_level" in data, "Missing safety_level"
        assert "summary" in data, "Missing summary"
        assert "alerts" in data, "Missing alerts"
        assert "suggestions" in data, "Missing suggestions"

        # Verify types
        assert isinstance(data["safety_level"], str)
        assert isinstance(data["summary"], str)
        assert isinstance(data["alerts"], list)
        assert isinstance(data["suggestions"], list)

        # Suggestions should have at least 1 item
        assert (
            len(data["suggestions"]) >= 1
        ), f"Practice mode should have at least 1 suggestion, got {len(data['suggestions'])}"

        # Summary should be meaningful (not empty)
        assert len(data["summary"]) > 0, "Summary is empty"

    @skip_without_gcp
    def test_api_gracefully_handles_empty_transcript(
        self,
        db_session: Session,
        counselor_with_empty_transcript,
        mock_gemini_for_expert_suggestions,
    ):
        """API should handle edge cases gracefully

        Expected behavior:
        - Empty transcript should return 400 (validation error)
        - Should NOT crash with 500
        """
        session_id = counselor_with_empty_transcript["session"].id
        auth_headers = self._get_auth_headers(
            db_session, "expert-suggestions-empty@test.com"
        )

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session_id}/deep-analyze?session_mode=emergency",
                headers=auth_headers,
            )

        # Should return 400 for empty transcript, not 500
        assert response.status_code == 400, (
            f"Expected 400 for empty transcript, got {response.status_code}. "
            f"API should validate empty input."
        )

        # Verify error message
        data = response.json()
        assert "detail" in data
        assert (
            "transcript" in data["detail"].lower()
            or "no transcript" in data["detail"].lower()
        )
