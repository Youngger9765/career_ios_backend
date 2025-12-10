"""
Client (個案) schemas
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    """Base client schema with common fields"""

    # Core identification
    code: Optional[str] = Field(
        None, description="Anonymous client code (auto-generated if not provided)"
    )
    name: str = Field(..., description="Client real name")
    nickname: Optional[str] = Field(None, description="Nickname")

    # Common required fields (all tenants)
    email: str = Field(..., description="Email address for consultation or records")
    gender: str = Field(..., description="Gender: 男／女／其他／不透露")
    birth_date: date = Field(
        ..., description="Birth date (Western calendar, 1900-2025)"
    )
    phone: str = Field(..., description="Mobile phone number")

    # Tenant-specific required fields (optional for cross-tenant compatibility)
    identity_option: Optional[str] = Field(
        None, description="Identity: 學生／社會新鮮人／轉職者／在職者／其他"
    )
    current_status: Optional[str] = Field(
        None, description="Current situation for quick case classification"
    )

    # Optional fields
    education: Optional[str] = Field(
        None, description="Education: 高中／大學／研究所等"
    )
    current_job: Optional[str] = Field(
        None, description="Current job (occupation/years of experience)"
    )
    career_status: Optional[str] = Field(
        None, description="Career status: 探索中／轉職準備／面試中／已在職等"
    )
    occupation: Optional[str] = Field(None, description="Occupation")
    location: Optional[str] = Field(None, description="Location/residence")

    # Consultation and medical history
    has_consultation_history: Optional[str] = Field(
        None, description="Past consultation experience (Yes/No + text)"
    )
    has_mental_health_history: Optional[str] = Field(
        None, description="Mental/psychiatric history (Yes/No + text, sensitive)"
    )

    # Additional information
    economic_status: Optional[str] = Field(None, description="Economic status")
    family_relations: Optional[str] = Field(
        None, description="Family relations description"
    )
    other_info: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Other flexible information"
    )
    tags: Optional[List[str]] = Field(
        default_factory=list, description="Tags for categorization"
    )
    notes: Optional[str] = Field(None, description="Private counselor notes")


class ClientCreate(ClientBase):
    """Schema for creating a new client"""

    pass


class ClientUpdate(BaseModel):
    """Schema for updating client (all fields optional)"""

    # Core identification
    code: Optional[str] = None
    name: Optional[str] = None
    nickname: Optional[str] = None

    # Required fields (optional in update)
    email: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    identity_option: Optional[str] = None
    current_status: Optional[str] = None
    phone: Optional[str] = None

    # Optional fields
    education: Optional[str] = None
    current_job: Optional[str] = None
    career_status: Optional[str] = None
    occupation: Optional[str] = None
    location: Optional[str] = None

    # Consultation and medical history
    has_consultation_history: Optional[str] = None
    has_mental_health_history: Optional[str] = None

    # Additional information
    economic_status: Optional[str] = None
    family_relations: Optional[str] = None
    other_info: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class ClientResponse(ClientBase):
    """Schema for client response"""

    id: UUID
    counselor_id: UUID
    tenant_id: str
    age: Optional[int] = Field(
        None, description="Age (auto-calculated from birth_date)"
    )
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    """Schema for paginated client list"""

    total: int
    items: List[ClientResponse]
