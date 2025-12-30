"""
Gemini Explicit Context Caching Manager
Manages creation, retrieval, and cleanup of Gemini cached contents
"""
import logging
from datetime import datetime, timezone
from typing import Tuple

import vertexai
from vertexai.preview import caching

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Manager for Gemini explicit context caching"""

    # Gemini's minimum token requirement for caching
    MIN_CACHE_TOKENS = 1024

    def __init__(self):
        """Initialize cache manager"""
        self.project_id = settings.GEMINI_PROJECT_ID
        self.location = settings.GEMINI_LOCATION
        self.model_name = settings.GEMINI_CHAT_MODEL
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of Vertex AI"""
        if not self._initialized:
            vertexai.init(project=self.project_id, location=self.location)
            self._initialized = True

    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a rough heuristic: 1 token ≈ 2-3 characters for English/Chinese mix.
        For Chinese text, this is more conservative (2 chars/token).

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Conservative estimate: 1 token per 2 characters
        # This ensures we don't underestimate and attempt cache creation too early
        return len(text) // 2

    async def get_or_create_cache(
        self,
        session_id: str,
        system_instruction: str,
        accumulated_transcript: str,
        ttl_seconds: int = 7200,
    ) -> Tuple[caching.CachedContent | None, bool]:
        """
        Get or create cache for a session (Strategy A: Always update)

        Strategy A: Delete old cache and create new one with updated transcript.
        This ensures cache always contains the latest accumulated conversation.

        Args:
            session_id: Unique session identifier
            system_instruction: System instruction for Gemini
            accumulated_transcript: Accumulated conversation transcript
            ttl_seconds: Time-to-live in seconds (default: 2 hours)

        Returns:
            Tuple of (CachedContent | None, is_new)
            - CachedContent: The cache object (None if content too short)
            - is_new: Always True for Strategy A (always recreating)

        Raises:
            Exception: If cache creation/retrieval fails
        """
        self._ensure_initialized()

        cache_display_name = f"counseling_session_{session_id}"

        try:
            # Step 1: Find and delete existing cache (if any)
            # Gracefully handle permission errors (e.g., missing cachedContents.list permission)
            try:
                existing_caches = caching.CachedContent.list()
                for cache in existing_caches:
                    if cache.display_name == cache_display_name:
                        logger.info(
                            f"Found existing cache, deleting to update with new content: {cache.name}"
                        )
                        cache.delete()
                        break
            except Exception as list_error:
                # If list() fails (e.g., permission denied), skip deletion and proceed to create
                # This is acceptable because:
                # 1. For new sessions, there won't be existing caches anyway
                # 2. Gemini will auto-expire old caches based on TTL
                logger.warning(
                    f"Cannot list existing caches (permission denied or API error): {list_error}. "
                    f"Proceeding to create new cache without checking for existing ones."
                )

            # Step 2: Check if content is long enough for caching
            combined_content = system_instruction + "\n\n" + accumulated_transcript
            estimated_tokens = self.estimate_token_count(combined_content)

            if estimated_tokens < self.MIN_CACHE_TOKENS:
                logger.info(
                    f"Content too short for caching: {estimated_tokens} tokens "
                    f"(minimum: {self.MIN_CACHE_TOKENS}). "
                    f"Transcript length: {len(accumulated_transcript)} chars"
                )
                return None, False

            # Step 3: Create new cache with updated accumulated transcript
            logger.info(
                f"Creating new cache for session: {session_id}, "
                f"estimated tokens: {estimated_tokens}, "
                f"transcript length: {len(accumulated_transcript)} chars"
            )

            cached_content = caching.CachedContent.create(
                model_name=self.model_name,
                system_instruction=system_instruction,
                contents=[accumulated_transcript],
                ttl=f"{ttl_seconds}s",
                display_name=cache_display_name,
            )

            logger.info(
                f"Cache created successfully: {cached_content.name}, "
                f"expires at {cached_content.expire_time}"
            )

            # Strategy A always returns is_new=True (always recreating)
            return cached_content, True

        except Exception as e:
            logger.error(f"Failed to create cache for session {session_id}: {e}")
            raise

    async def cleanup_expired_caches(self) -> int:
        """
        Clean up expired caches

        Returns:
            Number of caches deleted

        Raises:
            Exception: If cache cleanup fails due to permission errors
        """
        self._ensure_initialized()

        try:
            caches = caching.CachedContent.list()
            deleted_count = 0
            now = datetime.now(timezone.utc)

            for cache in caches:
                if cache.expire_time and cache.expire_time < now:
                    logger.info(f"Deleting expired cache: {cache.name}")
                    cache.delete()
                    deleted_count += 1

            logger.info(f"Cleanup completed: {deleted_count} caches deleted")
            return deleted_count

        except Exception as e:
            # Note: This requires cachedContents.list permission
            logger.error(f"Failed to cleanup caches (permission denied?): {e}")
            raise

    async def delete_cache_by_session(self, session_id: str) -> bool:
        """
        Delete cache for a specific session

        Args:
            session_id: Session identifier

        Returns:
            True if cache was deleted, False if not found

        Raises:
            Exception: If cache deletion fails due to permission errors
        """
        self._ensure_initialized()

        cache_display_name = f"counseling_session_{session_id}"

        try:
            caches = caching.CachedContent.list()
            for cache in caches:
                if cache.display_name == cache_display_name:
                    logger.info(
                        f"Deleting cache for session {session_id}: {cache.name}"
                    )
                    cache.delete()
                    return True

            logger.info(f"No cache found for session {session_id}")
            return False

        except Exception as e:
            # Note: This requires cachedContents.list permission
            logger.error(
                f"Failed to delete cache for session {session_id} (permission denied?): {e}"
            )
            raise


# Singleton instance
cache_manager = CacheManager()
