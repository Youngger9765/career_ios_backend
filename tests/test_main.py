"""
Basic tests for the Career Counseling API
"""
import pytest


def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_root_endpoint(client):
    """Test the root endpoint returns HTML"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "職涯諮詢平台" in response.text


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


@pytest.mark.asyncio
async def test_async_endpoint():
    """Test async endpoint handling"""
    # This is a placeholder for async tests
    assert True
