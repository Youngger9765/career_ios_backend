"""
Integration tests for Realtime Mode Switching and Risk Level Indicators
TDD - RED Phase: Write tests first, expect them to fail
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


# Skip these tests if Google Cloud credentials are not available or invalid
def _check_gcp_credentials():
    """Check if valid GCP credentials are available"""
    try:
        from google.auth import default
        from google.auth.exceptions import DefaultCredentialsError, RefreshError

        try:
            credentials, project = default()
            # Try to refresh to check if credentials are valid
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


class TestRealtimeModeSwitching:
    """Test mode switching (emergency vs practice) for realtime counseling"""

    @skip_without_gcp
    def test_emergency_mode_returns_simplified_response(self):
        """Test 1: Emergency mode should return ≤2 sentences per suggestion

        Scenario: Given mode="emergency"
        Expected: Each suggestion should be ≤2 sentences (simplified for urgent situations)
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "mode": "emergency",
                    "transcript": "家長：我要打死你！你給我滾出去！我受夠了！",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我要打死你！你給我滾出去！我受夠了！",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "summary" in data
            assert "alerts" in data
            assert "suggestions" in data
            assert "safety_level" in data  # NEW: Risk level field

            # Verify suggestions are simplified (≤2 sentences each)
            for suggestion in data["suggestions"]:
                # Count sentences (simplified: count periods, question marks, exclamations)
                sentence_count = (
                    suggestion.count("。")
                    + suggestion.count("？")
                    + suggestion.count("！")
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

    @skip_without_gcp
    def test_practice_mode_returns_detailed_response(self):
        """Test 2: Practice mode should return detailed analysis

        Scenario: Given mode="practice" (or no mode = default)
        Expected: Detailed format with comprehensive suggestions
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "mode": "practice",
                    "transcript": "家長：寶貝，我們一起想想怎麼做好嗎？我知道你也覺得很難。",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "寶貝，我們一起想想怎麼做好嗎？我知道你也覺得很難。",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "summary" in data
            assert "alerts" in data
            assert "suggestions" in data
            assert "safety_level" in data

            # Verify detailed format (more comprehensive)
            assert (
                len(data["suggestions"]) >= 2
            ), "Practice mode should have ≥2 suggestions"
            assert len(data["alerts"]) >= 1, "Practice mode should have ≥1 alert"

            # Suggestions can be longer in practice mode
            # No strict length limit for practice mode

    @skip_without_gcp
    def test_default_mode_is_practice(self):
        """Test 3: Default mode should be 'practice' when mode is not specified

        Scenario: Given no mode field in request
        Expected: Should default to practice mode with detailed analysis
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    # No "mode" field
                    "transcript": "家長：我們今天學到很多，謝謝你的配合。",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我們今天學到很多，謝謝你的配合。",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Should return detailed response (practice mode default)
            assert "summary" in data
            assert "suggestions" in data
            assert len(data["suggestions"]) >= 2


class TestRiskLevelIndicators:
    """Test risk level assessment (red/yellow/green) for realtime counseling"""

    @skip_without_gcp
    def test_safety_level_red_for_violent_language(self):
        """Test 4: Violent language should trigger RED risk level

        Scenario: Transcript contains violent language: "我要打死你！滾出去！"
        Expected: safety_level == "red"
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": "家長：我要打死你！你給我滾出去！我快受不了了！",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我要打死你！你給我滾出去！我快受不了了！",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify safety_level field exists
            assert "safety_level" in data

            # Should be RED for violent language
            assert (
                data["safety_level"] == "red"
            ), f"Expected 'red' but got '{data['safety_level']}'"

    @skip_without_gcp
    def test_safety_level_yellow_for_escalating_conflict(self):
        """Test 5: Escalating conflict should trigger YELLOW risk level

        Scenario: Transcript shows escalating emotions: "你怎麼又不聽話！我快氣死了！"
        Expected: safety_level == "yellow"
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": "家長：你怎麼又把房間弄亂！你說謊！我快氣死了！",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "你怎麼又把房間弄亂！你說謊！我快氣死了！",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify safety_level field exists
            assert "safety_level" in data

            # Should be YELLOW for escalating conflict
            assert (
                data["safety_level"] == "yellow"
            ), f"Expected 'yellow' but got '{data['safety_level']}'"

    @skip_without_gcp
    def test_safety_level_green_for_positive_interaction(self):
        """Test 6: Positive interaction should trigger GREEN risk level

        Scenario: Transcript shows calm, positive interaction: "寶貝，我們一起收拾好嗎？"
        Expected: safety_level == "green"
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": "家長：寶貝，我們一起收拾好嗎？我知道你累了，我們慢慢來。",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "寶貝，我們一起收拾好嗎？我知道你累了，我們慢慢來。",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify safety_level field exists
            assert "safety_level" in data

            # Should be GREEN for positive interaction
            assert (
                data["safety_level"] == "green"
            ), f"Expected 'green' but got '{data['safety_level']}'"

    @skip_without_gcp
    def test_safety_level_red_for_extreme_emotions(self):
        """Test 7: Extreme emotions should trigger RED risk level

        Scenario: Multiple red flag keywords: "恨死", "受不了", "不想活"
        Expected: safety_level == "red"
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": "家長：我恨死這樣的生活了，我真的受不了了！",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我恨死這樣的生活了，我真的受不了了！",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert "safety_level" in data
            assert (
                data["safety_level"] == "red"
            ), f"Expected 'red' but got '{data['safety_level']}'"

    @skip_without_gcp
    def test_safety_level_yellow_for_frustration(self):
        """Test 8: Frustration without violence should trigger YELLOW

        Scenario: Frustrated but not violent: "你不聽話", "煩死了"
        Expected: safety_level == "yellow"
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": "家長：你怎麼又不聽話！我真的快煩死了！",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "你怎麼又不聽話！我真的快煩死了！",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert "safety_level" in data
            assert (
                data["safety_level"] == "yellow"
            ), f"Expected 'yellow' but got '{data['safety_level']}'"


class TestSchemaValidation:
    """Test schema validation for mode and safety_level fields"""

    @skip_without_gcp
    def test_schema_validation_mode_field_emergency(self):
        """Test 9: Verify mode field accepts 'emergency'

        Scenario: POST with mode="emergency"
        Expected: Should accept and process correctly
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "mode": "emergency",
                    "transcript": "家長：我需要立即的建議！",
                    "speakers": [{"speaker": "client", "text": "我需要立即的建議！"}],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "safety_level" in data

    @skip_without_gcp
    def test_schema_validation_mode_field_practice(self):
        """Test 10: Verify mode field accepts 'practice'

        Scenario: POST with mode="practice"
        Expected: Should accept and process correctly
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "mode": "practice",
                    "transcript": "家長：我想學習更好的親子溝通方式。",
                    "speakers": [
                        {"speaker": "client", "text": "我想學習更好的親子溝通方式。"}
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "safety_level" in data

    def test_schema_validation_invalid_mode(self):
        """Test 11: Verify invalid mode is rejected

        Scenario: POST with mode="invalid"
        Expected: Should return 422 validation error
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "mode": "invalid_mode",
                    "transcript": "家長：測試",
                    "speakers": [{"speaker": "client", "text": "測試"}],
                    "time_range": "0:00-1:00",
                },
            )

            # Should fail validation
            assert response.status_code == 422

    @skip_without_gcp
    def test_schema_validation_safety_level_in_response(self):
        """Test 12: Verify response includes safety_level field

        Scenario: Any valid POST request
        Expected: Response must include safety_level field with value in ["red", "yellow", "green"]
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "transcript": "家長：今天天氣不錯。",
                    "speakers": [{"speaker": "client", "text": "今天天氣不錯。"}],
                    "time_range": "0:00-1:00",
                },
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

    @skip_without_gcp
    def test_complete_response_schema(self):
        """Test 13: Verify complete response schema with all new fields

        Scenario: Verify response includes all required fields including new ones
        Expected: Response should have summary, alerts, suggestions, safety_level, etc.
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "mode": "emergency",
                    "transcript": "家長：我快受不了了！",
                    "speakers": [{"speaker": "client", "text": "我快受不了了！"}],
                    "time_range": "0:00-1:00",
                },
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
                "safety_level",  # NEW FIELD
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

    @skip_without_gcp
    def test_emergency_mode_with_red_safety_level(self):
        """Test 14: Emergency mode + RED risk should provide urgent, simplified guidance

        Scenario: mode="emergency" + violent language (red risk)
        Expected: Simplified response with high urgency
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "mode": "emergency",
                    "transcript": "家長：我要打死他！我受夠了！滾開！",
                    "speakers": [
                        {"speaker": "client", "text": "我要打死他！我受夠了！滾開！"}
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Should be RED risk
            assert data["safety_level"] == "red"

            # Should have simplified emergency response
            for suggestion in data["suggestions"]:
                sentence_count = (
                    suggestion.count("。")
                    + suggestion.count("？")
                    + suggestion.count("！")
                )
                assert sentence_count <= 2

    @skip_without_gcp
    def test_practice_mode_with_green_safety_level(self):
        """Test 15: Practice mode + GREEN risk should provide detailed learning guidance

        Scenario: mode="practice" + positive interaction (green risk)
        Expected: Detailed response with learning focus
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/deep-analyze",
                json={
                    "mode": "practice",
                    "transcript": "家長：寶貝，我們一起想想怎麼解決這個問題好嗎？",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "寶貝，我們一起想想怎麼解決這個問題好嗎？",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Should be GREEN risk
            assert data["safety_level"] == "green"

            # Should have detailed practice response
            assert len(data["suggestions"]) >= 2
