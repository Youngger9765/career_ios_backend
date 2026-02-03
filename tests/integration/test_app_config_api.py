"""Integration tests for Multi-tenant App Config API"""
from fastapi.testclient import TestClient

from app.main import app


def test_get_app_config_island_parents_success():
    """Test GET /api/v1/app/config/island_parents - happy path"""
    with TestClient(app) as client:
        response = client.get("/api/v1/app/config/island_parents")

    assert response.status_code == 200
    data = response.json()

    # Verify ONLY 3 required fields exist
    assert "terms_url" in data
    assert "privacy_url" in data
    assert "landing_page_url" in data

    # Verify removed fields are NOT present
    assert "help_url" not in data
    assert "forgot_password_url" not in data
    assert "base_url" not in data
    assert "version" not in data
    assert "maintenance_mode" not in data

    # Verify exactly 3 fields returned
    assert len(data) == 3

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
    assert "terms_url" in data


def test_get_app_config_returns_env_values():
    """Test GET /api/v1/app/config/{tenant} - returns values from environment"""
    with TestClient(app) as client:
        response = client.get("/api/v1/app/config/island_parents")

    assert response.status_code == 200
    data = response.json()

    # Verify field types (only 3 fields now)
    assert isinstance(data["terms_url"], str)
    assert isinstance(data["privacy_url"], str)
    assert isinstance(data["landing_page_url"], str)

    # Verify all fields are non-empty
    assert len(data["terms_url"]) > 0
    assert len(data["privacy_url"]) > 0
    assert len(data["landing_page_url"]) > 0


def test_get_app_config_career_tenant_success():
    """Test GET /api/v1/app/config/career - future tenant support"""
    with TestClient(app) as client:
        response = client.get("/api/v1/app/config/career")

    assert response.status_code == 200
    data = response.json()

    # Verify ONLY 3 required fields exist
    assert "terms_url" in data
    assert "privacy_url" in data
    assert "landing_page_url" in data

    # Verify removed fields are NOT present
    assert "help_url" not in data
    assert "forgot_password_url" not in data
    assert "base_url" not in data
    assert "version" not in data
    assert "maintenance_mode" not in data

    # Verify exactly 3 fields returned
    assert len(data) == 3

    # Verify Career tenant has proper URLs
    assert isinstance(data["terms_url"], str)
    assert isinstance(data["privacy_url"], str)
    assert isinstance(data["landing_page_url"], str)
    assert len(data["terms_url"]) > 0
    assert len(data["privacy_url"]) > 0
    assert len(data["landing_page_url"]) > 0
