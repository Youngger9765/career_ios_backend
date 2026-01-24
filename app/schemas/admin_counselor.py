"""
Admin Counselor Management Pydantic Schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ============================================================================
# Response Schemas
# ============================================================================


class CounselorDetailResponse(BaseModel):
    """Full counselor details for admin view"""

    id: UUID
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    tenant_id: str
    role: str
    is_active: bool
    total_credits: int
    credits_used: int
    available_credits: int
    subscription_expires_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CounselorListItem(BaseModel):
    """Counselor summary for list view"""

    id: UUID
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    tenant_id: str
    role: str
    is_active: bool
    total_credits: int
    credits_used: int
    available_credits: int
    subscription_expires_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CounselorListResponse(BaseModel):
    """Paginated list of counselors"""

    total: int = Field(..., description="Total number of counselors")
    counselors: list[CounselorListItem] = Field(..., description="List of counselors")


# ============================================================================
# Request Schemas
# ============================================================================


class CounselorUpdateRequest(BaseModel):
    """Request to update counselor (admin only)"""

    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    role: Optional[str] = Field(None, description="Role: counselor, supervisor, admin")
    is_active: Optional[bool] = None
    subscription_expires_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Updated Name",
                "phone": "+886987654321",
                "role": "counselor",
                "is_active": True,
                "subscription_expires_at": "2026-12-31T23:59:59Z",
            }
        }
    )


class CounselorCreateRequest(BaseModel):
    """Request to create new counselor (admin only)"""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    password: str = Field(..., min_length=6, description="Password set by admin")
    tenant_id: str = Field(..., description="Tenant ID: career, island, island_parents")
    role: str = Field(
        default="counselor", description="Role: counselor, supervisor, admin"
    )
    total_credits: int = Field(default=0, ge=0, description="Initial credits")
    subscription_expires_at: Optional[datetime] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "newuser@example.com",
                "username": "newuser",
                "full_name": "New User",
                "phone": "+886912345678",
                "password": "secure_password_123",
                "tenant_id": "island_parents",
                "role": "counselor",
                "total_credits": 500,
                "subscription_expires_at": "2026-12-31T23:59:59Z",
            }
        }
    )


class CounselorCreateResponse(BaseModel):
    """Response after creating counselor"""

    counselor: CounselorDetailResponse
    temporary_password: Optional[str] = Field(
        None, description="Temporary password (deprecated, now set by admin)"
    )


# ============================================================================
# Delete Response Schema
# ============================================================================


class CounselorDeleteResponse(BaseModel):
    """Response after deleting counselor"""

    success: bool
    message: str
    counselor_id: UUID
