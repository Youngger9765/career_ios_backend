"""Integration tests for AI-powered safety assessment"""
import pytest
from httpx import AsyncClient
from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def test_session(auth_headers):
    """Create test session with case"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create case
        case_resp = await client.post(
            "/api/v1/cases",
            headers=auth_headers,
            json={"child_name": "Test Child", "child_age": 8}
        )
        case_id = case_resp.json()["id"]

        # Create session
        session_resp = await client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={"case_id": case_id, "session_mode": "practice"}
        )
        session_id = session_resp.json()["id"]

        yield {"session_id": session_id, "client": client, "headers": auth_headers}


class TestSafetyLevelDetection:
    """Test AI safety level classification"""
    pass


class TestSlidingWindow:
    """Test sliding window behavior"""
    pass


class TestSessionModes:
    """Test practice vs emergency mode"""
    pass


class TestExpertSuggestions:
    """Test expert suggestion matching"""
    pass


class TestResponseValidation:
    """Test output format compliance"""
    pass
