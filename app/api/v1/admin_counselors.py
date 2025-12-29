"""
Admin Counselor Management API Endpoints
"""
import logging
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db
from app.core.security import hash_password
from app.models.counselor import Counselor, CounselorRole
from app.models.password_reset import PasswordResetToken
from app.schemas.admin_counselor import (
    CounselorCreateRequest,
    CounselorCreateResponse,
    CounselorDeleteResponse,
    CounselorDetailResponse,
    CounselorListResponse,
    CounselorUpdateRequest,
)
from app.services.email_sender import email_sender

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/counselors", tags=["admin-counselors"])

# Optional security for debug mode
optional_security = HTTPBearer(auto_error=False)


def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    tenant_id: Optional[str] = Query(None, description="Tenant ID (DEBUG mode only)"),
    db: Session = Depends(get_db),
) -> Optional[Counselor]:
    """
    Verify current user is admin.

    In DEBUG mode without credentials, returns a mock admin.
    The tenant_id can be specified via query parameter for testing multi-tenant scenarios.
    In production or with credentials, requires valid admin authentication.

    NOTE: The tenant_id query parameter is ONLY used in DEBUG mode without credentials.
    In production mode or with authentication, the tenant_id from the JWT token is used.
    """
    # DEBUG MODE: Allow access without credentials
    if settings.DEBUG and credentials is None:
        # Use tenant_id from query parameter or default to 'career'
        # This allows frontend tenant switcher to work in debug mode
        mock_tenant_id = tenant_id or "career"

        # Return a mock admin counselor for the specified tenant
        # This is ONLY for local development/testing
        # Using a simple object instead of Counselor model to avoid DB dependencies
        from types import SimpleNamespace

        return SimpleNamespace(
            id="00000000-0000-0000-0000-000000000000",
            email=f"debug@admin.{mock_tenant_id}",
            username="debug_admin",
            full_name=f"Debug Admin ({mock_tenant_id})",
            tenant_id=mock_tenant_id,  # Dynamic tenant_id from query parameter
            role=CounselorRole.ADMIN,
            is_active=True,
            hashed_password="",
            available_credits=1000.0,
        )

    # PRODUCTION MODE or with credentials: Require authentication
    # NOTE: tenant_id query parameter is IGNORED in production mode
    # The tenant_id from the JWT token is always used for authenticated requests
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Authenticate user
    from app.core.security import decode_token

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: Optional[str] = payload.get("sub")
    token_tenant_id: Optional[str] = payload.get("tenant_id")

    if email is None or token_tenant_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    current_user = db.execute(
        select(Counselor).where(
            Counselor.email == email, Counselor.tenant_id == token_tenant_id
        )
    ).scalar_one_or_none()

    if current_user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user account")

    if current_user.role != CounselorRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    return current_user


def resolve_tenant_id(
    current_admin: Counselor,
    requested_tenant_id: Optional[str],
) -> str:
    """Resolve and validate tenant_id for admin access."""
    if requested_tenant_id is None:
        return current_admin.tenant_id

    # In DEBUG mode, allow cross-tenant access for testing
    if settings.DEBUG:
        return requested_tenant_id

    # In production, enforce strict tenant isolation
    if requested_tenant_id != current_admin.tenant_id:
        raise HTTPException(
            status_code=403,
            detail=f"Admin not allowed to access tenant '{requested_tenant_id}'",
        )
    return requested_tenant_id


def generate_temporary_password(length: int = 12) -> str:
    """Generate a secure temporary password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_secure_token() -> str:
    """Generate a cryptographically secure random token for password reset"""
    return secrets.token_urlsafe(32)


async def send_password_reset_email_for_new_counselor(
    counselor: Counselor,
    db: Session,
) -> None:
    """
    Generate password reset token and send email for newly created counselor.

    This allows the new counselor to set their own password via email link.
    Errors are logged but don't block counselor creation.

    Args:
        counselor: The newly created counselor object
        db: Database session
    """
    try:
        # Generate secure token
        token = generate_secure_token()

        # Create password reset token in database
        reset_token = PasswordResetToken(
            token=token,
            email=counselor.email,
            tenant_id=counselor.tenant_id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=6),
            used=False,
            request_ip=None,  # Admin-initiated, no client IP
        )

        db.add(reset_token)
        db.commit()

        # Send password reset email
        await email_sender.send_password_reset_email(
            to_email=counselor.email,
            reset_token=token,
            counselor_name=counselor.full_name,
            tenant_id=counselor.tenant_id,
        )

        logger.info(
            f"Password reset email sent to new counselor: {counselor.email} "
            f"(tenant: {counselor.tenant_id})"
        )

    except Exception as e:
        # Log error but don't fail the counselor creation
        logger.error(
            f"Failed to send password reset email for {counselor.email}: {e}",
            exc_info=True,
        )


@router.get("", response_model=CounselorListResponse)
async def list_counselors(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(
        None, description="Search by email, username, or full_name"
    ),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_admin: Optional[Counselor] = Depends(require_admin),
):
    """
    List all counselors with filtering, pagination, and sorting.
    Admin only. Filtered by tenant if authorized.
    """
    target_tenant_id = resolve_tenant_id(current_admin, tenant_id)

    # Build query with automatic tenant isolation
    query = select(Counselor).where(
        Counselor.deleted_at.is_(None), Counselor.tenant_id == target_tenant_id
    )

    # Apply filters
    if role:
        query = query.where(Counselor.role == role)
    if is_active is not None:
        query = query.where(Counselor.is_active == is_active)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Counselor.email.ilike(search_pattern),
                Counselor.username.ilike(search_pattern),
                Counselor.full_name.ilike(search_pattern),
            )
        )

    # Count total (using count function instead of len)
    from sqlalchemy import func

    count_query = (
        select(func.count())
        .select_from(Counselor)
        .where(Counselor.deleted_at.is_(None), Counselor.tenant_id == target_tenant_id)
    )
    if role:
        count_query = count_query.where(Counselor.role == role)
    if is_active is not None:
        count_query = count_query.where(Counselor.is_active == is_active)
    if search:
        search_pattern = f"%{search}%"
        count_query = count_query.where(
            or_(
                Counselor.email.ilike(search_pattern),
                Counselor.username.ilike(search_pattern),
                Counselor.full_name.ilike(search_pattern),
            )
        )
    total = db.execute(count_query).scalar()

    # Apply sorting
    sort_column = getattr(Counselor, sort_by, Counselor.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    counselors = db.execute(query).scalars().all()

    return CounselorListResponse(total=total, counselors=counselors)


@router.get("/{counselor_id}", response_model=CounselorDetailResponse)
async def get_counselor(
    counselor_id: UUID,
    db: Session = Depends(get_db),
    current_admin: Optional[Counselor] = Depends(require_admin),
):
    """
    Get single counselor details.
    Admin only. Automatically filtered by admin's tenant.
    """
    counselor = db.execute(
        select(Counselor).where(
            Counselor.id == counselor_id,
            Counselor.deleted_at.is_(None),
            Counselor.tenant_id == current_admin.tenant_id,
        )
    ).scalar_one_or_none()

    if not counselor:
        raise HTTPException(status_code=404, detail="Counselor not found")

    return counselor


@router.patch("/{counselor_id}", response_model=CounselorDetailResponse)
async def update_counselor(
    counselor_id: UUID,
    request: CounselorUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: Optional[Counselor] = Depends(require_admin),
):
    """
    Update counselor information.
    Admin only. Automatically filtered by admin's tenant.

    Note: Cannot update email, username, tenant_id (immutable fields).
    Cannot directly update credits (use /admin/credits/members/{id}/add instead).
    """
    counselor = db.execute(
        select(Counselor).where(
            Counselor.id == counselor_id,
            Counselor.deleted_at.is_(None),
            Counselor.tenant_id == current_admin.tenant_id,
        )
    ).scalar_one_or_none()

    if not counselor:
        raise HTTPException(status_code=404, detail="Counselor not found")

    # Update allowed fields only
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "role":
            # Convert string to CounselorRole enum
            setattr(counselor, field, CounselorRole(value))
        else:
            setattr(counselor, field, value)

    counselor.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(counselor)

    return counselor


@router.patch("/{counselor_id}/password")
async def change_counselor_password(
    counselor_id: UUID,
    request: dict,
    db: Session = Depends(get_db),
    current_admin: Optional[Counselor] = Depends(require_admin),
):
    """
    Change counselor password.
    Admin only. Automatically filtered by admin's tenant.
    """
    counselor = db.execute(
        select(Counselor).where(
            Counselor.id == counselor_id,
            Counselor.deleted_at.is_(None),
            Counselor.tenant_id == current_admin.tenant_id,
        )
    ).scalar_one_or_none()

    if not counselor:
        raise HTTPException(status_code=404, detail="Counselor not found")

    password = request.get("password")
    if not password or len(password) < 6:
        raise HTTPException(
            status_code=400, detail="Password must be at least 6 characters"
        )

    # Update password
    counselor.hashed_password = hash_password(password)
    counselor.updated_at = datetime.now(timezone.utc)
    db.commit()

    return {"success": True, "message": "Password changed successfully"}


@router.delete("/{counselor_id}", response_model=CounselorDeleteResponse)
async def delete_counselor(
    counselor_id: UUID,
    db: Session = Depends(get_db),
    current_admin: Optional[Counselor] = Depends(require_admin),
):
    """
    Delete counselor (soft delete).
    Admin only. Automatically filtered by admin's tenant.

    Behavior:
    - Soft delete (sets deleted_at timestamp)
    - Counselor cannot login after deletion
    - Related data (Sessions, Cases, Clients) preserved for audit trail
    """
    counselor = db.execute(
        select(Counselor).where(
            Counselor.id == counselor_id,
            Counselor.deleted_at.is_(None),
            Counselor.tenant_id == current_admin.tenant_id,
        )
    ).scalar_one_or_none()

    if not counselor:
        raise HTTPException(status_code=404, detail="Counselor not found")

    # Soft delete
    counselor.deleted_at = datetime.now(timezone.utc)
    counselor.is_active = False  # Also deactivate
    db.commit()

    return CounselorDeleteResponse(
        success=True,
        message="Counselor deleted successfully",
        counselor_id=counselor_id,
    )


@router.post("", response_model=CounselorCreateResponse)
async def create_counselor(
    request: CounselorCreateRequest,
    db: Session = Depends(get_db),
    current_admin: Optional[Counselor] = Depends(require_admin),
):
    """
    Create new counselor account.
    Admin only. Uses requested tenant_id if authorized.

    Auto-generates a temporary password for the new account.
    The counselor should change their password on first login.
    """
    target_tenant_id = resolve_tenant_id(current_admin, request.tenant_id)

    # Username uniqueness check removed per user request (allow duplicate usernames)

    # Check if email exists in the same tenant
    existing_email = db.execute(
        select(Counselor).where(
            Counselor.email == request.email, Counselor.tenant_id == target_tenant_id
        )
    ).scalar_one_or_none()

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail=f"Email '{request.email}' already exists in your tenant",
        )

    # Use password set by admin (no longer auto-generating)
    # Create new counselor with admin's tenant_id
    counselor = Counselor(
        email=request.email,
        username=request.username,
        full_name=request.full_name,
        phone=request.phone,
        hashed_password=hash_password(request.password),
        tenant_id=target_tenant_id,  # Use admin's tenant_id
        role=CounselorRole(request.role),
        is_active=True,
        available_credits=float(request.total_credits),  # Set initial available credits
        subscription_expires_at=request.subscription_expires_at,
    )

    db.add(counselor)
    db.commit()
    db.refresh(counselor)

    # Create initial credit log entry if total_credits > 0
    if request.total_credits > 0:
        from app.models.credit_log import CreditLog

        credit_log = CreditLog(
            counselor_id=counselor.id,
            credits_delta=float(request.total_credits),
            transaction_type="purchase",
            raw_data={
                "source": "admin_created",
                "initial_credits": request.total_credits,
            },
        )
        db.add(credit_log)
        db.commit()

    # Send password reset email to new counselor
    # This allows them to set their own password via email link
    await send_password_reset_email_for_new_counselor(counselor, db)

    return CounselorCreateResponse(
        counselor=CounselorDetailResponse.model_validate(counselor),
        temporary_password=None,  # No longer returning temporary password
    )
