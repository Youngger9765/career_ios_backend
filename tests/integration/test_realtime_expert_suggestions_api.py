"""
Integration Tests for Realtime API with 200 Expert Suggestions System
TDD RED PHASE - Tests written FIRST to define expected behavior

CRITICAL: All tests in this file are expected to FAIL initially.
They define the contract for how the Realtime API should integrate
with the 200-sentence expert suggestion system.

After these tests FAIL (RED), we implement the feature to make them PASS (GREEN).
"""
import pytest


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
    """Test Realtime API integration with 200 expert suggestions

    This test suite validates:
    1. Emergency mode selects 1-2 suggestions from expert pool
    2. Practice mode selects 3-4 suggestions from expert pool
    3. API returns safety_level (green/yellow/red)
    4. Suggestions match the safety_level color
    5. Safety level is determined by context (not just keywords)
    6. Suggestions are from expert pool (NOT LLM-generated)
    """

    @skip_without_gcp
    def test_emergency_mode_selects_from_200_expert_suggestions(
        self, client, db_session
    ):
        """Emergency mode should select 1-2 suggestions from 200 expert suggestions

        Expected behavior (RED - will fail until implemented):
        - POST /api/v1/transcript/deep-analyze with mode="emergency"
        - Response contains 1-2 suggestions
        - Each suggestion MUST be from the expert suggestion pool
        - Should NOT be LLM-generated freeform text

        Why this matters:
        - Emergency mode needs FAST, RELIABLE responses
        - Expert-curated suggestions ensure quality
        - Prevents hallucination or unsafe LLM suggestions
        """
        from app.config.parenting_suggestions import ALL_SUGGESTIONS

        # RED scenario: violent language
        request_data = {
            "transcript": "家長：你再不聽話我就打死你！孩子真的很煩！",
            "speakers": [
                {"speaker": "client", "text": "你再不聽話我就打死你！"},
                {"speaker": "client", "text": "孩子真的很煩！"},
            ],
            "mode": "emergency",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=request_data)

        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

        suggestions = data["suggestions"]

        # Emergency mode: MUST have 1-2 suggestions
        assert (
            1 <= len(suggestions) <= 2
        ), f"Emergency mode should return 1-2 suggestions, got {len(suggestions)}"

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
    def test_emergency_mode_includes_safety_level(self, client, db_session):
        """Emergency mode should return safety_level field

        Expected behavior (RED - will fail until implemented):
        - Response contains safety_level field
        - safety_level is one of: "green", "yellow", "red"
        - For violent language, should return "red"

        Why this matters:
        - Frontend needs to display color-coded indicators
        - Safety level drives UI behavior (alerts, warnings)
        - Different from risk_level (which is for general counseling risk)
        """
        request_data = {
            "transcript": "家長：你再不聽話我就打死你！滾出去！",
            "speakers": [
                {"speaker": "client", "text": "你再不聽話我就打死你！"},
                {"speaker": "client", "text": "滾出去！"},
            ],
            "mode": "emergency",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=request_data)

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

        # For violent language ("打死你", "滾"), should be RED
        assert safety_level == "red", (
            f"Expected 'red' for violent language, got '{safety_level}'. "
            f"Transcript contains violent keywords like '打死你' and '滾'."
        )

    @skip_without_gcp
    def test_practice_mode_selects_from_200_expert_suggestions(
        self, client, db_session
    ):
        """Practice mode should select 3-4 suggestions from 200 expert suggestions

        Expected behavior (RED - will fail until implemented):
        - POST /api/v1/transcript/deep-analyze with mode="practice"
        - Response contains 3-4 suggestions
        - Each suggestion MUST be from the expert suggestion pool
        - Should NOT be LLM-generated freeform text

        Why this matters:
        - Practice mode provides MORE suggestions for learning
        - Still uses expert-curated content for reliability
        - 3-4 suggestions allow deeper analysis
        """
        from app.config.parenting_suggestions import ALL_SUGGESTIONS

        # YELLOW scenario: frustration but not violent
        request_data = {
            "transcript": "家長：孩子最近情緒不穩定，常常發脾氣，我該怎麼辦？我覺得很煩。",
            "speakers": [
                {"speaker": "client", "text": "孩子最近情緒不穩定，常常發脾氣"},
                {"speaker": "client", "text": "我該怎麼辦？我覺得很煩。"},
            ],
            "mode": "practice",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data

        suggestions = data["suggestions"]

        # Practice mode: MUST have 3-4 suggestions
        assert (
            3 <= len(suggestions) <= 4
        ), f"Practice mode should return 3-4 suggestions, got {len(suggestions)}"

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
    def test_practice_mode_includes_safety_level(self, client, db_session):
        """Practice mode should return safety_level

        Expected behavior (RED - will fail until implemented):
        - Response contains safety_level field
        - safety_level is one of: "green", "yellow", "red"
        - For calm conversation, should return "green" or "yellow"
        """
        request_data = {
            "transcript": "家長：孩子最近不太願意跟我說話，我想學習怎麼跟他溝通。",
            "speakers": [
                {"speaker": "client", "text": "孩子最近不太願意跟我說話"},
                {"speaker": "client", "text": "我想學習怎麼跟他溝通"},
            ],
            "mode": "practice",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # MUST have safety_level field
        assert "safety_level" in data, "Response missing safety_level field"

        # Validate enum value
        safety_level = data["safety_level"]
        assert safety_level in [
            "green",
            "orange",
            "red",
        ], f"Invalid safety_level: {safety_level}"

        # For calm learning-oriented conversation, should be GREEN or YELLOW (not RED)
        assert safety_level in [
            "green",
            "yellow",
        ], f"Expected 'green' or 'yellow' for calm conversation, got '{safety_level}'"

    @skip_without_gcp
    def test_suggestions_match_safety_level_color(self, client, db_session):
        """Suggestions should match safety_level color

        Expected behavior (RED - will fail until implemented):
        - If safety_level is "red", suggestions come from RED_SUGGESTIONS
        - If safety_level is "yellow", suggestions come from YELLOW_SUGGESTIONS
        - If safety_level is "green", suggestions come from GREEN_SUGGESTIONS

        Why this matters:
        - RED suggestions contain urgent correction language
        - YELLOW suggestions focus on adjustment strategies
        - GREEN suggestions reinforce positive behavior
        - Mismatch would confuse counselors
        """
        from app.config.parenting_suggestions import (
            GREEN_SUGGESTIONS,
            RED_SUGGESTIONS,
        )

        # Test RED scenario
        red_request = {
            "transcript": "家長：你再不聽話我就打死你！滾出去！恨死你了！",
            "speakers": [
                {"speaker": "client", "text": "你再不聽話我就打死你！"},
                {"speaker": "client", "text": "滾出去！恨死你了！"},
            ],
            "mode": "emergency",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=red_request)
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
        green_request = {
            "transcript": "家長：謝謝你願意跟我說。我想更了解你的感受。",
            "speakers": [
                {"speaker": "client", "text": "謝謝你願意跟我說"},
                {"speaker": "client", "text": "我想更了解你的感受"},
            ],
            "mode": "practice",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=green_request)
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
    def test_safety_level_determined_by_context(self, client, db_session):
        """Safety level should be determined by context, not just keywords

        Expected behavior (RED - will fail until implemented):
        - Current _assess_risk_level() uses crude keyword matching
        - Should use LLM to understand CONTEXT and INTENT
        - "煩" in frustrated context → YELLOW
        - "煩" in violent context → RED

        Why this matters:
        - Same word has different severity in different contexts
        - Keyword matching is too simplistic
        - LLM can understand nuance and intent
        """
        # Scenario 1: "煩" in YELLOW context (frustrated but not violent)
        yellow_request = {
            "transcript": "家長：孩子最近很煩人，不過我知道是因為他壓力大。",
            "speakers": [
                {"speaker": "client", "text": "孩子最近很煩人"},
                {"speaker": "client", "text": "不過我知道是因為他壓力大"},
            ],
            "mode": "practice",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=yellow_request)
        assert response.status_code == 200
        data = response.json()

        # Should be YELLOW (frustrated but aware)
        assert data["safety_level"] == "yellow", (
            f"Expected 'yellow' for frustrated-but-aware context, got '{data['safety_level']}'. "
            f"Parent shows awareness ('我知道是因為他壓力大'), not escalating to violence."
        )

        # Scenario 2: "煩" in RED context (violent escalation)
        red_request = {
            "transcript": "家長：孩子煩死了！我真的快受不了了，想打他！",
            "speakers": [
                {"speaker": "client", "text": "孩子煩死了！"},
                {"speaker": "client", "text": "我真的快受不了了，想打他！"},
            ],
            "mode": "emergency",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=red_request)
        assert response.status_code == 200
        data = response.json()

        # Should be RED (escalating to violence)
        assert data["safety_level"] == "red", (
            f"Expected 'red' for violent escalation, got '{data['safety_level']}'. "
            f"Parent expresses violent intent ('想打他') - this is immediate danger."
        )

    @skip_without_gcp
    def test_emergency_mode_handles_green_scenarios(self, client, db_session):
        """Emergency mode should correctly identify GREEN scenarios

        Expected behavior (RED - will fail until implemented):
        - Not all emergency calls are RED/YELLOW
        - Some are false alarms or parent seeking validation
        - Should return "green" when appropriate
        - Should select from GREEN_SUGGESTIONS
        """
        from app.config.parenting_suggestions import GREEN_SUGGESTIONS

        green_request = {
            "transcript": "家長：我剛剛跟孩子說「我知道你很努力了」，他笑了。",
            "speakers": [
                {"speaker": "client", "text": "我剛剛跟孩子說「我知道你很努力了」"},
                {"speaker": "client", "text": "他笑了"},
            ],
            "mode": "emergency",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=green_request)
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
    def test_practice_mode_includes_analysis_fields(self, client, db_session):
        """Practice mode should include detailed analysis fields

        Expected behavior (RED - will fail until implemented):
        - Response contains safety_level
        - Response contains summary (detailed analysis)
        - Response contains alerts
        - Response contains 3-4 suggestions from expert pool

        Why this matters:
        - Practice mode is for LEARNING, not just quick feedback
        - Counselor needs context, not just suggestions
        - All fields work together to provide complete picture
        """
        request_data = {
            "transcript": "家長：孩子最近不太願意跟我說話，我覺得很擔心。諮詢師：可以聊聊是什麼讓你擔心的嗎？",
            "speakers": [
                {"speaker": "client", "text": "孩子最近不太願意跟我說話，我覺得很擔心"},
                {"speaker": "counselor", "text": "可以聊聊是什麼讓你擔心的嗎？"},
            ],
            "mode": "practice",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=request_data)

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

        # Suggestions should be 3-4 items
        assert (
            3 <= len(data["suggestions"]) <= 4
        ), f"Practice mode should have 3-4 suggestions, got {len(data['suggestions'])}"

        # Summary should be meaningful (not empty)
        assert len(data["summary"]) > 0, "Summary is empty"

    @skip_without_gcp
    def test_api_gracefully_handles_empty_transcript(self, client, db_session):
        """API should handle edge cases gracefully

        Expected behavior:
        - Empty transcript should return 400 or 422 (validation error)
        - OR return 200 with fallback suggestions
        - Should NOT crash with 500
        """
        request_data = {
            "transcript": "",
            "speakers": [],
            "mode": "emergency",
            "time_range": "0:00-1:00",
            "provider": "gemini",
        }

        response = client.post("/api/v1/transcript/deep-analyze", json=request_data)

        # Should not crash (either validation error or handled gracefully)
        assert (
            response.status_code in [200, 400, 422]
        ), f"Expected 200/400/422, got {response.status_code}. API should not crash on empty input."

        # If 200, should still have suggestions field
        if response.status_code == 200:
            data = response.json()
            assert "suggestions" in data
