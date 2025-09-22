from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.schemas.case import CaseResponse, CaseCreate, CaseUpdate
from app.utils.mock_data import mock_generator
from app.models.case import CaseStatus

router = APIRouter()


@router.get("/", response_model=List[CaseResponse])
async def list_cases(
    counselor_id: Optional[str] = Query(None),
    status: Optional[CaseStatus] = Query(None),
    limit: int = Query(10, le=100)
):
    """List cases with optional filters"""
    cases = [mock_generator.generate_case() for _ in range(limit)]
    
    if counselor_id:
        for case in cases:
            case["counselor_id"] = counselor_id
    
    if status:
        for case in cases:
            case["status"] = status
    
    return [CaseResponse(**case) for case in cases]


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str):
    """Get specific case details"""
    case = mock_generator.generate_case()
    case["id"] = case_id
    return CaseResponse(**case)


@router.post("/", response_model=CaseResponse, status_code=201)
async def create_case(case: CaseCreate):
    """Create new case"""
    case_data = mock_generator.generate_case()
    case_data.update(case.dict())
    return CaseResponse(**case_data)


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(case_id: str, case: CaseUpdate):
    """Update case information"""
    case_data = mock_generator.generate_case()
    case_data["id"] = case_id
    case_data.update(case.dict(exclude_unset=True))
    return CaseResponse(**case_data)