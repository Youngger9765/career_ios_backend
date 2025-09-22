from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.user import UserResponse, UserCreate
from app.utils.mock_data import mock_generator

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user():
    """Get current user info"""
    user_data = mock_generator.generate_user()
    return UserResponse(**user_data)


@router.get("/", response_model=List[UserResponse])
async def list_users():
    """List all users (mock data)"""
    users = [mock_generator.generate_user() for _ in range(5)]
    return [UserResponse(**user) for user in users]


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    """Create new user (mock)"""
    user_data = mock_generator.generate_user()
    user_data.update(user.dict(exclude={"password"}))
    return UserResponse(**user_data)