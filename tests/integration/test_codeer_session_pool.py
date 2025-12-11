"""Integration tests for Codeer session pool"""
import asyncio
import time

import pytest

from app.services.codeer_client import CodeerClient
from app.services.codeer_session_pool import CodeerSessionPool, get_codeer_session_pool


@pytest.mark.asyncio
async def test_session_reuse():
    """Test that sessions are reused correctly"""
    pool = CodeerSessionPool(ttl_seconds=3600)

    async with CodeerClient() as client:
        chat1 = await pool.get_or_create_session("test-reuse", client)
        chat2 = await pool.get_or_create_session("test-reuse", client)

        # Should be same chat
        assert chat1["id"] == chat2["id"]
        print(f"✅ Session reused: {chat1['id']}")


@pytest.mark.asyncio
async def test_session_expiration():
    """Test that expired sessions create new chat"""
    pool = CodeerSessionPool(ttl_seconds=1)  # 1 second TTL

    async with CodeerClient() as client:
        chat1 = await pool.get_or_create_session("test-expire", client)

        # Wait for expiration
        await asyncio.sleep(2)

        chat2 = await pool.get_or_create_session("test-expire", client)

        # Should be different chats
        assert chat1["id"] != chat2["id"]
        print("✅ New session created after expiration")


@pytest.mark.asyncio
async def test_performance_improvement():
    """Test that session reuse is faster"""
    pool = CodeerSessionPool()

    async with CodeerClient() as client:
        # First call (create chat)
        start = time.time()
        await pool.get_or_create_session("test-perf", client)
        create_duration = time.time() - start

        # Second call (reuse)
        start = time.time()
        await pool.get_or_create_session("test-perf", client)
        reuse_duration = time.time() - start

        print(f"Create: {create_duration:.2f}s, Reuse: {reuse_duration:.3f}s")

        # Reuse should be much faster (< 10% of create time)
        assert reuse_duration < create_duration * 0.1


@pytest.mark.asyncio
async def test_get_stats():
    """Test session statistics"""
    pool = CodeerSessionPool()

    async with CodeerClient() as client:
        await pool.get_or_create_session("stats-1", client)
        await pool.get_or_create_session("stats-2", client)

        stats = pool.get_stats()
        assert stats["active_sessions"] == 2
        assert stats["ttl_seconds"] == 7200


@pytest.mark.asyncio
async def test_singleton_pattern():
    """Test that get_codeer_session_pool returns singleton"""
    pool1 = get_codeer_session_pool()
    pool2 = get_codeer_session_pool()

    # Should be same instance
    assert pool1 is pool2
    print("✅ Singleton pattern working correctly")
