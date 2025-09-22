from fastapi import APIRouter, HTTPException, status
from app.schemas.user import UserLogin, Token
from app.utils.mock_data import mock_generator
import uuid

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login endpoint - returns mock JWT tokens"""
    if credentials.username == "demo" and credentials.password == "demo1234":
        return Token(
            access_token=f"mock_access_token_{uuid.uuid4()}",
            refresh_token=f"mock_refresh_token_{uuid.uuid4()}",
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
    """Refresh access token"""
    if refresh_token.startswith("mock_refresh_token_"):
        return Token(
            access_token=f"mock_access_token_{uuid.uuid4()}",
            refresh_token=f"mock_refresh_token_{uuid.uuid4()}",
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token"
    )


@router.post("/logout")
async def logout():
    """Logout endpoint"""
    return {"message": "Successfully logged out"}