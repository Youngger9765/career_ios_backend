#!/usr/bin/env python3
"""
Cleanup expired Gemini caches
用於清理過期的 Gemini explicit context caches
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path (must be before imports from app)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ruff: noqa: E402
from app.services.cache_manager import cache_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main cleanup routine"""
    logger.info("=" * 80)
    logger.info("🧹 Starting Gemini cache cleanup")
    logger.info("=" * 80)

    try:
        deleted_count = await cache_manager.cleanup_expired_caches()
        logger.info(f"✅ Cleanup completed: {deleted_count} caches deleted")
        return deleted_count
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    deleted = asyncio.run(main())
    logger.info("=" * 80)
    logger.info(f"🎯 Summary: {deleted} expired caches removed")
    logger.info("=" * 80)
