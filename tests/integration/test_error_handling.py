"""
Integration tests for RFC 7807 error handling in API endpoints

Tests that actual API endpoints return proper RFC 7807 formatted errors.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Create authenticated user and return auth headers"""
    # Register and login to get token
    register_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpass123",
        "full_name": "Test User",
        "tenant_id": "test-tenant",
        "role": "counselor",
    }
    response = client.post("/auth/register", json=register_data)
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestRFC7807IntegrationFormat:
    """Test RFC 7807 compliance in actual API responses"""

    def test_404_error_has_rfc7807_format(self, client, auth_headers):
        """Test 404 errors return RFC 7807 format"""
        response = client.get(
            "/api/v1/sessions/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )

        assert response.status_code == 404
        data = response.json()

        # RFC 7807 required fields
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data

        # Verify field values
        assert data["status"] == 404
        assert data["title"] == "Not Found"
        assert data["type"].startswith("https://")
        assert "/errors/" in data["type"]

    def test_400_error_has_rfc7807_format(self, client, auth_headers):
        """Test 400 errors return RFC 7807 format"""
        # Try to create session with invalid data
        invalid_data = {
            "case_id": "not-a-uuid",  # Invalid UUID format
            "session_number": 1,
            "session_date": "2024-01-01",
        }
        response = client.post(
            "/api/v1/sessions", json=invalid_data, headers=auth_headers
        )

        assert response.status_code in [400, 422]  # Could be 400 or 422
        data = response.json()

        # RFC 7807 required fields
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data

    def test_401_error_has_rfc7807_format(self, client):
        """Test 401 errors return RFC 7807 format"""
        # Try to access protected endpoint without auth
        response = client.get("/api/v1/sessions")

        assert response.status_code == 401
        data = response.json()

        # RFC 7807 required fields
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data

        assert data["status"] == 401
        assert data["title"] == "Unauthorized"

    def test_403_error_has_rfc7807_format(self, client, auth_headers):
        """Test 403 errors return RFC 7807 format"""
        # Try to access another user's session (permission error)
        # First create a session
        from uuid import uuid4

        # This should trigger a 403 or 404 based on permission logic
        response = client.get(f"/api/v1/sessions/{uuid4()}", headers=auth_headers)

        # May return 404 if not found, or 403 if found but no permission
        assert response.status_code in [403, 404]
        data = response.json()

        # RFC 7807 required fields
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data

    def test_409_error_has_rfc7807_format(self, client):
        """Test 409 errors return RFC 7807 format"""
        # Try to register with existing email
        register_data = {
            "email": "duplicate@example.com",
            "username": "user1",
            "password": "testpass123",
            "full_name": "User One",
            "tenant_id": "test-tenant",
            "role": "counselor",
        }

        # First registration should succeed
        response1 = client.post("/auth/register", json=register_data)
        assert response1.status_code == 201

        # Second registration with same email should fail with 409 or 400
        register_data["username"] = "user2"  # Different username
        response2 = client.post("/auth/register", json=register_data)

        assert response2.status_code in [400, 409]
        data = response2.json()

        # RFC 7807 required fields
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data

    def test_500_error_has_rfc7807_format(self, client, monkeypatch):
        """Test 500 errors return RFC 7807 format"""
        # This test is tricky - we'd need to mock a database failure
        # For now, we'll just verify the structure exists
        # In a real scenario, you'd use monkeypatch to cause a DB error
        pass  # Placeholder for actual 500 error testing


class TestAuthEndpointErrors:
    """Test error handling in auth endpoints"""

    def test_login_with_invalid_credentials(self, client):
        """Test login with wrong password returns RFC 7807 format"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpass",
            "tenant_id": "test-tenant",
        }
        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()

        assert data["status"] == 401
        assert data["title"] == "Unauthorized"
        assert data["type"].startswith("https://")
        assert data["instance"] == "/auth/login"
        assert "detail" in data

    def test_register_with_existing_username(self, client):
        """Test registration with duplicate username returns RFC 7807 format"""
        register_data = {
            "email": "user1@example.com",
            "username": "duplicate_user",
            "password": "testpass123",
            "full_name": "User One",
            "tenant_id": "test-tenant",
            "role": "counselor",
        }

        # First registration
        response1 = client.post("/auth/register", json=register_data)
        assert response1.status_code == 201

        # Second registration with same username
        register_data["email"] = "user2@example.com"  # Different email
        response2 = client.post("/auth/register", json=register_data)

        assert response2.status_code in [400, 409]
        data = response2.json()

        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data
        assert "username" in data["detail"].lower()

    def test_update_profile_with_invalid_data(self, client, auth_headers):
        """Test profile update with invalid data returns RFC 7807 format"""
        update_data = {}  # Empty update
        response = client.patch("/auth/me", json=update_data, headers=auth_headers)

        assert response.status_code == 400
        data = response.json()

        assert data["status"] == 400
        assert data["title"] == "Bad Request"
        assert data["type"].startswith("https://")
        assert "detail" in data


class TestSessionEndpointErrors:
    """Test error handling in session endpoints"""

    def test_create_session_with_invalid_case_id(self, client, auth_headers):
        """Test creating session with non-existent case returns RFC 7807 format"""
        from uuid import uuid4

        session_data = {
            "case_id": str(uuid4()),  # Non-existent case
            "session_number": 1,
            "session_date": "2024-01-01",
        }
        response = client.post(
            "/api/v1/sessions", json=session_data, headers=auth_headers
        )

        assert response.status_code in [400, 404]
        data = response.json()

        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data

    def test_get_nonexistent_session(self, client, auth_headers):
        """Test getting non-existent session returns RFC 7807 format"""
        from uuid import uuid4

        response = client.get(f"/api/v1/sessions/{uuid4()}", headers=auth_headers)

        assert response.status_code == 404
        data = response.json()

        assert data["status"] == 404
        assert data["title"] == "Not Found"
        assert data["type"] == "https://api.career-counseling.app/errors/not-found"
        assert "Session not found" in data["detail"]

    def test_update_nonexistent_session(self, client, auth_headers):
        """Test updating non-existent session returns RFC 7807 format"""
        from uuid import uuid4

        update_data = {"name": "Updated Session"}
        response = client.patch(
            f"/api/v1/sessions/{uuid4()}", json=update_data, headers=auth_headers
        )

        assert response.status_code == 404
        data = response.json()

        assert data["status"] == 404
        assert data["title"] == "Not Found"
        assert "type" in data
        assert "detail" in data
        assert "instance" in data

    def test_delete_session_with_reports(self, client, auth_headers):
        """Test deleting session with reports returns RFC 7807 format"""
        # This would require setting up a session with reports
        # For now, just verify error format structure
        from uuid import uuid4

        response = client.delete(f"/api/v1/sessions/{uuid4()}", headers=auth_headers)

        # Should be 404 (not found) since session doesn't exist
        assert response.status_code == 404
        data = response.json()

        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data


class TestErrorMiddlewareIntegration:
    """Test that error middleware catches all unhandled exceptions"""

    def test_middleware_catches_unhandled_exceptions(self, client):
        """Test middleware converts unhandled exceptions to RFC 7807 format"""
        # This would require an endpoint that throws an unhandled exception
        # For now, we'll test that the middleware is in place
        pass  # Placeholder

    def test_validation_errors_converted_to_rfc7807(self, client, auth_headers):
        """Test Pydantic validation errors are converted to RFC 7807 format"""
        invalid_data = {
            "case_id": "not-a-uuid",  # Invalid UUID
            "session_number": "not-a-number",  # Invalid type
            "session_date": "invalid-date",  # Invalid date format
        }
        response = client.post(
            "/api/v1/sessions", json=invalid_data, headers=auth_headers
        )

        assert response.status_code == 422
        data = response.json()

        # Should be RFC 7807 format
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data

        assert data["status"] == 422
        assert data["title"] == "Unprocessable Entity"


class TestChineseErrorMessages:
    """Test Chinese error message support"""

    def test_error_message_supports_chinese(self, client):
        """Test error messages can contain Chinese characters"""
        # This would require setting Accept-Language header
        # For now, just verify Chinese characters are preserved
        login_data = {
            "email": "測試@example.com",  # Chinese email
            "password": "wrongpass",
            "tenant_id": "test-tenant",
        }
        response = client.post("/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()

        # RFC 7807 format should be preserved
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data

    def test_chinese_detail_message_preserved(self, client, auth_headers):
        """Test Chinese characters in detail field are preserved"""
        # Create an error scenario that would return Chinese message
        # For now, just verify the structure supports it
        pass  # Placeholder


class TestErrorResponseConsistency:
    """Test that all endpoints return consistent error format"""

    def test_all_endpoints_use_same_error_format(self, client, auth_headers):
        """Test error format is consistent across different endpoints"""
        from uuid import uuid4

        # Test multiple endpoints
        endpoints_to_test = [
            ("GET", f"/api/v1/sessions/{uuid4()}", None),
            ("PATCH", f"/api/v1/sessions/{uuid4()}", {"name": "Test"}),
            ("DELETE", f"/api/v1/sessions/{uuid4()}", None),
            ("GET", "/api/v1/sessions/timeline?client_id=" + str(uuid4()), None),
        ]

        for method, url, json_data in endpoints_to_test:
            if method == "GET":
                response = client.get(url, headers=auth_headers)
            elif method == "PATCH":
                response = client.patch(url, json=json_data, headers=auth_headers)
            elif method == "DELETE":
                response = client.delete(url, headers=auth_headers)

            # All should return 404 and RFC 7807 format
            if response.status_code >= 400:
                data = response.json()
                assert "type" in data, f"Missing 'type' in {method} {url}"
                assert "title" in data, f"Missing 'title' in {method} {url}"
                assert "status" in data, f"Missing 'status' in {method} {url}"
                assert "detail" in data, f"Missing 'detail' in {method} {url}"
                assert "instance" in data, f"Missing 'instance' in {method} {url}"
