"""
Case CRUD API endpoints
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.schemas.case import CaseCreate, CaseResponse, CaseUpdate

router = APIRouter(prefix="/api/v1/cases", tags=["Cases"])


@router.get("", response_model=dict)
def list_cases(
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> dict:
    """
    List cases with optional filtering

    Args:
        client_id: Optional client ID to filter cases
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated counselor
        tenant_id: Tenant ID from JWT
        db: Database session

    Returns:
        Dictionary with items and total count
    """
    query = select(Case).where(
        Case.tenant_id == tenant_id,
        Case.deleted_at.is_(None),
    )

    if client_id:
        query = query.where(Case.client_id == client_id)

    query = query.order_by(Case.created_at.desc())

    # Get total count using SQL COUNT
    count_query = select(func.count()).select_from(Case).where(Case.tenant_id == tenant_id)
    if client_id:
        count_query = count_query.where(Case.client_id == client_id)
    total_count = db.execute(count_query).scalar()

    # Get paginated results
    result = db.execute(query.offset(skip).limit(limit))
    cases = result.scalars().all()

    return {
        "items": [CaseResponse.model_validate(case) for case in cases],
        "total": total_count,
        "skip": skip,
        "limit": limit,
    }


def _generate_case_number(db: Session, tenant_id: str) -> str:
    """
    Generate unique case number in format CASE0001, CASE0002, etc.

    Args:
        db: Database session
        tenant_id: Tenant ID

    Returns:
        Generated case number
    """
    # Find the highest existing case number for this tenant (exclude deleted)
    result = db.execute(
        select(Case.case_number)
        .where(Case.tenant_id == tenant_id)
        .where(Case.case_number.like("CASE%"))
        .where(Case.deleted_at.is_(None))
        .order_by(Case.case_number.desc())
    )
    numbers = result.scalars().all()

    # Extract numbers and find max
    max_num = 0
    for num_str in numbers:
        if num_str.startswith("CASE") and num_str[4:].isdigit():
            num = int(num_str[4:])
            if num > max_num:
                max_num = num

    # Generate next number
    next_num = max_num + 1
    return f"CASE{next_num:04d}"


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    case_data: CaseCreate,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> CaseResponse:
    """
    Create a new case

    Args:
        case_data: Case information
        current_user: Current authenticated counselor
        tenant_id: Tenant ID from JWT
        db: Database session

    Returns:
        Created case information

    Raises:
        HTTPException: 400 if case number already exists
        HTTPException: 404 if client not found
        HTTPException: 500 if database error occurs
    """
    try:
        # Auto-generate case_number if not provided
        case_number = case_data.case_number
        if not case_number:
            case_number = _generate_case_number(db, tenant_id)

        # Check if case number already exists (exclude deleted)
        result = db.execute(
            select(Case).where(
                Case.case_number == case_number,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Case number '{case_number}' already exists",
            )

        # Verify client exists and belongs to same tenant
        client_result = db.execute(
            select(Client).where(
                Client.id == case_data.client_id,
                Client.tenant_id == tenant_id,
            )
        )
        client = client_result.scalar_one_or_none()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {case_data.client_id} not found or doesn't belong to this tenant",
            )

        # Create case
        new_case = Case(
            case_number=case_number,
            counselor_id=current_user.id,
            client_id=case_data.client_id,
            tenant_id=tenant_id,
            status=case_data.status,
            summary=case_data.summary,
            goals=case_data.goals,
            problem_description=case_data.problem_description,
        )

        db.add(new_case)
        db.commit()
        db.refresh(new_case)

        return CaseResponse.model_validate(new_case)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create case: {str(e)}",
        )


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> CaseResponse:
    """
    Get case by ID

    Args:
        case_id: Case ID
        current_user: Current authenticated counselor
        tenant_id: Tenant ID from JWT
        db: Database session

    Returns:
        Case information

    Raises:
        HTTPException: 404 if case not found
    """
    result = db.execute(
        select(Case).where(
            Case.id == case_id,
            Case.tenant_id == tenant_id,
            Case.deleted_at.is_(None),
        )
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    return CaseResponse.model_validate(case)


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: UUID,
    case_data: CaseUpdate,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> CaseResponse:
    """
    Update case

    Args:
        case_id: Case ID
        case_data: Fields to update
        current_user: Current authenticated counselor
        tenant_id: Tenant ID from JWT
        db: Database session

    Returns:
        Updated case information

    Raises:
        HTTPException: 404 if case not found
        HTTPException: 500 if update fails
    """
    try:
        result = db.execute(
            select(Case).where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        )
        case = result.scalar_one_or_none()

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found",
            )

        # Update fields
        update_data = case_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(case, field, value)

        db.commit()
        db.refresh(case)

        return CaseResponse.model_validate(case)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update case: {str(e)}",
        )


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    case_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    """
    Soft delete case (sets deleted_at timestamp)

    Args:
        case_id: Case ID
        current_user: Current authenticated counselor
        tenant_id: Tenant ID from JWT
        db: Database session

    Raises:
        HTTPException: 404 if case not found
        HTTPException: 500 if delete fails
    """
    from datetime import datetime, timezone

    try:
        result = db.execute(
            select(Case).where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        )
        case = result.scalar_one_or_none()

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found",
            )

        # Soft delete
        case.deleted_at = datetime.now(timezone.utc)
        db.commit()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete case: {str(e)}",
        )
