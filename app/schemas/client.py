"""
Client (個案) schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ClientBase(BaseModel):
    """Base client schema with common fields"""

    code: str = Field(..., description="Anonymous client code")
    name: str = Field(..., description="Client name (pseudonym)")
    nickname: Optional[str] = Field(None, description="Nickname")
    age: Optional[int] = Field(None, ge=0, le=150, description="Age")
    gender: Optional[str] = Field(None, description="Gender")
    occupation: Optional[str] = Field(None, description="Occupation")
    education: Optional[str] = Field(None, description="Education level")
    location: Optional[str] = Field(None, description="Location/residence")
    economic_status: Optional[str] = Field(None, description="Economic status")
    family_relations: Optional[str] = Field(None, description="Family relations description")
    other_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Other flexible information")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags for categorization")
    notes: Optional[str] = Field(None, description="Private counselor notes")


class ClientCreate(ClientBase):
    """Schema for creating a new client"""

    pass


class ClientUpdate(BaseModel):
    """Schema for updating client (all fields optional)"""

    code: Optional[str] = None
    name: Optional[str] = None
    nickname: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = None
    occupation: Optional[str] = None
    education: Optional[str] = None
    location: Optional[str] = None
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
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    """Schema for paginated client list"""

    total: int
    items: List[ClientResponse]
