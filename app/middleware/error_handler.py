"""
Error Handler Middleware

Converts all exceptions to RFC 7807 format and handles request validation errors.
"""
import logging
from typing import Callable

from fastapi import Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import format_error_response

logger = logging.getLogger(__name__)


async def rfc7807_error_handler_middleware(
    request: Request, call_next: Callable
) -> Response:
    """
    Middleware to catch all exceptions and format as RFC 7807.

    Args:
        request: Incoming request
        call_next: Next middleware/handler in chain

    Returns:
        Response with RFC 7807 formatted errors
    """
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        return handle_exception(request, exc)


def handle_exception(request: Request, exc: Exception) -> JSONResponse:
    """
    Convert exception to RFC 7807 formatted JSON response.

    Args:
        request: The request that caused the exception
        exc: The exception to handle

    Returns:
        JSONResponse with RFC 7807 formatted error
    """
    # Get request path for instance field
    instance = str(request.url.path)

    # Handle FastAPI HTTPException (including our custom RFC7807HTTPException)
    if isinstance(exc, StarletteHTTPException):
        # Check if detail is already RFC 7807 formatted (dict)
        if isinstance(exc.detail, dict):
            # Already RFC 7807 format from our custom exceptions
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
                headers=getattr(exc, "headers", None),
            )
        else:
            # Standard HTTPException - convert to RFC 7807
            error_response = format_error_response(
                status_code=exc.status_code,
                detail=str(exc.detail),
                instance=instance,
            )
            return JSONResponse(
                status_code=exc.status_code,
                content=error_response,
                headers=getattr(exc, "headers", None),
            )

    # Handle Pydantic validation errors
    if isinstance(exc, RequestValidationError):
        # Format validation errors
        error_details = []
        has_password_error = False

        for error in exc.errors():
            field_name = error["loc"][-1] if error["loc"] else ""
            error_details.append(
                {
                    "field": " -> ".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )
            if field_name in ("password", "new_password"):
                has_password_error = True

        detail = f"Validation failed: {len(error_details)} error(s)"
        error_response = format_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            instance=instance,
            errors=error_details,  # Extra field with validation details
        )

        if has_password_error:
            from app.core.password_validator import get_password_rules

            error_response["password_rules"] = get_password_rules()

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response,
        )

    # Handle all other exceptions as 500 Internal Server Error
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
    )

    error_response = format_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred",
        instance=instance,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response,
    )


# Exception handlers for FastAPI app.add_exception_handler()
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTPException and convert to RFC 7807 format.

    Args:
        request: The request that caused the exception
        exc: HTTPException instance

    Returns:
        JSONResponse with RFC 7807 formatted error
    """
    return handle_exception(request, exc)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle RequestValidationError and convert to RFC 7807 format.

    Args:
        request: The request that caused the exception
        exc: RequestValidationError instance

    Returns:
        JSONResponse with RFC 7807 formatted error
    """
    return handle_exception(request, exc)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic exceptions and convert to RFC 7807 format.

    Args:
        request: The request that caused the exception
        exc: Exception instance

    Returns:
        JSONResponse with RFC 7807 formatted error
    """
    return handle_exception(request, exc)
