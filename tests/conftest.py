"""
Pytest configuration and fixtures
"""
import os
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Set test environment
os.environ["MOCK_MODE"] = "true"
os.environ["DEBUG"] = "true"


@pytest.fixture
def client() -> Generator:
    """Create a synchronous test client for the FastAPI app"""
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator:
    """Create an async test client for the FastAPI app"""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client


@pytest.fixture
def mock_audio_file():
    """Create a mock audio file for testing"""
    return {
        "file": ("test_audio.mp3", b"fake audio content", "audio/mpeg")
    }


@pytest.fixture
def sample_session_data():
    """Sample session data for testing"""
    return {
        "counselor_id": 1,
        "client_id": 1,
        "room_number": "A101",
        "notes": "Initial consultation session"
    }


@pytest.fixture
def auth_headers():
    """Mock authentication headers"""
    return {
        "Authorization": "Bearer mock_token_12345"
    }
