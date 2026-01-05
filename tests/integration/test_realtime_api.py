"""
Integration tests for Transcript API (ElevenLabs Token)
and Island Parents HTML pages.

Note: The old /api/v1/realtime/analyze endpoint has been replaced with
session-based analysis endpoints:
- POST /api/v1/sessions/{session_id}/quick-feedback
- POST /api/v1/sessions/{session_id}/deep-analyze
- POST /api/v1/sessions/{session_id}/report

These session-based endpoints are tested in test_session_analysis_api.py
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


# Skip ElevenLabs tests if API key is not available
# This happens in CI without secrets configured or when key is not set locally
def _check_elevenlabs_credentials():
    """Check if ElevenLabs API key is available"""
    import os

    api_key = os.getenv("ELEVEN_LABS_API_KEY")
    return api_key is not None and len(api_key) > 0


HAS_ELEVENLABS_API_KEY = _check_elevenlabs_credentials()

skip_without_elevenlabs = pytest.mark.skipif(
    not HAS_ELEVENLABS_API_KEY,
    reason="ElevenLabs API key not available (set ELEVEN_LABS_API_KEY in environment)",
)


class TestElevenLabsTokenAPI:
    """Test ElevenLabs Token Generation API (No Auth Required)

    Endpoint moved from /api/v1/realtime/elevenlabs-token
    to /api/v1/transcript/elevenlabs-token
    """

    @skip_without_elevenlabs
    def test_generate_token_success(self):
        """Test POST /api/v1/transcript/elevenlabs-token - Should return a valid token"""
        with TestClient(app) as client:
            response = client.post("/api/v1/transcript/elevenlabs-token")

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "token" in data
            assert isinstance(data["token"], str)
            assert len(data["token"]) > 0

            # Token should be non-empty string (ElevenLabs generates UUID-like tokens)
            assert data["token"].strip() != ""


class TestIslandParentsPages:
    """Test Island Parents HTML pages load without errors

    Note: The old /realtime-counseling route has been removed.
    Island Parents pages are now at /island-parents/*
    """

    def test_island_parents_login_page_loads(self):
        """Test GET /island-parents - Login page should load successfully"""
        with TestClient(app) as client:
            response = client.get("/island-parents")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_island_parents_clients_page_loads(self):
        """Test GET /island-parents/clients - Clients page should load successfully"""
        with TestClient(app) as client:
            response = client.get("/island-parents/clients")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_island_parents_recording_page_loads(self):
        """Test GET /island-parents/recording - Recording page should load successfully"""
        with TestClient(app) as client:
            response = client.get("/island-parents/recording")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_island_parents_session_page_loads(self):
        """Test GET /island-parents/session - Session page should load successfully"""
        with TestClient(app) as client:
            response = client.get("/island-parents/session")

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"
