"""Client CRUD API endpoints"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.counselor import Counselor
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)
from app.services.client_service import ClientService

router = APIRouter(prefix="/api/v1/clients", tags=["Clients"])


# Timeline Response Schemas
class TimelineSessionItem(BaseModel):
    """單次會談的時間線資訊"""

    session_id: UUID
    session_number: int
    date: str  # YYYY-MM-DD
    time_range: Optional[str] = None  # "HH:MM-HH:MM" or None
    summary: Optional[str] = None  # 會談摘要
    has_report: bool  # 是否有報告
    report_id: Optional[UUID] = None  # 報告 ID


class ClientTimelineResponse(BaseModel):
    """個案歷程時間線響應"""

    client_id: UUID
    client_name: str
    client_code: str
    total_sessions: int
    sessions: List[TimelineSessionItem]


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_data: ClientCreate,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ClientResponse:
    """Create a new client"""
    try:
        service = ClientService(db)
        client_dict = client_data.model_dump()

        client = service.create_client(
            client_data=client_dict,
            counselor=current_user,
            tenant_id=tenant_id,
        )

        return ClientResponse.model_validate(client)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create client: {str(e)}",
        )


@router.get("", response_model=ClientListResponse)
def list_clients(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of records to return"),
    search: Optional[str] = Query(
        None, description="Search by name, nickname, or code"
    ),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ClientListResponse:
    """List all clients for current counselor"""
    service = ClientService(db)
    clients, total = service.list_clients(
        counselor=current_user,
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        search=search,
    )

    return ClientListResponse(
        total=total,
        items=[ClientResponse.model_validate(c) for c in clients],
    )


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ClientResponse:
    """Get a specific client by ID"""
    service = ClientService(db)
    client = service.get_client_by_id(
        client_id=client_id,
        counselor=current_user,
        tenant_id=tenant_id,
    )

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    return ClientResponse.model_validate(client)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: UUID,
    client_data: ClientUpdate,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ClientResponse:
    """Update a client"""
    try:
        service = ClientService(db)
        update_data = client_data.model_dump(exclude_unset=True)

        client = service.update_client(
            client_id=client_id,
            update_data=update_data,
            counselor=current_user,
            tenant_id=tenant_id,
        )

        return ClientResponse.model_validate(client)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update client: {str(e)}",
        )


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    """Soft delete a client (sets deleted_at timestamp)"""
    service = ClientService(db)
    service.delete_client(
        client_id=client_id,
        counselor=current_user,
        tenant_id=tenant_id,
    )


@router.get("/{client_id}/timeline", response_model=ClientTimelineResponse)
def get_client_timeline(
    client_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ClientTimelineResponse:
    """取得個案的會談歷程時間線"""
    service = ClientService(db)
    client, timeline_items = service.get_client_timeline(
        client_id=client_id,
        counselor=current_user,
        tenant_id=tenant_id,
    )

    return ClientTimelineResponse(
        client_id=client.id,
        client_name=client.name,
        client_code=client.code,
        total_sessions=len(timeline_items),
        sessions=[TimelineSessionItem(**item) for item in timeline_items],
    )
