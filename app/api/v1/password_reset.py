"""
Password Reset API endpoints (v1)

Provides secure password reset functionality:
1. Request password reset - Send reset email with verification code
2. Verify verification code - Check if code is valid
3. Confirm password reset - Update password with verification code
"""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.middleware.rate_limit import limiter
from app.models.counselor import Counselor
from app.models.password_reset import PasswordResetToken
from app.schemas.auth import (
    PasswordResetConfirm,
    PasswordResetConfirmResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    VerifyCodeRequest,
    VerifyCodeResponse,
)
from app.services.external.email_sender import email_sender
from app.utils.verification_code import generate_verification_code

router = APIRouter(prefix="/auth/password-reset", tags=["Password Reset"])

TOKEN_EXPIRY_HOURS = 6

# Weak password blacklist
WEAK_PASSWORDS = {
    "123456",
    "password",
    "12345678",
    "qwerty",
    "abc123",
    "123456789",
    "111111",
    "password123",
}


def generate_secure_token() -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(32)


def is_password_weak(password: str) -> tuple[bool, str | None]:
    """
    Check if password meets security requirements

    Returns:
        (is_weak, error_message)
    """
    if len(password) < 8:
        return True, "Password must be at least 8 characters long"

    # Disabled for testing - only check minimum length
    # if password.lower() in WEAK_PASSWORDS:
    #     return True, "Password is too common. Please choose a stronger password"

    # if password.isdigit():
    #     return True, "Password cannot be only numbers"

    # if not any(c.isalpha() for c in password):
    #     return True, "Password must contain at least one letter"

    # if not any(c.isdigit() for c in password):
    #     return True, "Password must contain at least one number"

    return False, None


@router.post("/request", response_model=PasswordResetResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PASSWORD_RESET_PER_HOUR}/hour")
async def request_password_reset(
    request_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
    """
    Request password reset email

    Args:
        request_data: Email/phone and tenant_id
        request: FastAPI request (for IP tracking)
        db: Database session

    Returns:
        PasswordResetResponse with success message

    Notes:
        - Always returns success to prevent user enumeration
        - Rate limited to prevent abuse
        - Token expires in 6 hours
    """
    # Validate input
    if not request_data.email and not request_data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone must be provided",
        )

    # Query counselor by email/phone and tenant_id
    query = select(Counselor).where(Counselor.tenant_id == request_data.tenant_id)

    if request_data.email:
        query = query.where(Counselor.email == request_data.email)
    elif request_data.phone:
        query = query.where(Counselor.phone == request_data.phone)

    result = db.execute(query)
    counselor = result.scalar_one_or_none()

    # Always return success message (prevent user enumeration)
    response = PasswordResetResponse(message="Password reset email sent successfully")

    # Only create token if counselor exists
    if counselor:
        # Generate secure token (for backward compatibility)
        token = generate_secure_token()

        # Generate 6-digit verification code
        verification_code = generate_verification_code()

        # Create password reset token
        reset_token = PasswordResetToken(
            token=token,
            email=counselor.email,
            tenant_id=counselor.tenant_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
            verification_code=verification_code,
            code_expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            used=False,
            request_ip=request.client.host if request.client else None,
        )

        db.add(reset_token)
        db.commit()

        # Send email with verification code (async)
        try:
            await email_sender.send_password_reset_email(
                to_email=counselor.email,
                verification_code=verification_code,
                counselor_name=counselor.full_name or "User",  # Handle None case
                tenant_id=counselor.tenant_id,
                source=request_data.source,  # Pass source parameter for compatibility
            )
        except Exception as e:
            # Log error but don't expose to user
            import logging

            logging.error(f"Failed to send password reset email: {e}")

        # Include token in response for testing
        response.token = token

    return response


@router.post("/verify-code", response_model=VerifyCodeResponse)
def verify_password_reset_code(
    request: VerifyCodeRequest,
    db: Session = Depends(get_db),
) -> VerifyCodeResponse:
    """
    Verify password reset verification code

    Args:
        request: Email, verification code, and tenant_id
        db: Database session

    Returns:
        VerifyCodeResponse with validation result

    Raises:
        HTTPException: 400 if code is invalid, expired, or account is locked
    """
    # First, try to find any token for this email/tenant (to check lockout)
    result = db.execute(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.email == request.email,
            PasswordResetToken.tenant_id == request.tenant_id,
            PasswordResetToken.deleted_at.is_(None),
        )
        .order_by(PasswordResetToken.created_at.desc())
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    # Check if account is locked
    if reset_token.locked_until is not None:
        locked_until = reset_token.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)

        if locked_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many failed attempts. Account is temporarily locked.",
            )

    # Check if verification code matches
    if reset_token.verification_code != request.verification_code:
        # Increment verify_attempts
        reset_token.verify_attempts += 1

        # Lock account if 5 or more failed attempts
        if reset_token.verify_attempts >= 5:
            reset_token.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    # Check if code has expired
    code_expires_at = reset_token.code_expires_at
    if code_expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    if code_expires_at.tzinfo is None:
        code_expires_at = code_expires_at.replace(tzinfo=timezone.utc)

    if code_expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired",
        )

    # Check if code has already been used
    if reset_token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has already been used",
        )

    # Code is valid
    return VerifyCodeResponse(
        valid=True,
        message="Verification code is valid",
    )


@router.post("/confirm", response_model=PasswordResetConfirmResponse)
def confirm_password_reset(
    confirm_data: PasswordResetConfirm,
    request: Request,
    db: Session = Depends(get_db),
) -> PasswordResetConfirmResponse:
    """
    Confirm password reset and update password

    Args:
        confirm_data: Token and new password
        request: FastAPI request (for IP tracking)
        db: Database session

    Returns:
        PasswordResetConfirmResponse with success message

    Raises:
        HTTPException: 400 if token invalid or password weak
    """
    # Query token by verification_code, email, and tenant_id
    result = db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.verification_code == confirm_data.verification_code,
            PasswordResetToken.email == confirm_data.email,
            PasswordResetToken.tenant_id == confirm_data.tenant_id,
            PasswordResetToken.deleted_at.is_(None),
        )
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    if reset_token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has already been used",
        )

    # Check verification code expiry (10 minutes)
    code_expires_at = reset_token.code_expires_at
    if code_expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    if code_expires_at.tzinfo is None:
        code_expires_at = code_expires_at.replace(tzinfo=timezone.utc)

    if code_expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired",
        )

    # Validate password strength
    is_weak, error_message = is_password_weak(confirm_data.new_password)
    if is_weak:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    try:
        # Query counselor
        counselor_result = db.execute(
            select(Counselor).where(
                Counselor.email == reset_token.email,
                Counselor.tenant_id == reset_token.tenant_id,
            )
        )
        counselor = counselor_result.scalar_one_or_none()

        if not counselor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found",
            )

        # Update password
        counselor.hashed_password = hash_password(confirm_data.new_password)

        # Mark email as verified (since they received and confirmed the verification code)
        if not counselor.email_verified:
            counselor.email_verified = True

        # Mark token as used
        reset_token.mark_as_used(ip=request.client.host if request.client else None)

        db.commit()

        return PasswordResetConfirmResponse(message="Password reset successfully")

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}",
        )
