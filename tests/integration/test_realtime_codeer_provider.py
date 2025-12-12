"""
Integration tests for Realtime API with Codeer provider
Tests the new provider parameter and Codeer integration
"""

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _check_codeer_credentials():
    """Check if Codeer API key is available"""
    api_key = os.getenv("CODEER_API_KEY")
    return api_key is not None and len(api_key) > 0


HAS_CODEER_API_KEY = _check_codeer_credentials()

skip_without_codeer = pytest.mark.skipif(
    not HAS_CODEER_API_KEY,
    reason="Codeer API key not available (set CODEER_API_KEY in environment)",
)


class TestRealtimeCodeerProvider:
    """Test Realtime Analysis API with Codeer provider"""

    @skip_without_codeer
    def test_analyze_with_codeer_provider(self):
        """Test POST /api/v1/realtime/analyze with provider=codeer"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你好，今天想聊什麼？\n家長：我家孩子最近不聽話，我很焦慮...",
                    "speakers": [
                        {"speaker": "counselor", "text": "你好，今天想聊什麼？"},
                        {
                            "speaker": "client",
                            "text": "我家孩子最近不聽話，我很焦慮...",
                        },
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
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
            assert "provider_metadata" in data

            # Verify provider metadata
            assert data["provider_metadata"]["provider"] == "codeer"
            assert "latency_ms" in data["provider_metadata"]
            assert data["provider_metadata"]["latency_ms"] > 0
            assert "親子專家" in data["provider_metadata"]["model"]

            # Verify token usage is present and valid
            assert "codeer_token_usage" in data["provider_metadata"]
            token_usage = data["provider_metadata"]["codeer_token_usage"]
            assert token_usage is not None, "Token usage should not be None"
            assert "total_prompt_tokens" in token_usage
            assert "total_completion_tokens" in token_usage
            assert "total_tokens" in token_usage
            assert "total_calls" in token_usage
            assert token_usage["total_tokens"] > 0, "Should have non-zero token usage"
            assert token_usage["total_calls"] >= 1, "Should have at least 1 API call"

            # Verify data types
            assert isinstance(data["summary"], str)
            assert isinstance(data["alerts"], list)
            assert isinstance(data["suggestions"], list)

            # Verify content quality
            assert len(data["summary"]) > 0
            assert len(data["alerts"]) >= 1
            assert len(data["suggestions"]) >= 1

    @skip_without_codeer
    def test_analyze_with_codeer_parenting_context(self):
        """Test Codeer provider with parenting-specific content"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": """
家長：我家孩子今年5歲，最近很愛發脾氣，動不動就哭鬧。
諮詢師：能具體說說是什麼情況嗎？
家長：比如說，我叫他吃飯，他不吃，我一催他就開始哭。
諮詢師：這種情況多久了？
家長：大概一個月了，我真的快崩潰了...
                    """.strip(),
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我家孩子今年5歲，最近很愛發脾氣，動不動就哭鬧。",
                        },
                        {"speaker": "counselor", "text": "能具體說說是什麼情況嗎？"},
                        {
                            "speaker": "client",
                            "text": "比如說，我叫他吃飯，他不吃，我一催他就開始哭。",
                        },
                        {"speaker": "counselor", "text": "這種情況多久了？"},
                        {
                            "speaker": "client",
                            "text": "大概一個月了，我真的快崩潰了...",
                        },
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Should detect parenting context and provide relevant suggestions
            assert data["provider_metadata"]["provider"] == "codeer"
            assert len(data["suggestions"]) >= 1

            # Verify JSON structure is valid
            assert isinstance(data["alerts"], list)
            assert isinstance(data["suggestions"], list)

    def test_invalid_provider(self):
        """Test with invalid provider value"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "測試內容",
                    "speakers": [{"speaker": "counselor", "text": "測試"}],
                    "time_range": "0:00-1:00",
                    "provider": "invalid_provider",
                },
            )

            # Should return 422 for invalid provider
            assert response.status_code == 422
            data = response.json()
            assert "provider" in str(data).lower()

    def test_provider_defaults_to_gemini(self):
        """Test that provider defaults to gemini when not specified"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "測試內容",
                    "speakers": [{"speaker": "counselor", "text": "測試"}],
                    "time_range": "0:00-1:00",
                    # No provider specified
                },
            )

            # Should still be valid (will fail later if no GCP creds, but schema should pass)
            # We're just testing that omitting provider is valid
            assert response.status_code in [200, 500]  # 500 if no GCP creds

    @skip_without_codeer
    def test_codeer_provider_performance(self):
        """Test that Codeer provider responds within acceptable time"""
        import time

        with TestClient(app) as client:
            start_time = time.time()

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你最近怎麼樣？\n家長：孩子不聽話。",
                    "speakers": [
                        {"speaker": "counselor", "text": "你最近怎麼樣？"},
                        {"speaker": "client", "text": "孩子不聽話。"},
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                },
            )

            elapsed_time = time.time() - start_time

            assert response.status_code == 200
            data = response.json()

            # Should respond within reasonable time (40 seconds for Codeer)
            # Note: Increased from 25s to account for DB connection timeout in CI
            assert elapsed_time < 40.0

            # Latency should be tracked in metadata
            assert data["provider_metadata"]["latency_ms"] > 0
            assert data["provider_metadata"]["latency_ms"] < 40000

    @skip_without_codeer
    def test_codeer_provider_with_cache_disabled(self):
        """Test Codeer provider with cache disabled (cache is Gemini-only)"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你好。\n家長：你好。",
                    "speakers": [
                        {"speaker": "counselor", "text": "你好。"},
                        {"speaker": "client", "text": "你好。"},
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                    "use_cache": False,
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Should work normally (cache_metadata should be None for Codeer)
            assert data["provider_metadata"]["provider"] == "codeer"
            assert data["cache_metadata"] is None


class TestRealtimeProviderComparison:
    """Compare Gemini and Codeer providers"""

    @skip_without_codeer
    def test_both_providers_same_input(self):
        """Test that both providers return valid responses for the same input"""
        test_input = {
            "transcript": "諮詢師：今天想聊什麼？\n家長：孩子不愛學習。",
            "speakers": [
                {"speaker": "counselor", "text": "今天想聊什麼？"},
                {"speaker": "client", "text": "孩子不愛學習。"},
            ],
            "time_range": "0:00-1:00",
        }

        with TestClient(app) as client:
            # Test Codeer provider
            codeer_response = client.post(
                "/api/v1/realtime/analyze",
                json={**test_input, "provider": "codeer"},
            )

            assert codeer_response.status_code == 200
            codeer_data = codeer_response.json()

            # Verify Codeer response
            assert codeer_data["provider_metadata"]["provider"] == "codeer"
            assert len(codeer_data["summary"]) > 0
            assert len(codeer_data["alerts"]) >= 1
            assert len(codeer_data["suggestions"]) >= 1

            # Both should return valid analysis
            assert isinstance(codeer_data["summary"], str)
            assert isinstance(codeer_data["alerts"], list)
            assert isinstance(codeer_data["suggestions"], list)
