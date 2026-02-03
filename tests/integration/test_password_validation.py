"""
Integration tests for password strength validation.

Tests verify that the registration endpoint properly enforces password strength
requirements including length, character complexity, and common password blocking.

Note: Error responses follow RFC 7807 format with errors in the 'errors' array.
"""
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app


class TestPasswordValidation:
    """Test password strength validation on registration endpoint"""

    def test_register_password_too_short(self, db_session: Session):
        """Test registration rejects password < 12 chars"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "shortpass@example.com",
                    "password": "Short1!",  # 7 characters (< 12)
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()
            # RFC 7807 format: errors are in the 'errors' array
            assert "errors" in data
            error_messages = " ".join([err.get("message", "") for err in data["errors"]])
            assert "12 characters" in error_messages.lower() or "string_too_short" in error_messages.lower()

    def test_register_password_no_uppercase(self, db_session: Session):
        """Test registration rejects password without uppercase letter"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "nouppercase@example.com",
                    "password": "validpass123!",  # No uppercase
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()
            assert "errors" in data
            error_messages = " ".join([err.get("message", "") for err in data["errors"]])
            assert "uppercase" in error_messages.lower()

    def test_register_password_no_lowercase(self, db_session: Session):
        """Test registration rejects password without lowercase letter"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "nolowercase@example.com",
                    "password": "VALIDPASS123!",  # No lowercase
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()
            assert "errors" in data
            error_messages = " ".join([err.get("message", "") for err in data["errors"]])
            assert "lowercase" in error_messages.lower()

    def test_register_password_no_digit(self, db_session: Session):
        """Test registration rejects password without digit"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "nodigit@example.com",
                    "password": "ValidPassword!",  # No digit
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()
            assert "errors" in data
            error_messages = " ".join([err.get("message", "") for err in data["errors"]])
            assert "digit" in error_messages.lower()

    def test_register_password_no_special_char(self, db_session: Session):
        """Test registration rejects password without special character"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "nospecial@example.com",
                    "password": "ValidPassword123",  # No special character
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()
            assert "errors" in data
            error_messages = " ".join([err.get("message", "") for err in data["errors"]])
            assert "special character" in error_messages.lower()

    def test_register_common_password_rejected(self, db_session: Session):
        """Test registration rejects common passwords"""
        with TestClient(app) as client:
            # Try a password from the common password list
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "commonpass@example.com",
                    "password": "Password123!",  # Common password (password123!)
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()
            assert "errors" in data
            error_messages = " ".join([err.get("message", "") for err in data["errors"]])
            assert "common" in error_messages.lower() or "unique" in error_messages.lower()

    def test_register_valid_strong_password(self, db_session: Session):
        """Test registration accepts valid strong password"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "strongpass@example.com",
                    "password": "MyV3ry$tr0ngP@ss",  # Meets all requirements
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert isinstance(data["access_token"], str)
            assert len(data["access_token"]) > 0

    def test_password_validation_error_messages_clear(self, db_session: Session):
        """Test validation errors provide clear feedback"""
        with TestClient(app) as client:
            # Try password with multiple violations (too short, no uppercase, no special char)
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "multiviolation@example.com",
                    "password": "short123",  # Too short (8 chars), no uppercase, no special char
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()
            assert "errors" in data

            # Error message should mention specific violations
            error_messages = " ".join([err.get("message", "") for err in data["errors"]])
            assert len(error_messages) > 0
            # Should contain at least one validation requirement hint
            assert any(
                keyword in error_messages.lower()
                for keyword in ["character", "uppercase", "special", "length", "12"]
            )

    def test_register_password_exactly_12_chars_valid(self, db_session: Session):
        """Test registration accepts password with exactly 12 characters (boundary test)"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "exactly12@example.com",
                    "password": "Valid1Pass!2",  # Exactly 12 characters
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data

    def test_register_password_11_chars_invalid(self, db_session: Session):
        """Test registration rejects password with exactly 11 characters (boundary test)"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "exactly11@example.com",
                    "password": "Valid1Pass!",  # Exactly 11 characters
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()
            assert "errors" in data
            error_messages = " ".join([err.get("message", "") for err in data["errors"]])
            assert "12" in error_messages or "length" in error_messages.lower()

    def test_register_special_char_at_symbol_accepted(self, db_session: Session):
        """Test registration accepts password with @ special character"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "specialchar@example.com",
                    "password": "ValidP@ssw0rd123",  # @ is special character
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data

    def test_register_common_password_case_insensitive(self, db_session: Session):
        """Test common password check is case-insensitive"""
        with TestClient(app) as client:
            # "password123!" is in common password list
            # Try uppercase version
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "casetest@example.com",
                    "password": "PASSWORD123!",  # Uppercase version of common password
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()
            assert "errors" in data
            error_messages = " ".join([err.get("message", "") for err in data["errors"]])
            assert "common" in error_messages.lower() or "unique" in error_messages.lower()

    def test_register_multiple_validation_errors(self, db_session: Session):
        """Test password with multiple violations returns comprehensive error"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "multierror@example.com",
                    "password": "abc",  # Too short, no uppercase, no digit, no special char
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()
            assert "errors" in data
            # Should have at least one error
            assert len(data["errors"]) > 0

    def test_register_password_strength_error_format(self, db_session: Session):
        """Test password validation errors follow RFC 7807 format"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "format@example.com",
                    "password": "weak",  # Multiple violations
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 422
            data = response.json()

            # RFC 7807 required fields
            assert "type" in data
            assert "title" in data
            assert "status" in data
            assert data["status"] == 422
            assert "detail" in data
            assert "errors" in data

            # Errors array should contain field, message, type
            for error in data["errors"]:
                assert "field" in error
                assert "message" in error
                assert "type" in error
                assert "password" in error["field"]
