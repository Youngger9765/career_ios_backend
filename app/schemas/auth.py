"""
Authentication schemas
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.password_validator import validate_password_strength
from app.models.counselor import CounselorRole


class LoginRequest(BaseModel):
    """Login credentials"""

    email: EmailStr
    password: str
    tenant_id: str


class RegisterRequest(BaseModel):
    """Registration request - simplified to only require email and password"""

    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters with letters and digits")
    tenant_id: str
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, min_length=1)
    role: CounselorRole = CounselorRole.COUNSELOR

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength requirements"""
        validate_password_strength(v)
        return v


class TokenResponse(BaseModel):
    """JWT token response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RegisterResponse(BaseModel):
    """Registration response with token and email verification status"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    email_verified: bool = False
    verification_email_sent: bool = False
    message: str


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
    email_verified: bool = False  # Email verification status
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
    source: Optional[str] = Field(
        None,
        description="Request source: 'app' (from iOS) or 'web' (from browser)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "tenant_id": "test_tenant",
                "source": "app",
            }
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


class VerifyCodeRequest(BaseModel):
    """Verification code verification request"""

    email: EmailStr
    verification_code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")
    tenant_id: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "verification_code": "123456",
                "tenant_id": "test_tenant",
            }
        }
    )


class VerifyCodeResponse(BaseModel):
    """Verification code verification response"""

    valid: bool
    message: str
    token: Optional[str] = None  # JWT token for password reset (only if valid)


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""

    verification_code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$")
    new_password: str = Field(..., min_length=8, description="Password must be at least 8 characters with letters and digits")
    email: EmailStr
    tenant_id: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password strength requirements"""
        validate_password_strength(v)
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "verification_code": "123456",
                "new_password": "SecurePass1",
                "email": "user@example.com",
                "tenant_id": "test_tenant",
            }
        }
    )


class PasswordResetConfirmResponse(BaseModel):
    """Password reset confirmation response"""

    message: str


class VerifyEmailRequest(BaseModel):
    """Email verification request"""

    token: str = Field(..., description="JWT verification token from email")


class VerifyEmailResponse(BaseModel):
    """Email verification response"""

    message: str
    email: str


class ResendVerificationRequest(BaseModel):
    """Resend verification email request"""

    email: EmailStr
    tenant_id: str


class ResendVerificationResponse(BaseModel):
    """Resend verification email response"""

    message: str


# Resolve forward references for LoginResponse
LoginResponse.model_rebuild()
