"""Integration tests for Usage Stats API endpoint."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.counselor import Counselor

client = TestClient(app)


def test_get_usage_stats_subscription(
    db_session: Session, test_counselor_subscription: Counselor, auth_headers_subscription: dict
) -> None:
    """Test GET /api/v1/usage/stats returns subscription stats."""
    response = client.get("/api/v1/usage/stats", headers=auth_headers_subscription)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["billing_mode"] == "subscription"
    assert data["monthly_limit_minutes"] == 60
    assert data["monthly_used_minutes"] == 0
    assert data["monthly_remaining_minutes"] == 60
    assert data["usage_percentage"] == 0.0
    assert data["is_limit_reached"] is False
    assert "usage_period_start" in data
    assert "usage_period_end" in data

    # Prepaid fields should be None
    assert data["available_credits"] is None


def test_get_usage_stats_prepaid(
    db_session: Session, test_counselor_prepaid: Counselor, auth_headers_prepaid: dict
) -> None:
    """Test GET /api/v1/usage/stats returns prepaid stats."""
    response = client.get("/api/v1/usage/stats", headers=auth_headers_prepaid)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["billing_mode"] == "prepaid"
    assert data["available_credits"] == 100.0

    # Subscription fields should be None
    assert data["monthly_limit_minutes"] is None
    assert data["monthly_used_minutes"] is None
    assert data["monthly_remaining_minutes"] is None
    assert data["usage_percentage"] is None
    assert data["is_limit_reached"] is None
    assert data["usage_period_start"] is None
    assert data["usage_period_end"] is None


def test_get_usage_stats_unauthorized() -> None:
    """Test GET /api/v1/usage/stats returns 401 without auth."""
    response = client.get("/api/v1/usage/stats")

    assert response.status_code == 403  # HTTPBearer returns 403 for missing token
