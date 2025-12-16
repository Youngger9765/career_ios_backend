"""
Authentication schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.counselor import CounselorRole


class LoginRequest(BaseModel):
    """Login credentials"""

    email: EmailStr
    password: str
    tenant_id: str


class RegisterRequest(BaseModel):
    """Registration request"""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    tenant_id: str
    role: CounselorRole = CounselorRole.COUNSELOR


class TokenResponse(BaseModel):
    """JWT token response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class CounselorInfo(BaseModel):
    """Current counselor information"""

    id: UUID
    email: str
    username: str
    full_name: str
    role: str
    tenant_id: str
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CounselorUpdate(BaseModel):
    """Counselor update request"""

    full_name: Optional[str] = None
    username: Optional[str] = None
