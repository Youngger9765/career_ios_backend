"""
Unit tests for RFC 7807 (Problem Details) error handling

Tests the standardized error format across all HTTP status codes.
"""
from fastapi import status

from app.core.errors import (
    format_error_response,
    get_error_type_uri,
    translate_error_message,
)
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    UnauthorizedError,
    UnprocessableEntityError,
)


class TestRFC7807ErrorFormat:
    """Test RFC 7807 compliance for error responses"""

    def test_error_response_has_required_fields(self):
        """RFC 7807 requires: type, title, status, detail, instance"""
        response = format_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request",
            instance="/api/v1/test",
        )

        assert "type" in response
        assert "title" in response
        assert "status" in response
        assert "detail" in response
        assert "instance" in response

    def test_error_response_status_code_matches(self):
        """Status code in response must match HTTP status"""
        response = format_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
            instance="/api/v1/test",
        )

        assert response["status"] == 404

    def test_error_response_type_is_uri(self):
        """Type field must be a valid URI"""
        response = format_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request",
            instance="/api/v1/test",
        )

        assert response["type"].startswith("https://")
        assert "/errors/" in response["type"]

    def test_error_response_title_is_human_readable(self):
        """Title should be a short, human-readable summary"""
        response = format_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request",
            instance="/api/v1/test",
        )

        assert isinstance(response["title"], str)
        assert len(response["title"]) > 0
        assert response["title"] == "Bad Request"

    def test_error_response_detail_preserves_message(self):
        """Detail field should contain the specific error message"""
        detail_msg = "Missing required field: client_id"
        response = format_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail_msg,
            instance="/api/v1/sessions",
        )

        assert response["detail"] == detail_msg

    def test_error_response_instance_preserves_path(self):
        """Instance field should preserve the request path"""
        instance_path = "/api/v1/sessions/123"
        response = format_error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
            instance=instance_path,
        )

        assert response["instance"] == instance_path


class TestHTTPStatusCodes:
    """Test all common HTTP error status codes"""

    def test_400_bad_request_error(self):
        """Test 400 Bad Request error format"""
        error = BadRequestError(detail="Invalid input", instance="/api/v1/test")

        assert error.status_code == 400
        assert error.detail["status"] == 400
        assert error.detail["title"] == "Bad Request"
        assert "Invalid input" in error.detail["detail"]

    def test_401_unauthorized_error(self):
        """Test 401 Unauthorized error format"""
        error = UnauthorizedError(detail="Invalid credentials", instance="/api/v1/auth")

        assert error.status_code == 401
        assert error.detail["status"] == 401
        assert error.detail["title"] == "Unauthorized"
        assert "Invalid credentials" in error.detail["detail"]

    def test_403_forbidden_error(self):
        """Test 403 Forbidden error format"""
        error = ForbiddenError(
            detail="Access denied", instance="/api/v1/admin/counselors"
        )

        assert error.status_code == 403
        assert error.detail["status"] == 403
        assert error.detail["title"] == "Forbidden"
        assert "Access denied" in error.detail["detail"]

    def test_404_not_found_error(self):
        """Test 404 Not Found error format"""
        error = NotFoundError(
            detail="Session not found", instance="/api/v1/sessions/123"
        )

        assert error.status_code == 404
        assert error.detail["status"] == 404
        assert error.detail["title"] == "Not Found"
        assert "Session not found" in error.detail["detail"]

    def test_409_conflict_error(self):
        """Test 409 Conflict error format"""
        error = ConflictError(
            detail="Email already exists", instance="/api/v1/auth/register"
        )

        assert error.status_code == 409
        assert error.detail["status"] == 409
        assert error.detail["title"] == "Conflict"
        assert "Email already exists" in error.detail["detail"]

    def test_422_unprocessable_entity_error(self):
        """Test 422 Unprocessable Entity error format"""
        error = UnprocessableEntityError(
            detail="Validation failed: invalid UUID format", instance="/api/v1/sessions"
        )

        assert error.status_code == 422
        assert error.detail["status"] == 422
        assert error.detail["title"] == "Unprocessable Entity"
        assert "Validation failed" in error.detail["detail"]

    def test_500_internal_server_error(self):
        """Test 500 Internal Server Error format"""
        error = InternalServerError(
            detail="Database connection failed", instance="/api/v1/sessions"
        )

        assert error.status_code == 500
        assert error.detail["status"] == 500
        assert error.detail["title"] == "Internal Server Error"
        assert "Database connection failed" in error.detail["detail"]


class TestErrorTypeURI:
    """Test error type URI generation"""

    def test_get_error_type_uri_400(self):
        """Test type URI for 400 errors"""
        uri = get_error_type_uri(400)
        assert uri == "https://api.career-counseling.app/errors/bad-request"

    def test_get_error_type_uri_401(self):
        """Test type URI for 401 errors"""
        uri = get_error_type_uri(401)
        assert uri == "https://api.career-counseling.app/errors/unauthorized"

    def test_get_error_type_uri_403(self):
        """Test type URI for 403 errors"""
        uri = get_error_type_uri(403)
        assert uri == "https://api.career-counseling.app/errors/forbidden"

    def test_get_error_type_uri_404(self):
        """Test type URI for 404 errors"""
        uri = get_error_type_uri(404)
        assert uri == "https://api.career-counseling.app/errors/not-found"

    def test_get_error_type_uri_409(self):
        """Test type URI for 409 errors"""
        uri = get_error_type_uri(409)
        assert uri == "https://api.career-counseling.app/errors/conflict"

    def test_get_error_type_uri_422(self):
        """Test type URI for 422 errors"""
        uri = get_error_type_uri(422)
        assert uri == "https://api.career-counseling.app/errors/unprocessable-entity"

    def test_get_error_type_uri_500(self):
        """Test type URI for 500 errors"""
        uri = get_error_type_uri(500)
        assert uri == "https://api.career-counseling.app/errors/internal-server-error"

    def test_get_error_type_uri_unknown_defaults_to_server_error(self):
        """Test unknown status codes default to server-error"""
        uri = get_error_type_uri(599)
        assert uri == "https://api.career-counseling.app/errors/server-error"


class TestMultiLanguageSupport:
    """Test Chinese and English error message support"""

    def test_translate_error_message_english_400(self):
        """Test English translation for 400 error"""
        msg = translate_error_message("Invalid input", lang="en")
        assert msg == "Invalid input"  # Pass through for English

    def test_translate_error_message_chinese_404(self):
        """Test Chinese error message for 404"""
        msg = translate_error_message("Session not found", lang="zh-TW")
        assert "找不到" in msg or "未找到" in msg

    def test_translate_error_message_chinese_401(self):
        """Test Chinese error message for 401"""
        msg = translate_error_message("Invalid credentials", lang="zh-TW")
        assert "憑證" in msg or "認證" in msg or "密碼" in msg

    def test_translate_error_message_chinese_403(self):
        """Test Chinese error message for 403"""
        msg = translate_error_message("Access denied", lang="zh-TW")
        assert "拒絕" in msg or "權限" in msg or "無權" in msg

    def test_translate_error_message_defaults_to_english(self):
        """Test default language is English"""
        msg = translate_error_message("Test error")
        assert msg == "Test error"

    def test_error_response_with_chinese_detail(self):
        """Test error response preserves Chinese characters"""
        response = format_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="無效的輸入",
            instance="/api/v1/test",
        )

        assert response["detail"] == "無效的輸入"
        assert "無效" in response["detail"]


class TestErrorResponseEdgeCases:
    """Test edge cases and special scenarios"""

    def test_error_response_with_empty_detail(self):
        """Test error response handles empty detail message"""
        response = format_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="",
            instance="/api/v1/test",
        )

        assert response["detail"] == ""
        assert response["status"] == 500

    def test_error_response_with_none_instance(self):
        """Test error response handles None instance"""
        response = format_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test error",
            instance=None,
        )

        assert response["instance"] is None or response["instance"] == ""

    def test_error_response_with_long_detail_message(self):
        """Test error response handles long detail messages"""
        long_detail = "A" * 1000
        response = format_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=long_detail,
            instance="/api/v1/test",
        )

        assert response["detail"] == long_detail
        assert len(response["detail"]) == 1000

    def test_error_response_with_special_characters(self):
        """Test error response handles special characters"""
        response = format_error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input: <script>alert('xss')</script>",
            instance="/api/v1/test?param=value&other=123",
        )

        assert "<script>" in response["detail"]
        assert response["instance"] == "/api/v1/test?param=value&other=123"
