"""
Authentication API endpoints
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.models.counselor import Counselor
from app.schemas.auth import CounselorInfo, CounselorUpdate, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = Settings()


@router.post("/login", response_model=TokenResponse)
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Login endpoint - authenticate counselor and return JWT token

    Args:
        credentials: Email and password
        db: Database session

    Returns:
        TokenResponse with access_token

    Raises:
        HTTPException: 401 if credentials are invalid, 403 if account inactive
    """
    # Query counselor by email
    result = db.execute(
        select(Counselor).where(Counselor.email == credentials.email)
    )
    counselor = result.scalar_one_or_none()

    # Check if counselor exists and password is correct
    if counselor is None or not verify_password(
        credentials.password, counselor.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is active
    if not counselor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete login",
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
        # Convert to dict and filter out None values
        update_fields = {k: v for k, v in update_data.model_dump(exclude_unset=True).items() if v is not None}

        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update",
            )

        # Check username uniqueness if being updated (only if different from current)
        if "username" in update_fields and update_fields["username"] != current_user.username:
            result = db.execute(
                select(Counselor).where(
                    Counselor.username == update_fields["username"],
                    Counselor.id != current_user.id,
                )
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Username '{update_fields['username']}' already exists",
                )

        # Update fields
        for field, value in update_fields.items():
            setattr(current_user, field, value)

        db.commit()
        db.refresh(current_user)

        return CounselorInfo.model_validate(current_user)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update counselor info: {str(e)}",
        )
