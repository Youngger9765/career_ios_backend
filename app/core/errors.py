"""
RFC 7807 (Problem Details) Error Handling Utilities

Provides utility functions for formatting errors according to RFC 7807 standard.
"""
from typing import Any, Dict, Optional


def get_error_type_uri(status_code: int) -> str:
    """
    Generate RFC 7807 type URI for error status code.

    Args:
        status_code: HTTP status code

    Returns:
        URI string for the error type
    """
    error_types = {
        400: "bad-request",
        401: "unauthorized",
        403: "forbidden",
        404: "not-found",
        409: "conflict",
        422: "unprocessable-entity",
        500: "internal-server-error",
    }

    error_type = error_types.get(status_code, "server-error")
    return f"https://api.career-counseling.app/errors/{error_type}"


def get_error_title(status_code: int) -> str:
    """
    Get human-readable title for HTTP status code.

    Args:
        status_code: HTTP status code

    Returns:
        Human-readable error title
    """
    titles = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
    }

    return titles.get(status_code, "Server Error")


def translate_error_message(message: str, lang: str = "en") -> str:
    """
    Translate error message to specified language.

    Args:
        message: English error message
        lang: Target language code (en, zh-TW)

    Returns:
        Translated error message
    """
    if lang == "en":
        return message

    # Chinese translations for common error messages
    translations = {
        "Session not found": "找不到會談記錄",
        "Invalid credentials": "無效的認證憑證",
        "Access denied": "拒絕存取",
        "Invalid input": "無效的輸入",
        "Email already exists": "電子郵件已存在",
        "Username already exists": "使用者名稱已存在",
        "Database connection failed": "資料庫連線失敗",
    }

    # Try exact match first
    if message in translations:
        return translations[message]

    # Try partial match for common phrases
    for en_phrase, zh_phrase in translations.items():
        if en_phrase.lower() in message.lower():
            return message.replace(en_phrase, zh_phrase)

    # Return original if no translation found
    return message


def format_error_response(
    status_code: int,
    detail: str,
    instance: Optional[str] = None,
    lang: str = "en",
    **extra_fields: Any,
) -> Dict[str, Any]:
    """
    Format error response according to RFC 7807.

    Args:
        status_code: HTTP status code
        detail: Specific error message
        instance: URI of the request that caused the error
        lang: Language for error message (default: en)
        **extra_fields: Additional fields to include in response

    Returns:
        RFC 7807 formatted error response
    """
    response = {
        "type": get_error_type_uri(status_code),
        "title": get_error_title(status_code),
        "status": status_code,
        "detail": detail,
        "instance": instance or "",
    }

    # Add any extra fields
    response.update(extra_fields)

    return response
