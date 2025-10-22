"""
Integration test fixtures
"""
import pytest
from httpx import AsyncClient, ASGITransport
from typing import AsyncGenerator


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for integration tests"""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
