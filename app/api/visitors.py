from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.visitor import VisitorResponse, VisitorCreate, VisitorUpdate
from app.utils.mock_data import mock_generator

router = APIRouter()


@router.get("/", response_model=List[VisitorResponse])
async def list_visitors():
    """List all visitors (mock data)"""
    visitors = [mock_generator.generate_visitor() for _ in range(10)]
    return [VisitorResponse(**visitor) for visitor in visitors]


@router.get("/{visitor_id}", response_model=VisitorResponse)
async def get_visitor(visitor_id: str):
    """Get specific visitor"""
    visitor = mock_generator.generate_visitor()
    visitor["id"] = visitor_id
    return VisitorResponse(**visitor)


@router.post("/", response_model=VisitorResponse, status_code=201)
async def create_visitor(visitor: VisitorCreate):
    """Create new visitor"""
    visitor_data = mock_generator.generate_visitor()
    visitor_data.update(visitor.dict())
    return VisitorResponse(**visitor_data)


@router.put("/{visitor_id}", response_model=VisitorResponse)
async def update_visitor(visitor_id: str, visitor: VisitorUpdate):
    """Update visitor info"""
    visitor_data = mock_generator.generate_visitor()
    visitor_data["id"] = visitor_id
    visitor_data.update(visitor.dict(exclude_unset=True))
    return VisitorResponse(**visitor_data)