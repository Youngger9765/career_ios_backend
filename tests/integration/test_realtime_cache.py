"""
Integration tests for Gemini Explicit Context Caching
TDD - Write tests first (RED phase)
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestRealtimeCacheAPI:
    """Test Gemini explicit context caching functionality"""

    @pytest.mark.asyncio
    async def test_analyze_with_cache_creates_cache(self, async_client):
        """
        Test that first call creates a cache
        GIVEN: A realtime analyze request with use_cache=True
        WHEN: First call is made
        THEN: Cache is created and response includes cache metadata
        """
        # Mock cache creation
        with patch(
            "app.services.cache_manager.CacheManager.get_or_create_cache"
        ) as mock_cache:
            mock_cached_content = MagicMock()
            mock_cached_content.name = "cache_session_123"
            mock_cache.return_value = (mock_cached_content, True)  # (cache, is_new)

            # Mock Gemini service response
            with patch(
                "app.services.gemini_service.GeminiService.analyze_with_cache"
            ) as mock_analyze:
                mock_analyze.return_value = {
                    "summary": "Test summary",
                    "alerts": ["Alert 1"],
                    "suggestions": ["Suggestion 1"],
                    "usage_metadata": {
                        "cached_content_token_count": 0,
                        "prompt_token_count": 1500,
                    },
                }

                # Make request
                response = await async_client.post(
                    "/api/v1/realtime/analyze",
                    json={
                        "transcript": "counselor: Hello\nclient: Hi",
                        "speakers": [
                            {"speaker": "counselor", "text": "Hello"},
                            {"speaker": "client", "text": "Hi"},
                        ],
                        "time_range": "0:00-1:00",
                        "use_cache": True,
                        "session_id": "session_123",
                    },
                )

                # Assert response
                assert response.status_code == 200
                data = response.json()
                assert data["summary"] == "Test summary"
                assert "cache_metadata" in data
                assert data["cache_metadata"]["cache_created"] is True
                assert data["cache_metadata"]["cache_name"] == "cache_session_123"

    @pytest.mark.asyncio
    async def test_analyze_with_cache_reuses_cache(self, async_client):
        """
        Test that second call reuses existing cache
        GIVEN: A cache already exists for session_id
        WHEN: Second call is made
        THEN: Cache is reused and cached_tokens > 0
        """
        with patch(
            "app.services.cache_manager.CacheManager.get_or_create_cache"
        ) as mock_cache:
            mock_cached_content = MagicMock()
            mock_cached_content.name = "cache_session_123"
            mock_cache.return_value = (
                mock_cached_content,
                False,
            )  # (cache, is_new=False)

            with patch(
                "app.services.gemini_service.GeminiService.analyze_with_cache"
            ) as mock_analyze:
                mock_analyze.return_value = {
                    "summary": "Test summary 2",
                    "alerts": ["Alert 2"],
                    "suggestions": ["Suggestion 2"],
                    "usage_metadata": {
                        "cached_content_token_count": 2500,
                        "prompt_token_count": 150,
                    },
                }

                response = await async_client.post(
                    "/api/v1/realtime/analyze",
                    json={
                        "transcript": "counselor: How are you?\nclient: I'm fine",
                        "speakers": [
                            {"speaker": "counselor", "text": "How are you?"},
                            {"speaker": "client", "text": "I'm fine"},
                        ],
                        "time_range": "1:00-2:00",
                        "use_cache": True,
                        "session_id": "session_123",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert "cache_metadata" in data
                assert data["cache_metadata"]["cache_created"] is False
                assert data["cache_metadata"]["cached_tokens"] > 0

    @pytest.mark.asyncio
    async def test_cache_fallback_on_error(self, async_client):
        """
        Test that when cache fails, request falls back to non-cached mode
        GIVEN: Cache creation/retrieval fails
        WHEN: Request is made
        THEN: Falls back to non-cached analysis and returns valid response
        """
        with patch(
            "app.services.cache_manager.CacheManager.get_or_create_cache"
        ) as mock_cache:
            mock_cache.side_effect = Exception("Cache error")

            with patch(
                "app.services.gemini_service.GeminiService.analyze_realtime_transcript"
            ) as mock_fallback:
                mock_fallback.return_value = {
                    "summary": "Fallback summary",
                    "alerts": ["Fallback alert"],
                    "suggestions": ["Fallback suggestion"],
                }

                response = await async_client.post(
                    "/api/v1/realtime/analyze",
                    json={
                        "transcript": "counselor: Test\nclient: Response",
                        "speakers": [
                            {"speaker": "counselor", "text": "Test"},
                            {"speaker": "client", "text": "Response"},
                        ],
                        "time_range": "0:00-1:00",
                        "use_cache": True,
                        "session_id": "session_error",
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert data["summary"] == "Fallback summary"
                # Cache metadata should be None or indicate error
                assert (
                    data.get("cache_metadata") is None
                    or data["cache_metadata"].get("error") is not None
                )

    @pytest.mark.asyncio
    async def test_use_cache_false_bypasses_cache(self, async_client):
        """
        Test that use_cache=False bypasses caching
        GIVEN: use_cache is explicitly set to False
        WHEN: Request is made
        THEN: No cache is used, standard analysis is performed
        """
        with patch(
            "app.services.gemini_service.GeminiService.analyze_realtime_transcript"
        ) as mock_analyze:
            mock_analyze.return_value = {
                "summary": "Non-cached summary",
                "alerts": ["Alert"],
                "suggestions": ["Suggestion"],
            }

            response = await async_client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "counselor: Test\nclient: Response",
                    "speakers": [
                        {"speaker": "counselor", "text": "Test"},
                        {"speaker": "client", "text": "Response"},
                    ],
                    "time_range": "0:00-1:00",
                    "use_cache": False,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["summary"] == "Non-cached summary"
            assert "cache_metadata" not in data or data["cache_metadata"] is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_caches(self):
        """
        Test cache cleanup mechanism
        GIVEN: Multiple caches with different expiration times
        WHEN: Cleanup is triggered
        THEN: Expired caches are deleted, active caches remain
        """
        from app.services.cache_manager import CacheManager

        with patch(
            "app.services.cache_manager.caching.CachedContent.list"
        ) as mock_list:
            # Mock cache list with expired and active caches
            expired_cache = MagicMock()
            expired_cache.name = "expired_cache"
            expired_cache.expire_time = datetime(2020, 1, 1, tzinfo=timezone.utc)

            active_cache = MagicMock()
            active_cache.name = "active_cache"
            active_cache.expire_time = datetime(2030, 1, 1, tzinfo=timezone.utc)

            mock_list.return_value = [expired_cache, active_cache]

            manager = CacheManager()
            deleted_count = await manager.cleanup_expired_caches()

            # Should delete only expired cache
            assert deleted_count == 1
            expired_cache.delete.assert_called_once()
            active_cache.delete.assert_not_called()


class TestCacheBackwardCompatibility:
    """Test backward compatibility of cache feature"""

    @pytest.mark.asyncio
    async def test_request_without_use_cache_defaults_to_true(self, async_client):
        """
        Test that requests without use_cache field default to cache enabled
        GIVEN: Request without use_cache field
        WHEN: Request is made
        THEN: Cache is used by default (backward compatible)
        """
        with patch(
            "app.services.cache_manager.CacheManager.get_or_create_cache"
        ) as mock_cache:
            mock_cached_content = MagicMock()
            mock_cached_content.name = "cache_default"
            mock_cache.return_value = (mock_cached_content, True)

            with patch(
                "app.services.gemini_service.GeminiService.analyze_with_cache"
            ) as mock_analyze:
                mock_analyze.return_value = {
                    "summary": "Default cache behavior",
                    "alerts": [],
                    "suggestions": [],
                    "usage_metadata": {
                        "cached_content_token_count": 0,
                        "prompt_token_count": 1000,
                    },
                }

                response = await async_client.post(
                    "/api/v1/realtime/analyze",
                    json={
                        "transcript": "counselor: Hi\nclient: Hello",
                        "speakers": [
                            {"speaker": "counselor", "text": "Hi"},
                            {"speaker": "client", "text": "Hello"},
                        ],
                        "time_range": "0:00-1:00",
                        "session_id": "default_session",
                        # Note: use_cache not specified
                    },
                )

                assert response.status_code == 200
                data = response.json()
                assert "cache_metadata" in data
