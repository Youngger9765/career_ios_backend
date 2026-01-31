"""Integration tests for Multi-tenant App Config API"""
from fastapi.testclient import TestClient

from app.main import app


def test_get_app_config_island_parents_success():
    """Test GET /api/v1/app/config/island_parents - happy path"""
    with TestClient(app) as client:
        response = client.get("/api/v1/app/config/island_parents")

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

    # Verify Island Parents URLs
    assert "comma.study/island_parents" in data["terms_url"]
    assert "comma.study/island_parents" in data["privacy_url"]
    assert "comma.study/island_parents" in data["landing_page_url"]


def test_get_app_config_invalid_tenant_404():
    """Test GET /api/v1/app/config/invalid_tenant - should return 404"""
    with TestClient(app) as client:
        response = client.get("/api/v1/app/config/invalid_tenant")

    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_app_config_no_auth_required():
    """Test GET /api/v1/app/config/{tenant} - no authentication required"""
    with TestClient(app) as client:
        # No auth headers - should still work
        response = client.get("/api/v1/app/config/island_parents")

    assert response.status_code == 200
    data = response.json()
    assert "version" in data


def test_get_app_config_returns_env_values():
    """Test GET /api/v1/app/config/{tenant} - returns values from environment"""
    with TestClient(app) as client:
        response = client.get("/api/v1/app/config/island_parents")

    assert response.status_code == 200
    data = response.json()

    # Should have default values from settings
    assert data["version"] == "1.0.0"
    assert data["maintenance_mode"] is False

    # Verify field types
    assert isinstance(data["terms_url"], str)
    assert isinstance(data["privacy_url"], str)
    assert isinstance(data["landing_page_url"], str)
    assert isinstance(data["help_url"], str)
    assert isinstance(data["forgot_password_url"], str)
    assert isinstance(data["base_url"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["maintenance_mode"], bool)


def test_get_app_config_career_tenant_success():
    """Test GET /api/v1/app/config/career - future tenant support"""
    with TestClient(app) as client:
        response = client.get("/api/v1/app/config/career")

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

    # Verify Career tenant has proper URLs
    assert isinstance(data["terms_url"], str)
    assert isinstance(data["privacy_url"], str)
    assert isinstance(data["landing_page_url"], str)
    assert len(data["terms_url"]) > 0
    assert len(data["privacy_url"]) > 0
    assert len(data["landing_page_url"]) > 0
