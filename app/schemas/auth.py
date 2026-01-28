"""
Authentication schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.counselor import CounselorRole


class LoginRequest(BaseModel):
    """Login credentials"""

    email: EmailStr
    password: str
    tenant_id: str


class RegisterRequest(BaseModel):
    """Registration request - simplified to only require email and password"""

    email: EmailStr
    password: str = Field(..., min_length=8)
    tenant_id: str
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, min_length=1)
    role: CounselorRole = CounselorRole.COUNSELOR


class TokenResponse(BaseModel):
    """JWT token response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class LoginResponse(BaseModel):
    """Login response with token and user info"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: "CounselorInfo"  # Forward reference


class CounselorInfo(BaseModel):
    """Current counselor information"""

    id: UUID
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    tenant_id: str
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]

    # Credit system fields
    available_credits: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class CounselorUpdate(BaseModel):
    """Counselor update request"""

    full_name: Optional[str] = None
    username: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Password reset request"""

    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    tenant_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "user@example.com", "tenant_id": "test_tenant"}
        }
    )


class PasswordResetResponse(BaseModel):
    """Password reset request response"""

    message: str
    token: Optional[str] = None  # Only for testing/development


class PasswordResetVerifyResponse(BaseModel):
    """Password reset token verification response"""

    valid: bool
    email: Optional[str] = None
    message: Optional[str] = None


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""

    token: str
    new_password: str = Field(..., min_length=8)


class PasswordResetConfirmResponse(BaseModel):
    """Password reset confirmation response"""

    message: str


# Resolve forward references for LoginResponse
LoginResponse.model_rebuild()
