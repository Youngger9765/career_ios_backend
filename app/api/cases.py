"""Case CRUD API endpoints"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.counselor import Counselor
from app.schemas.case import CaseCreate, CaseResponse, CaseUpdate
from app.services.clients.case_service import CaseService

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
    """List cases with optional filtering"""
    service = CaseService(db)
    cases, total = service.list_cases(
        tenant_id=tenant_id,
        counselor_id=current_user.id,
        skip=skip,
        limit=limit,
        client_id=client_id,
    )

    return {
        "items": [CaseResponse.model_validate(case) for case in cases],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    case_data: CaseCreate,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> CaseResponse:
    """Create a new case"""
    try:
        service = CaseService(db)
        case_dict = case_data.model_dump()

        new_case = service.create_case(
            case_data=case_dict,
            counselor=current_user,
            tenant_id=tenant_id,
        )

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
    """Get a specific case by ID"""
    service = CaseService(db)
    case = service.get_case_by_id(
        case_id=case_id, tenant_id=tenant_id, counselor_id=current_user.id
    )

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
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
    """Update a case"""
    try:
        service = CaseService(db)
        update_data = case_data.model_dump(exclude_unset=True)

        updated_case = service.update_case(
            case_id=case_id,
            update_data=update_data,
            tenant_id=tenant_id,
            counselor_id=current_user.id,
        )

        return CaseResponse.model_validate(updated_case)

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
    """Soft delete a case (sets deleted_at timestamp)"""
    service = CaseService(db)
    service.delete_case(
        case_id=case_id,
        counselor=current_user,
        tenant_id=tenant_id,
    )
