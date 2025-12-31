"""
Custom Exception Classes with RFC 7807 Support

All custom exceptions return RFC 7807 formatted error details.
"""
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

from app.core.errors import format_error_response


class RFC7807HTTPException(HTTPException):
    """
    Base HTTPException with RFC 7807 formatting support.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        instance: Optional[str] = None,
        lang: str = "en",
        headers: Optional[Dict[str, str]] = None,
        **extra_fields: Any,
    ):
        """
        Initialize RFC 7807 compliant exception.

        Args:
            status_code: HTTP status code
            detail: Specific error message
            instance: URI of the request that caused the error
            lang: Language for error message
            headers: Optional HTTP headers
            **extra_fields: Additional fields for error response
        """
        # Format error as RFC 7807
        error_detail = format_error_response(
            status_code=status_code,
            detail=detail,
            instance=instance,
            lang=lang,
            **extra_fields,
        )

        super().__init__(status_code=status_code, detail=error_detail, headers=headers)


class BadRequestError(RFC7807HTTPException):
    """400 Bad Request"""

    def __init__(
        self,
        detail: str = "Bad request",
        instance: Optional[str] = None,
        **extra_fields: Any,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            instance=instance,
            **extra_fields,
        )


class UnauthorizedError(RFC7807HTTPException):
    """401 Unauthorized"""

    def __init__(
        self,
        detail: str = "Unauthorized",
        instance: Optional[str] = None,
        **extra_fields: Any,
    ):
        headers = {"WWW-Authenticate": "Bearer"}
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            instance=instance,
            headers=headers,
            **extra_fields,
        )


class ForbiddenError(RFC7807HTTPException):
    """403 Forbidden"""

    def __init__(
        self,
        detail: str = "Access forbidden",
        instance: Optional[str] = None,
        **extra_fields: Any,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            instance=instance,
            **extra_fields,
        )


class NotFoundError(RFC7807HTTPException):
    """404 Not Found"""

    def __init__(
        self,
        detail: str = "Resource not found",
        instance: Optional[str] = None,
        **extra_fields: Any,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            instance=instance,
            **extra_fields,
        )


class ConflictError(RFC7807HTTPException):
    """409 Conflict"""

    def __init__(
        self,
        detail: str = "Resource conflict",
        instance: Optional[str] = None,
        **extra_fields: Any,
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            instance=instance,
            **extra_fields,
        )


class UnprocessableEntityError(RFC7807HTTPException):
    """422 Unprocessable Entity"""

    def __init__(
        self,
        detail: str = "Unprocessable entity",
        instance: Optional[str] = None,
        **extra_fields: Any,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            instance=instance,
            **extra_fields,
        )


class InternalServerError(RFC7807HTTPException):
    """500 Internal Server Error"""

    def __init__(
        self,
        detail: str = "Internal server error",
        instance: Optional[str] = None,
        **extra_fields: Any,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            instance=instance,
            **extra_fields,
        )
