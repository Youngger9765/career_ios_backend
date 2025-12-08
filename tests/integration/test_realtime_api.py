"""
Integration tests for Realtime STT Counseling API
TDD - Write tests first (RED Phase), then implement (GREEN Phase)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


# Skip these tests if Google Cloud credentials are not available or invalid
# This happens in CI without GCP secrets configured or when credentials expire locally
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


# Skip ElevenLabs tests if API key is not available
# This happens in CI without secrets configured or when key is not set locally
def _check_elevenlabs_credentials():
    """Check if ElevenLabs API key is available"""
    import os

    api_key = os.getenv("ELEVEN_LABS_API_KEY")
    return api_key is not None and len(api_key) > 0


HAS_ELEVENLABS_API_KEY = _check_elevenlabs_credentials()

skip_without_elevenlabs = pytest.mark.skipif(
    not HAS_ELEVENLABS_API_KEY,
    reason="ElevenLabs API key not available (set ELEVEN_LABS_API_KEY in environment)",
)


class TestRealtimeAnalysisAPI:
    """Test Realtime Analysis API endpoints (No Auth Required - Demo Feature)"""

    @skip_without_gcp
    def test_analyze_transcript_success(self):
        """Test POST /api/v1/realtime/analyze - Success case with valid input"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你最近工作上有什麼困擾嗎？\n案主：我覺得活著沒什麼意義...",
                    "speakers": [
                        {"speaker": "counselor", "text": "你最近工作上有什麼困擾嗎？"},
                        {"speaker": "client", "text": "我覺得活著沒什麼意義..."},
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            # Should return 200 OK
            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "summary" in data
            assert "alerts" in data
            assert "suggestions" in data
            assert "time_range" in data
            assert "timestamp" in data

            # Verify data types
            assert isinstance(data["summary"], str)
            assert isinstance(data["alerts"], list)
            assert isinstance(data["suggestions"], list)
            assert data["time_range"] == "0:00-1:00"

            # Verify content quality
            assert len(data["summary"]) > 0
            assert len(data["alerts"]) >= 1
            assert len(data["suggestions"]) >= 1

    @skip_without_gcp
    def test_analyze_transcript_minimal_input(self):
        """Test with minimal valid input"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你好。\n案主：你好。",
                    "speakers": [
                        {"speaker": "counselor", "text": "你好。"},
                        {"speaker": "client", "text": "你好。"},
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "summary" in data

    @skip_without_gcp
    def test_analyze_transcript_suicide_risk_detection(self):
        """Test that suicide-related keywords trigger alerts"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "案主：我想自殺，活著太痛苦了。",
                    "speakers": [
                        {"speaker": "client", "text": "我想自殺，活著太痛苦了。"}
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Should contain alerts about suicide risk
            assert len(data["alerts"]) > 0

    def test_analyze_transcript_invalid_missing_fields(self):
        """Test POST /api/v1/realtime/analyze - Missing required fields returns 422"""
        with TestClient(app) as client:
            # Missing transcript field
            response = client.post(
                "/api/v1/realtime/analyze",
                json={"speakers": [], "time_range": "0:00-1:00"},
            )

            assert response.status_code == 422

    def test_analyze_transcript_empty_transcript(self):
        """Test with empty transcript"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={"transcript": "", "speakers": [], "time_range": "0:00-1:00"},
            )

            # Should return 422 for empty transcript
            assert response.status_code == 422

    def test_analyze_transcript_invalid_speaker_role(self):
        """Test with invalid speaker role"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "測試內容",
                    "speakers": [{"speaker": "invalid_role", "text": "測試"}],
                    "time_range": "0:00-1:00",
                },
            )

            # Should return 422 for invalid speaker role
            assert response.status_code == 422

    @skip_without_gcp
    def test_analyze_transcript_long_content(self):
        """Test with longer transcript (simulate 1 minute of conversation)"""
        with TestClient(app) as client:
            long_transcript = """
諮詢師：你好，今天想聊什麼呢？
案主：我最近對工作感到很焦慮。
諮詢師：能多說一些嗎？
案主：我覺得我做什麼都不對，主管總是在盯著我。
諮詢師：聽起來你感受到很大的壓力。
案主：對，我有時候會想，活著到底有什麼意義...
諮詢師：你說「活著沒意義」，這是最近才有的想法嗎？
案主：最近特別強烈。
            """
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": long_transcript,
                    "speakers": [
                        {"speaker": "counselor", "text": "你好，今天想聊什麼呢？"},
                        {"speaker": "client", "text": "我最近對工作感到很焦慮。"},
                        {"speaker": "counselor", "text": "能多說一些嗎？"},
                        {
                            "speaker": "client",
                            "text": "我覺得我做什麼都不對，主管總是在盯著我。",
                        },
                        {"speaker": "counselor", "text": "聽起來你感受到很大的壓力。"},
                        {
                            "speaker": "client",
                            "text": "對，我有時候會想，活著到底有什麼意義...",
                        },
                        {
                            "speaker": "counselor",
                            "text": "你說「活著沒意義」，這是最近才有的想法嗎？",
                        },
                        {"speaker": "client", "text": "最近特別強烈。"},
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Should provide meaningful analysis
            assert len(data["summary"]) > 20
            assert len(data["alerts"]) >= 2
            assert len(data["suggestions"]) >= 2

    @skip_without_gcp
    def test_analyze_transcript_different_time_ranges(self):
        """Test with different time ranges"""
        with TestClient(app) as client:
            for time_range in ["0:00-1:00", "1:00-2:00", "5:00-6:00"]:
                response = client.post(
                    "/api/v1/realtime/analyze",
                    json={
                        "transcript": "諮詢師：你好。\n案主：你好。",
                        "speakers": [
                            {"speaker": "counselor", "text": "你好。"},
                            {"speaker": "client", "text": "你好。"},
                        ],
                        "time_range": time_range,
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["time_range"] == time_range

    @skip_without_gcp
    def test_analyze_transcript_performance(self):
        """Test that API responds within acceptable time (< 5 seconds)"""
        import time

        with TestClient(app) as client:
            start_time = time.time()

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你最近怎麼樣？\n案主：還好。",
                    "speakers": [
                        {"speaker": "counselor", "text": "你最近怎麼樣？"},
                        {"speaker": "client", "text": "還好。"},
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            elapsed_time = time.time() - start_time

            assert response.status_code == 200
            # Should respond within 5 seconds (Gemini Flash is fast)
            assert elapsed_time < 5.0

    @skip_without_gcp
    def test_analyze_transcript_response_format(self):
        """Test that response follows expected JSON format"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：今天感覺如何？\n案主：我覺得有點焦慮。",
                    "speakers": [
                        {"speaker": "counselor", "text": "今天感覺如何？"},
                        {"speaker": "client", "text": "我覺得有點焦慮。"},
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure matches schema
            assert isinstance(data["summary"], str)
            assert isinstance(data["alerts"], list)
            assert isinstance(data["suggestions"], list)
            assert isinstance(data["time_range"], str)
            assert isinstance(data["timestamp"], str)

            # Verify arrays contain strings
            for alert in data["alerts"]:
                assert isinstance(alert, str)

            for suggestion in data["suggestions"]:
                assert isinstance(suggestion, str)


class TestElevenLabsTokenAPI:
    """Test ElevenLabs Token Generation API (No Auth Required)"""

    @skip_without_elevenlabs
    def test_generate_token_success(self):
        """Test POST /api/v1/realtime/elevenlabs-token - Should return a valid token"""
        with TestClient(app) as client:
            response = client.post("/api/v1/realtime/elevenlabs-token")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "token" in data
            assert isinstance(data["token"], str)
            assert len(data["token"]) > 0

            # Token should be non-empty string (ElevenLabs generates UUID-like tokens)
            assert data["token"].strip() != ""
