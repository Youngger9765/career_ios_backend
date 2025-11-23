"""
FastAPI dependencies for authentication and authorization
"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.counselor import Counselor

# HTTP Bearer token scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> Counselor:
    """
    Get current authenticated counselor from JWT token

    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Database session

    Returns:
        Counselor model instance

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get counselor email and tenant_id from token
    email: Optional[str] = payload.get("sub")
    tenant_id: Optional[str] = payload.get("tenant_id")

    if email is None or tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query counselor from database (must match both email AND tenant_id)
    result = db.execute(
        select(Counselor).where(
            Counselor.email == email, Counselor.tenant_id == tenant_id
        )
    )
    counselor = result.scalar_one_or_none()

    if counselor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not counselor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return counselor


def get_tenant_id(
    current_user: Counselor = Depends(get_current_user),
) -> str:
    """
    Get tenant_id from current authenticated user's JWT token

    Args:
        current_user: Current authenticated counselor

    Returns:
        Tenant ID string from user's profile
    """
    return current_user.tenant_id  # type: ignore[return-value]
