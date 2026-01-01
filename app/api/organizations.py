"""
Organizations API endpoints
Multi-tenant organization management
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
)
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.organization import Organization
from app.models.session import Session as SessionModel
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationStats,
    OrganizationUpdate,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("", response_model=OrganizationListResponse)
def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or tenant_id"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: Counselor = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationListResponse:
    """
    List organizations (multi-tenant aware)

    - Regular counselors: See only their own organization
    - Admins: Could see all organizations (if implemented)

    Returns:
        OrganizationListResponse with paginated results
    """
    # Build base query - filter by current user's tenant
    query = select(Organization).where(Organization.tenant_id == current_user.tenant_id)

    # Apply filters
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Organization.name.ilike(search_pattern))
            | (Organization.tenant_id.ilike(search_pattern))
        )

    if is_active is not None:
        query = query.where(Organization.is_active == is_active)

    # Get total count
    total = db.scalar(select(func.count()).select_from(query.subquery()))

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    organizations = db.scalars(query).all()

    return OrganizationListResponse(
        organizations=[
            OrganizationResponse.model_validate(org) for org in organizations
        ],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
) -> OrganizationResponse:
    """
    Get organization details by ID

    Args:
        org_id: Organization UUID
        current_user: Current authenticated user
        db: Database session

    Returns:
        OrganizationResponse with full details

    Raises:
        NotFoundError: If organization not found or not accessible
    """
    # Query organization
    result = db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.tenant_id == current_user.tenant_id,
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise NotFoundError(
            detail=f"Organization with ID {org_id} not found",
            instance=str(request.url.path) if request else None,
        )

    # Update stats before returning
    organization.update_stats(db)
    db.commit()
    db.refresh(organization)

    return OrganizationResponse.model_validate(organization)


@router.get("/{org_id}/stats", response_model=OrganizationStats)
def get_organization_stats(
    org_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
) -> OrganizationStats:
    """
    Get detailed statistics for an organization

    Returns:
        OrganizationStats with computed metrics
    """
    # Query organization
    result = db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.tenant_id == current_user.tenant_id,
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise NotFoundError(
            detail=f"Organization with ID {org_id} not found",
            instance=str(request.url.path) if request else None,
        )

    # Compute real-time stats
    tenant_id = organization.tenant_id

    # Count active counselors
    counselor_count = (
        db.scalar(
            select(func.count(Counselor.id)).where(
                Counselor.tenant_id == tenant_id, Counselor.is_active.is_(True)
            )
        )
        or 0
    )

    # Count clients
    client_count = (
        db.scalar(select(func.count(Client.id)).where(Client.tenant_id == tenant_id))
        or 0
    )

    # Count sessions
    session_count = (
        db.scalar(
            select(func.count(SessionModel.id)).where(
                SessionModel.tenant_id == tenant_id
            )
        )
        or 0
    )

    # Count "active" sessions - sessions with start_time but no end_time
    active_sessions_count = (
        db.scalar(
            select(func.count(SessionModel.id)).where(
                SessionModel.tenant_id == tenant_id,
                SessionModel.start_time.isnot(None),
                SessionModel.end_time.is_(None),
            )
        )
        or 0
    )

    return OrganizationStats(
        tenant_id=organization.tenant_id,
        name=organization.name,
        counselor_count=counselor_count,
        client_count=client_count,
        session_count=session_count,
        active_sessions_count=active_sessions_count,
        total_session_duration=0.0,  # TODO: Compute if duration field exists
    )


@router.post(
    "", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED
)
def create_organization(
    org_data: OrganizationCreate,
    current_user: Counselor = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
) -> OrganizationResponse:
    """
    Create a new organization

    Args:
        org_data: Organization creation data
        current_user: Current authenticated user (must be admin)
        db: Database session

    Returns:
        OrganizationResponse with created organization

    Raises:
        ConflictError: If tenant_id already exists
    """
    # Check if tenant_id already exists
    result = db.execute(
        select(Organization).where(Organization.tenant_id == org_data.tenant_id)
    )
    if result.scalar_one_or_none():
        raise ConflictError(
            detail=f"Organization with tenant_id '{org_data.tenant_id}' already exists",
            instance=str(request.url.path) if request else None,
        )

    try:
        # Create organization
        organization = Organization(
            tenant_id=org_data.tenant_id,
            name=org_data.name,
            description=org_data.description,
            is_active=True,
            counselor_count=0,
            client_count=0,
            session_count=0,
        )

        db.add(organization)
        db.commit()
        db.refresh(organization)

        return OrganizationResponse.model_validate(organization)

    except (ConflictError, BadRequestError):
        raise
    except Exception as e:
        db.rollback()
        raise InternalServerError(
            detail=f"Failed to create organization: {str(e)}",
            instance=str(request.url.path) if request else None,
        )


@router.patch("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: UUID,
    update_data: OrganizationUpdate,
    current_user: Counselor = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
) -> OrganizationResponse:
    """
    Update organization details

    Args:
        org_id: Organization UUID
        update_data: Fields to update
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated OrganizationResponse

    Raises:
        NotFoundError: If organization not found
        BadRequestError: If no valid fields to update
    """
    # Query organization (must belong to current user's tenant)
    result = db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.tenant_id == current_user.tenant_id,
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise NotFoundError(
            detail=f"Organization with ID {org_id} not found",
            instance=str(request.url.path) if request else None,
        )

    try:
        # Get update fields (exclude None)
        update_fields = {
            k: v
            for k, v in update_data.model_dump(exclude_unset=True).items()
            if v is not None
        }

        if not update_fields:
            raise BadRequestError(
                detail="No valid fields to update",
                instance=str(request.url.path) if request else None,
            )

        # Apply updates
        for field, value in update_fields.items():
            setattr(organization, field, value)

        db.commit()
        db.refresh(organization)

        return OrganizationResponse.model_validate(organization)

    except (BadRequestError, NotFoundError):
        raise
    except Exception as e:
        db.rollback()
        raise InternalServerError(
            detail=f"Failed to update organization: {str(e)}",
            instance=str(request.url.path) if request else None,
        )


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
) -> None:
    """
    Soft delete an organization

    Sets is_active = False instead of deleting

    Args:
        org_id: Organization UUID
        current_user: Current authenticated user
        db: Database session

    Raises:
        NotFoundError: If organization not found
    """
    # Query organization
    result = db.execute(
        select(Organization).where(
            Organization.id == org_id,
            Organization.tenant_id == current_user.tenant_id,
        )
    )
    organization = result.scalar_one_or_none()

    if not organization:
        raise NotFoundError(
            detail=f"Organization with ID {org_id} not found",
            instance=str(request.url.path) if request else None,
        )

    try:
        # Soft delete - set is_active to False
        organization.is_active = False
        db.commit()

    except Exception as e:
        db.rollback()
        raise InternalServerError(
            detail=f"Failed to delete organization: {str(e)}",
            instance=str(request.url.path) if request else None,
        )
