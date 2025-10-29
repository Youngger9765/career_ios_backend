"""
Client CRUD API endpoints
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.client import Client
from app.models.counselor import Counselor
from app.schemas.client import (
    ClientCreate,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)

router = APIRouter(prefix="/api/v1/clients", tags=["Clients"])


def _generate_client_code(db: Session, tenant_id: str) -> str:
    """
    Generate unique client code in format C0001, C0002, etc.

    Args:
        db: Database session
        tenant_id: Tenant ID

    Returns:
        Generated client code
    """
    # Find the highest existing code number for this tenant
    result = db.execute(
        select(Client.code)
        .where(Client.tenant_id == tenant_id)
        .where(Client.code.like("C%"))
        .order_by(Client.code.desc())
    )
    codes = result.scalars().all()

    # Extract numbers from codes and find max
    max_num = 0
    for code in codes:
        if code.startswith("C") and code[1:].isdigit():
            num = int(code[1:])
            if num > max_num:
                max_num = num

    # Generate next code
    next_num = max_num + 1
    return f"C{next_num:04d}"


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_data: ClientCreate,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ClientResponse:
    """
    Create a new client

    Args:
        client_data: Client information
        current_user: Current authenticated counselor
        tenant_id: Tenant ID from environment
        db: Database session

    Returns:
        Created client information

    Raises:
        HTTPException: 400 if client code already exists
        HTTPException: 500 if database error occurs
    """
    try:
        # Auto-generate code if not provided
        client_code = client_data.code
        if not client_code:
            client_code = _generate_client_code(db, tenant_id)

        # Check if code already exists
        result = db.execute(
            select(Client).where(
                Client.code == client_code, Client.tenant_id == tenant_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Client code '{client_code}' already exists",
            )

        # Create new client
        client_dict = client_data.model_dump(exclude={"code"})
        client = Client(
            **client_dict,
            code=client_code,
            counselor_id=current_user.id,
            tenant_id=tenant_id,
        )
        db.add(client)
        db.commit()
        db.refresh(client)

        return ClientResponse.model_validate(client)

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        # Rollback on any database error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create client: {str(e)}",
        )


@router.get("", response_model=ClientListResponse)
def list_clients(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Max number of records to return"),
    search: Optional[str] = Query(None, description="Search by name, nickname, or code"),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ClientListResponse:
    """
    List all clients for current counselor

    Args:
        skip: Pagination offset
        limit: Number of items per page
        search: Optional search query
        current_user: Current authenticated counselor
        tenant_id: Tenant ID
        db: Database session

    Returns:
        Paginated list of clients
    """
    # Base query - only current counselor's clients
    query = select(Client).where(
        Client.counselor_id == current_user.id,
        Client.tenant_id == tenant_id,
    )

    # Add search filter
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Client.name.ilike(search_pattern),
                Client.nickname.ilike(search_pattern),
                Client.code.ilike(search_pattern),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(Client.created_at.desc())
    result = db.execute(query)
    clients = result.scalars().all()

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
    """
    Get a specific client by ID

    Args:
        client_id: Client UUID
        current_user: Current authenticated counselor
        tenant_id: Tenant ID
        db: Database session

    Returns:
        Client information

    Raises:
        HTTPException: 404 if client not found or not owned by counselor
    """
    result = db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
        )
    )
    client = result.scalar_one_or_none()

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
    """
    Update a client

    Args:
        client_id: Client UUID
        client_data: Updated client information
        current_user: Current authenticated counselor
        tenant_id: Tenant ID
        db: Database session

    Returns:
        Updated client information

    Raises:
        HTTPException: 404 if client not found or not owned by counselor
        HTTPException: 400 if trying to update code to existing code
    """
    result = db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    try:
        # Update fields
        update_data = client_data.model_dump(exclude_unset=True)

        # Check if code is being updated and if it conflicts with existing client
        if "code" in update_data and update_data["code"] != client.code:
            existing = db.execute(
                select(Client).where(
                    Client.code == update_data["code"],
                    Client.tenant_id == tenant_id,
                    Client.id != client_id,
                )
            ).scalar_one_or_none()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Client code '{update_data['code']}' already exists",
                )

        for field, value in update_data.items():
            setattr(client, field, value)

        db.commit()
        db.refresh(client)

        return ClientResponse.model_validate(client)

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        # Rollback on any database error
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
    """
    Delete a client

    Args:
        client_id: Client UUID
        current_user: Current authenticated counselor
        tenant_id: Tenant ID
        db: Database session

    Raises:
        HTTPException: 404 if client not found or not owned by counselor
    """
    result = db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    db.delete(client)
    db.commit()
