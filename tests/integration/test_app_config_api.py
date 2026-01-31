"""Integration tests for App Config API"""
from fastapi.testclient import TestClient

from app.main import app


def test_get_app_config_success():
    """Test GET /api/v1/app/config - happy path"""
    with TestClient(app) as client:
        response = client.get("/api/v1/app/config")

    assert response.status_code == 200
    data = response.json()

    # Verify all required fields exist
    assert "terms_url" in data
    assert "privacy_url" in data
    assert "landing_page_url" in data
    assert "help_url" in data
    assert "forgot_password_url" in data
    assert "base_url" in data
    assert "version" in data
    assert "maintenance_mode" in data

    # Verify field types
    assert isinstance(data["terms_url"], str)
    assert isinstance(data["privacy_url"], str)
    assert isinstance(data["landing_page_url"], str)
    assert isinstance(data["help_url"], str)
    assert isinstance(data["forgot_password_url"], str)
    assert isinstance(data["base_url"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["maintenance_mode"], bool)


def test_get_app_config_no_auth_required():
    """Test GET /api/v1/app/config - no authentication required"""
    with TestClient(app) as client:
        # No auth headers - should still work
        response = client.get("/api/v1/app/config")

    assert response.status_code == 200
    data = response.json()
    assert "version" in data


def test_get_app_config_returns_env_values():
    """Test GET /api/v1/app/config - returns values from environment"""
    with TestClient(app) as client:
        response = client.get("/api/v1/app/config")

    assert response.status_code == 200
    data = response.json()

    # Should have default values from settings
    assert data["version"] == "1.0.0"
    assert data["maintenance_mode"] is False
