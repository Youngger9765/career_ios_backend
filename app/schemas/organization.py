"""
Organization schemas for API requests and responses
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    """Base organization schema"""

    name: str = Field(
        ..., min_length=1, max_length=200, description="Organization name"
    )
    description: Optional[str] = Field(None, description="Organization description")


class OrganizationCreate(OrganizationBase):
    """Create organization request"""

    tenant_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique tenant identifier",
        pattern=r"^[a-zA-Z0-9_-]+$",
    )


class OrganizationUpdate(BaseModel):
    """Update organization request"""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """Organization response with full details"""

    id: UUID
    tenant_id: str
    is_active: bool
    counselor_count: int = Field(0, description="Number of active counselors")
    client_count: int = Field(0, description="Number of active clients")
    session_count: int = Field(0, description="Total number of sessions")
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class OrganizationListResponse(BaseModel):
    """List of organizations with pagination"""

    organizations: list[OrganizationResponse]
    total: int
    page: int = 1
    page_size: int = 20


class OrganizationStats(BaseModel):
    """Organization statistics"""

    tenant_id: str
    name: str
    counselor_count: int
    client_count: int
    session_count: int
    active_sessions_count: int = Field(0, description="Currently active sessions")
    total_session_duration: float = Field(
        0.0, description="Total session duration in hours"
    )

    class Config:
        from_attributes = True
