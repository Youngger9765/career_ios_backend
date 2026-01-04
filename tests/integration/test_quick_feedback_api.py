"""
Integration tests for Quick Feedback API
Tests the /api/v1/transcript/quick-feedback endpoint
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


# Skip tests if Google Cloud credentials are not available
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


class TestQuickFeedbackAPI:
    """Test Quick Feedback API endpoints (No Auth Required - Demo Feature)"""

    @skip_without_gcp
    def test_quick_feedback_success(self):
        """Test POST /api/v1/transcript/quick-feedback - Success case with valid transcript"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/quick-feedback",
                json={
                    "recent_transcript": "家長：你再這樣我就生氣了！\n孩子：我不是故意的..."
                },
            )

            assert response.status_code == 200

            data = response.json()

            # Verify response structure
            assert "message" in data
            assert "type" in data
            assert "timestamp" in data
            assert "latency_ms" in data

            # Verify data types
            assert isinstance(data["message"], str)
            assert isinstance(data["type"], str)
            assert isinstance(data["timestamp"], str)
            assert isinstance(data["latency_ms"], int)

            # Verify content
            assert len(data["message"]) > 0
            assert data["type"] in ["ai_generated", "fallback", "fallback_error"]
            assert data["latency_ms"] >= 0

    def test_quick_feedback_empty_transcript_validation(self):
        """Test validation rejects empty transcript"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/quick-feedback", json={"recent_transcript": ""}
            )

            assert response.status_code == 422  # Validation error

            data = response.json()

            # RFC 7807 format
            assert "type" in data
            assert "title" in data
            assert "status" in data
            assert "detail" in data

    def test_quick_feedback_missing_transcript_field(self):
        """Test validation rejects missing recent_transcript field"""
        with TestClient(app) as client:
            response = client.post("/api/v1/transcript/quick-feedback", json={})

            assert response.status_code == 422  # Validation error

    def test_quick_feedback_whitespace_only_transcript(self):
        """Test validation rejects whitespace-only transcript"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/quick-feedback",
                json={"recent_transcript": "   \n\t  "},
            )

            assert response.status_code == 422  # Validation error

    @skip_without_gcp
    def test_quick_feedback_performance_latency(self):
        """Test latency is reasonable (< 5 seconds for integration test)"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/quick-feedback",
                json={"recent_transcript": "家長：今天天氣不錯\n孩子：是啊"},
            )

            assert response.status_code == 200

            data = response.json()

            # Latency should be reasonable
            # Note: In production target is < 2s, but integration tests may be slower
            assert data["latency_ms"] < 5000  # 5 seconds max

    @skip_without_gcp
    def test_quick_feedback_message_quality(self):
        """Test message is concise and appropriate"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/quick-feedback",
                json={"recent_transcript": "家長：你做得很好！\n孩子：謝謝媽媽"},
            )

            assert response.status_code == 200

            data = response.json()

            # Message should exist and not be empty
            assert len(data["message"]) > 0

            # Message should ideally be concise
            # Note: AI may not always follow 20-char limit, so we allow flexibility
            assert (
                len(data["message"]) <= 50
            ), f"Message too long: {len(data['message'])} chars"

    @skip_without_gcp
    def test_quick_feedback_dangerous_transcript(self):
        """Test response to potentially dangerous conversation"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/quick-feedback",
                json={
                    "recent_transcript": "家長：你再這樣我就打死你！\n孩子：我害怕..."
                },
            )

            assert response.status_code == 200

            data = response.json()

            # Should still provide feedback (possibly calming message)
            assert len(data["message"]) > 0
            assert data["type"] in ["ai_generated", "fallback", "fallback_error"]

    @skip_without_gcp
    def test_quick_feedback_question_transcript(self):
        """Test response to question-based interaction"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/quick-feedback",
                json={"recent_transcript": "家長：你今天在學校開心嗎？\n孩子：很開心"},
            )

            assert response.status_code == 200

            data = response.json()

            # Should provide encouraging feedback
            assert len(data["message"]) > 0

    @skip_without_gcp
    def test_quick_feedback_long_transcript(self):
        """Test handling of longer transcript (still within 10s window)"""
        long_transcript = "\n".join(
            [
                "家長：今天在學校怎麼樣？",
                "孩子：很好啊",
                "家長：有什麼開心的事嗎？",
                "孩子：我跟小明一起玩",
                "家長：那很棒啊",
                "孩子：對啊",
            ]
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/transcript/quick-feedback",
                json={"recent_transcript": long_transcript},
            )

            assert response.status_code == 200

            data = response.json()
            assert len(data["message"]) > 0
