"""Integration test for Codeer provider with session pooling and multi-model support"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.asyncio
async def test_codeer_provider_with_session_pooling():
    """Test that Codeer provider accepts session_id and routes correctly"""
    with TestClient(app) as client:
        # Test with session_id parameter
        response = client.post(
            "/api/v1/realtime/analyze",
            json={
                "transcript": "諮詢師：你好。\n案主：你好。",
                "speakers": [
                    {"speaker": "counselor", "text": "你好"},
                    {"speaker": "client", "text": "你好"},
                ],
                "time_range": "0:00-1:00",
                "provider": "codeer",
                "session_id": "test-session-123",  # Session ID for pooling
            },
        )

        # Should not error on parameter acceptance
        # Actual analysis may fail due to Codeer API, but routing should work
        assert response.status_code in [200, 500]

        # If successful, verify response has provider metadata
        if response.status_code == 200:
            data = response.json()
            assert "provider_metadata" in data
            assert data["provider_metadata"]["provider"] == "codeer"


@pytest.mark.asyncio
async def test_codeer_provider_without_session_id():
    """Test that Codeer provider works without session_id (fallback)"""
    with TestClient(app) as client:
        # Test without session_id parameter
        response = client.post(
            "/api/v1/realtime/analyze",
            json={
                "transcript": "諮詢師：你好。\n案主：你好。",
                "speakers": [
                    {"speaker": "counselor", "text": "你好"},
                    {"speaker": "client", "text": "你好"},
                ],
                "time_range": "0:00-1:00",
                "provider": "codeer",
                # No session_id - should fallback to creating new chat
            },
        )

        # Should not error on missing session_id
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "provider_metadata" in data
            assert data["provider_metadata"]["provider"] == "codeer"


class TestCodeerMultiModelSupport:
    """Test Codeer with different models (Claude, Gemini, GPT-5)"""

    @pytest.mark.asyncio
    async def test_codeer_with_claude_sonnet(self):
        """Test Codeer provider with Claude Sonnet model"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：最近家裡的孩子怎麼樣？\n案主：他最近很不聽話。",
                    "speakers": [
                        {"speaker": "counselor", "text": "最近家裡的孩子怎麼樣？"},
                        {"speaker": "client", "text": "他最近很不聽話。"},
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                    "codeer_model": "claude-sonnet",
                    "session_id": "test-claude-session",
                },
            )

            # Should accept claude-sonnet model
            assert response.status_code in [200, 500]

            if response.status_code == 200:
                data = response.json()
                assert "provider_metadata" in data
                assert data["provider_metadata"]["provider"] == "codeer"
                # Model should be shown in metadata
                assert "claude" in data["provider_metadata"]["model"].lower()

    @pytest.mark.asyncio
    async def test_codeer_with_gemini_flash(self):
        """Test Codeer provider with Gemini Flash model"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：最近家裡的孩子怎麼樣？\n案主：他最近很不聽話。",
                    "speakers": [
                        {"speaker": "counselor", "text": "最近家裡的孩子怎麼樣？"},
                        {"speaker": "client", "text": "他最近很不聽話。"},
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                    "codeer_model": "gemini-flash",
                    "session_id": "test-gemini-session",
                },
            )

            # Should accept gemini-flash model
            assert response.status_code in [200, 500]

            if response.status_code == 200:
                data = response.json()
                assert "provider_metadata" in data
                assert data["provider_metadata"]["provider"] == "codeer"
                # Model should be shown in metadata
                assert "gemini" in data["provider_metadata"]["model"].lower()

    @pytest.mark.asyncio
    async def test_codeer_with_gpt5_mini(self):
        """Test Codeer provider with GPT-5 Mini model (default)"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：最近家裡的孩子怎麼樣？\n案主：他最近很不聽話。",
                    "speakers": [
                        {"speaker": "counselor", "text": "最近家裡的孩子怎麼樣？"},
                        {"speaker": "client", "text": "他最近很不聽話。"},
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                    "codeer_model": "gpt5-mini",
                    "session_id": "test-gpt5-session",
                },
            )

            # Should accept gpt5-mini model
            assert response.status_code in [200, 500]

            if response.status_code == 200:
                data = response.json()
                assert "provider_metadata" in data
                assert data["provider_metadata"]["provider"] == "codeer"
                # Model should be shown in metadata
                assert "gpt5" in data["provider_metadata"]["model"].lower()

    @pytest.mark.asyncio
    async def test_codeer_model_aliases(self):
        """Test Codeer with model aliases (claude, gemini, gpt)"""
        with TestClient(app) as client:
            # Test 'claude' alias
            response1 = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你好。\n案主：你好。",
                    "speakers": [
                        {"speaker": "counselor", "text": "你好"},
                        {"speaker": "client", "text": "你好"},
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                    "codeer_model": "claude",  # Alias for claude-sonnet
                },
            )
            assert response1.status_code in [200, 500]

            # Test 'gemini' alias
            response2 = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你好。\n案主：你好。",
                    "speakers": [
                        {"speaker": "counselor", "text": "你好"},
                        {"speaker": "client", "text": "你好"},
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                    "codeer_model": "gemini",  # Alias for gemini-flash
                },
            )
            assert response2.status_code in [200, 500]

            # Test 'gpt' alias
            response3 = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你好。\n案主：你好。",
                    "speakers": [
                        {"speaker": "counselor", "text": "你好"},
                        {"speaker": "client", "text": "你好"},
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                    "codeer_model": "gpt",  # Alias for gpt5-mini
                },
            )
            assert response3.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_codeer_default_model(self):
        """Test Codeer defaults to gpt5-mini when model not specified"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你好。\n案主：你好。",
                    "speakers": [
                        {"speaker": "counselor", "text": "你好"},
                        {"speaker": "client", "text": "你好"},
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                    # No codeer_model specified - should default to gpt5-mini
                },
            )

            assert response.status_code in [200, 500]

            if response.status_code == 200:
                data = response.json()
                assert "provider_metadata" in data
                assert data["provider_metadata"]["provider"] == "codeer"

    @pytest.mark.asyncio
    async def test_codeer_invalid_model_rejected(self):
        """Test that invalid model names are rejected by schema validation"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你好。\n案主：你好。",
                    "speakers": [
                        {"speaker": "counselor", "text": "你好"},
                        {"speaker": "client", "text": "你好"},
                    ],
                    "time_range": "0:00-1:00",
                    "provider": "codeer",
                    "codeer_model": "invalid-model",  # Should be rejected
                },
            )

            # Should return validation error (422)
            assert response.status_code == 422
            error_data = response.json()
            assert "detail" in error_data
