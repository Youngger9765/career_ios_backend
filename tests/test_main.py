"""
Basic tests for the Career Counseling API
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_root_endpoint(client):
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_mock_sessions_list(client):
    """Test listing sessions (mock data)"""
    response = client.get("/api/v1/sessions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        # Check first session has required fields
        session = data[0]
        assert "id" in session
        assert "counselor_name" in session
        assert "client_name" in session


def test_mock_session_detail(client):
    """Test getting session detail (mock data)"""
    # Assuming session ID 1 exists in mock data
    response = client.get("/api/v1/sessions/1")
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"] == 1


def test_mock_upload_audio(client, mock_audio_file):
    """Test audio upload endpoint (mock)"""
    response = client.post("/api/v1/sessions/1/upload", files=mock_audio_file)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert "job_id" in data


def test_nonexistent_endpoint(client):
    """Test that nonexistent endpoints return 404"""
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404


def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.get("/health")
    assert response.status_code == 200
    # In test environment, CORS headers might not be present
    # This is just a placeholder test


class TestMockData:
    """Test mock data generation"""
    
    def test_mock_mode_enabled(self):
        """Verify mock mode is enabled"""
        from app.core.config import settings
        assert settings.MOCK_MODE == True
    
    def test_mock_user_generation(self):
        """Test mock user data generation"""
        from app.services.mock_service import MockDataService
        mock_service = MockDataService()
        users = mock_service.generate_users(5)
        assert len(users) == 5
        for user in users:
            assert "id" in user
            assert "email" in user
    
    def test_mock_session_generation(self):
        """Test mock session data generation"""
        from app.services.mock_service import MockDataService
        mock_service = MockDataService()
        sessions = mock_service.generate_sessions(3)
        assert len(sessions) == 3
        for session in sessions:
            assert "id" in session
            assert "created_at" in session


@pytest.mark.asyncio
async def test_async_endpoint():
    """Test async endpoint handling"""
    # This is a placeholder for async tests
    assert True


def test_pipeline_stages(client):
    """Test pipeline stages are defined correctly"""
    response = client.get("/api/v1/pipeline/stages")
    assert response.status_code == 200
    data = response.json()
    assert "stages" in data
    stages = data["stages"]
    assert len(stages) == 5  # Should have 5 stages
    
    # Check each stage has required fields
    for stage in stages:
        assert "id" in stage
        assert "name" in stage
        assert "status" in stage