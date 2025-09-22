from pydantic import EmailStr, Field
from typing import Optional
from typing import Union
from app.schemas.base import BaseSchema, BaseResponse
from app.models.user import UserRole


class UserBase(BaseSchema):
    email: EmailStr
    username: str
    full_name: str
    role: UserRole = UserRole.COUNSELOR


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseSchema):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(BaseResponse, UserBase):
    is_active: bool


class UserLogin(BaseSchema):
    username: str
    password: str


class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseSchema):
    username: Optional[str] = None