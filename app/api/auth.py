"""
Authentication API endpoints
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.email_verification import (
    create_verification_token,
    verify_verification_token,
)
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InternalServerError,
    UnauthorizedError,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.middleware.rate_limit import limiter
from app.models.counselor import Counselor
from app.schemas.auth import (
    CounselorInfo,
    CounselorUpdate,
    LoginRequest,
    RegisterRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    TokenResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.services.external.email_sender import EmailSenderService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit(f"{settings.RATE_LIMIT_REGISTER_PER_HOUR}/hour")
async def register(
    register_data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Register a new counselor account

    Args:
        register_data: Registration information (email, username, password, etc.)
        db: Database session

    Returns:
        TokenResponse with access_token (auto-login after registration)

    Raises:
        HTTPException: 400 if email+tenant_id or username already exists
    """
    # Check if email + tenant_id combination already exists
    result = db.execute(
        select(Counselor).where(
            Counselor.email == register_data.email,
            Counselor.tenant_id == register_data.tenant_id,
        )
    )
    if result.scalar_one_or_none():
        raise ConflictError(
            detail=f"Email '{register_data.email}' already exists for tenant '{register_data.tenant_id}'",
            instance=str(request.url.path),
        )

    # Check username uniqueness if provided (only if not None)
    if register_data.username is not None:
        result = db.execute(
            select(Counselor).where(Counselor.username == register_data.username)
        )
        if result.scalar_one_or_none():
            raise ConflictError(
                detail=f"Username '{register_data.username}' already exists",
                instance=str(request.url.path),
            )

    try:
        # Set is_active based on email verification setting
        is_active_value = not settings.ENABLE_EMAIL_VERIFICATION

        # Create new counselor (username and full_name are optional, can be None)
        counselor = Counselor(
            email=register_data.email,
            username=register_data.username,  # Can be None or provided value
            full_name=register_data.full_name,  # Can be None or provided value
            hashed_password=hash_password(register_data.password),
            tenant_id=register_data.tenant_id,
            role=register_data.role,
            is_active=is_active_value,  # False if verification enabled
        )

        db.add(counselor)
        db.commit()
        db.refresh(counselor)

        # Send verification email if enabled
        if settings.ENABLE_EMAIL_VERIFICATION:
            verification_token = create_verification_token(
                counselor.email, counselor.tenant_id
            )
            email_service = EmailSenderService()
            await email_service.send_verification_email(
                to_email=counselor.email,
                verification_token=verification_token,
                tenant_id=counselor.tenant_id,
            )

        # Auto-login: Create access token
        token_data = {
            "sub": counselor.email,
            "tenant_id": counselor.tenant_id,
            "role": counselor.role.value,
        }
        access_token = create_access_token(token_data)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        )

    except (ConflictError, BadRequestError):
        raise
    except Exception as e:
        db.rollback()
        raise InternalServerError(
            detail=f"Failed to register: {str(e)}",
            instance=str(request.url.path),
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(f"{settings.RATE_LIMIT_LOGIN_PER_MINUTE}/minute")
def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Login endpoint - authenticate counselor and return JWT token

    Args:
        credentials: Email, password, and tenant_id
        db: Database session

    Returns:
        TokenResponse with access_token

    Raises:
        HTTPException: 401 if credentials are invalid, 403 if account inactive
    """
    # Query counselor by email AND tenant_id
    result = db.execute(
        select(Counselor).where(
            Counselor.email == credentials.email,
            Counselor.tenant_id == credentials.tenant_id,
        )
    )
    counselor = result.scalar_one_or_none()

    # Check if counselor exists and password is correct
    if counselor is None or not verify_password(
        credentials.password, counselor.hashed_password
    ):
        raise UnauthorizedError(
            detail="Incorrect email, password, or tenant ID",
            instance=str(request.url.path),
        )

    # Check if account is active (email verified)
    if not counselor.is_active:
        raise ForbiddenError(
            detail="Email not verified. Please check your email for verification link.",
            instance=str(request.url.path),
        )

    try:
        # Update last_login
        counselor.last_login = datetime.now(timezone.utc)
        db.commit()

        # Create access token
        token_data = {
            "sub": counselor.email,
            "tenant_id": counselor.tenant_id,
            "role": counselor.role.value,
        }
        access_token = create_access_token(token_data)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        )

    except Exception:
        # Rollback on any database error
        db.rollback()
        raise InternalServerError(
            detail="Failed to complete login",
            instance=str(request.url.path),
        )


@router.get("/me", response_model=CounselorInfo)
def get_current_counselor(
    current_user: Counselor = Depends(get_current_user),
) -> CounselorInfo:
    """
    Get current authenticated counselor information

    Args:
        current_user: Current authenticated counselor from JWT

    Returns:
        CounselorInfo with user details
    """
    return CounselorInfo.model_validate(current_user)


@router.patch("/me", response_model=CounselorInfo)
def update_current_counselor(
    update_data: CounselorUpdate,
    request: Request,
    current_user: Counselor = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CounselorInfo:
    """
    Update current authenticated counselor information

    Args:
        update_data: Fields to update (full_name, username)
        current_user: Current authenticated counselor from JWT
        db: Database session

    Returns:
        Updated CounselorInfo

    Raises:
        HTTPException: 400 if username already exists, 500 if update fails
    """
    try:
        # Convert to dict and process values
        # Convert empty strings to None for nullable fields (username, full_name)
        # Allow None values to clear fields
        update_fields = {}
        for k, v in update_data.model_dump(exclude_unset=True).items():
            # Convert empty string to None for nullable fields
            if k in ("username", "full_name") and v == "":
                update_fields[k] = None
            else:
                # Allow None values (to clear fields) or actual values
                update_fields[k] = v

        if not update_fields:
            raise BadRequestError(
                detail="No valid fields to update",
                instance=str(request.url.path),
            )

        # Check username uniqueness if being updated (only if different from current and not None)
        if (
            "username" in update_fields
            and update_fields["username"] is not None
            and update_fields["username"] != current_user.username
        ):
            result = db.execute(
                select(Counselor).where(
                    Counselor.username == update_fields["username"],
                    Counselor.id != current_user.id,
                )
            )
            if result.scalar_one_or_none():
                raise ConflictError(
                    detail=f"Username '{update_fields['username']}' already exists",
                    instance=str(request.url.path),
                )

        # Update fields
        for field, value in update_fields.items():
            setattr(current_user, field, value)

        db.commit()
        db.refresh(current_user)

        return CounselorInfo.model_validate(current_user)

    except (BadRequestError, ConflictError):
        raise
    except Exception as e:
        db.rollback()
        raise InternalServerError(
            detail=f"Failed to update counselor info: {str(e)}",
            instance=str(request.url.path),
        )


@router.post("/verify-email", response_model=VerifyEmailResponse)
def verify_email(
    data: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> VerifyEmailResponse:
    """
    Verify email address using token from verification email

    Args:
        data: Verification token
        db: Database session

    Returns:
        VerifyEmailResponse with success message

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    try:
        payload = verify_verification_token(data.token)
        email = payload["email"]
        tenant_id = payload["tenant_id"]

        counselor = db.execute(
            select(Counselor).where(
                Counselor.email == email, Counselor.tenant_id == tenant_id
            )
        ).scalar_one_or_none()

        if not counselor:
            raise UnauthorizedError("Invalid verification token")

        if counselor.is_active:
            return VerifyEmailResponse(
                message="Email already verified", email=email
            )

        counselor.is_active = True
        db.commit()

        return VerifyEmailResponse(message="Email verified successfully", email=email)
    except JWTError:
        raise UnauthorizedError("Invalid or expired verification token")


@router.post("/resend-verification", response_model=ResendVerificationResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PASSWORD_RESET_PER_HOUR}/hour")
async def resend_verification(
    data: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> ResendVerificationResponse:
    """
    Resend email verification link

    Args:
        data: Email and tenant_id
        request: FastAPI request
        db: Database session

    Returns:
        ResendVerificationResponse with success message

    Raises:
        HTTPException: 400 if email already verified
    """
    counselor = db.execute(
        select(Counselor).where(
            Counselor.email == data.email, Counselor.tenant_id == data.tenant_id
        )
    ).scalar_one_or_none()

    # Don't reveal if email exists (security)
    if not counselor:
        return ResendVerificationResponse(
            message="If the email exists, a verification email has been sent"
        )

    if counselor.is_active:
        raise BadRequestError("Email already verified")

    verification_token = create_verification_token(counselor.email, counselor.tenant_id)
    email_service = EmailSenderService()
    await email_service.send_verification_email(
        to_email=counselor.email,
        verification_token=verification_token,
        tenant_id=counselor.tenant_id,
    )

    return ResendVerificationResponse(message="Verification email sent")
