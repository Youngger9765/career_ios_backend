"""
RevenueCat Service - Manage RevenueCat subscriber lifecycle
"""
import logging
from urllib.parse import quote

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

REVENUECAT_API_BASE = "https://api.revenuecat.com/v1"
REQUEST_TIMEOUT = 10  # seconds


def delete_customer(email: str, user_id: str) -> bool:
    """
    Delete a RevenueCat subscriber by calling the DELETE subscribers API.

    The app_user_id is constructed as ``{email}|{user_id}`` and URL-encoded
    before being embedded in the request path.

    Args:
        email: The counselor's original (pre-anonymization) email address.
        user_id: The counselor's UUID as a string.

    Returns:
        True if the subscriber was deleted successfully (HTTP 200/204).
        False if the secret key is missing, the API returned an error, or any
        exception occurred.  Failures are logged but never propagate.
    """
    secret_key = settings.REVENUECAT_SECRET_KEY
    if not secret_key:
        logger.warning(
            "REVENUECAT_SECRET_KEY is not configured; skipping RevenueCat delete"
        )
        return False

    app_user_id = f"{email}|{user_id}"
    encoded_app_user_id = quote(app_user_id, safe="")
    url = f"{REVENUECAT_API_BASE}/subscribers/{encoded_app_user_id}"

    headers = {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.delete(url, headers=headers)

        if response.status_code in (200, 204):
            logger.info(
                "RevenueCat subscriber deleted successfully for user_id=%s", user_id
            )
            return True

        logger.error(
            "RevenueCat delete failed for user_id=%s: HTTP %s %s",
            user_id,
            response.status_code,
            response.text,
        )
        return False

    except Exception as exc:
        logger.error(
            "RevenueCat delete raised an exception for user_id=%s: %s",
            user_id,
            exc,
        )
        return False
