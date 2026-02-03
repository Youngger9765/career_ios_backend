"""
Email verification utilities using JWT tokens.

Provides token generation and verification for email confirmation workflow.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt

from app.core.config import settings


def create_verification_token(email: str, tenant_id: str) -> str:
    """
    Generate a JWT token for email verification.

    Args:
        email: User's email address
        tenant_id: Tenant identifier

    Returns:
        JWT token string valid for VERIFICATION_TOKEN_EXPIRE_HOURS
    """
    expires_delta = timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {
        "sub": email,
        "tenant_id": tenant_id,
        "type": "email_verification",
        "exp": expire,
    }

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_verification_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode email verification token.

    Args:
        token: JWT token to verify

    Returns:
        Decoded token payload with 'sub' (email) and 'tenant_id'

    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # Verify token type
        token_type: str | None = payload.get("type")
        if token_type != "email_verification":
            raise JWTError("Invalid token type")

        email: str | None = payload.get("sub")
        tenant_id: str | None = payload.get("tenant_id")

        if email is None or tenant_id is None:
            raise JWTError("Invalid token payload")

        return {"email": email, "tenant_id": tenant_id}

    except JWTError as e:
        raise JWTError(f"Token verification failed: {str(e)}")
