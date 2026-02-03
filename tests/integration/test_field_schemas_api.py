"""
Integration tests for Field Schemas API
TDD - Write tests first, then implement
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor


class TestFieldSchemasAPI:
    """Test Field Schemas endpoints"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-schemas@test.com",
            username="schemascounselor",
            full_name="Schemas Test Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "counselor-schemas@test.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    def test_get_client_field_schema_success(self, db_session: Session, auth_headers):
        """Test GET /api/v1/ui/field-schemas/client - Get client field schema"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/ui/field-schemas/client",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "sections" in data
            assert data["form_type"] == "client"
            # Should return field definitions for client entity

    def test_get_client_field_schema_unauthorized(self):
        """Test getting client schema without auth returns 403"""
        with TestClient(app) as client:
            response = client.get("/api/v1/ui/field-schemas/client")

            assert response.status_code == 403

    def test_get_case_field_schema_success(self, db_session: Session, auth_headers):
        """Test GET /api/v1/ui/field-schemas/case - Get case field schema"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/ui/field-schemas/case",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "sections" in data
            assert data["form_type"] == "case"
            # Should return field definitions for case entity

    def test_get_case_field_schema_unauthorized(self):
        """Test getting case schema without auth returns 403"""
        with TestClient(app) as client:
            response = client.get("/api/v1/ui/field-schemas/case")

            assert response.status_code == 403

    def test_get_client_case_field_schema_success(
        self, db_session: Session, auth_headers
    ):
        """Test GET /api/v1/ui/field-schemas/client-case - Get combined client-case field schema"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/ui/field-schemas/client-case",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            # Should return combined schema with both client and case
            assert "client" in data
            assert "case" in data
            assert "tenant_id" in data
            assert data["tenant_id"] == "career"
            # Verify client schema structure
            assert data["client"]["form_type"] == "client"
            assert "sections" in data["client"]
            # Verify case schema structure
            assert data["case"]["form_type"] == "case"
            assert "sections" in data["case"]

    def test_get_client_case_field_schema_unauthorized(self):
        """Test getting client-case schema without auth returns 403"""
        with TestClient(app) as client:
            response = client.get("/api/v1/ui/field-schemas/client-case")

            assert response.status_code == 403
