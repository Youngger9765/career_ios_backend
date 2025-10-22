"""Evaluation Test Sets API - 評估測試集管理"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.evaluation import EvaluationTestSet

router = APIRouter(prefix="/api/rag/evaluation/testsets", tags=["evaluation-testsets"])


# Schemas
class TestCase(BaseModel):
    """單個測試案例"""
    question: str
    ground_truth: Optional[str] = None
    contexts: Optional[List[str]] = None
    metadata: Optional[dict] = None


class TestSetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    test_cases: List[TestCase]


class TestSetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    test_cases: Optional[List[TestCase]] = None


class TestSetResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    category: Optional[str]
    total_cases: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class TestSetDetailResponse(TestSetResponse):
    test_cases: List[dict]


# API Endpoints
@router.post("/", response_model=TestSetResponse)
async def create_testset(
    testset_data: TestSetCreate,
    db: Session = Depends(get_db)
):
    """建立測試集"""
    test_cases_json = [case.model_dump() for case in testset_data.test_cases]

    testset = EvaluationTestSet(
        name=testset_data.name,
        description=testset_data.description,
        category=testset_data.category,
        test_cases=test_cases_json,
        total_cases=len(test_cases_json),
        is_active=True
    )

    db.add(testset)
    db.commit()
    db.refresh(testset)
    return testset


@router.get("/", response_model=List[TestSetResponse])
async def list_testsets(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """列出測試集"""
    query = db.query(EvaluationTestSet)

    if category:
        query = query.filter(EvaluationTestSet.category == category)
    if is_active is not None:
        query = query.filter(EvaluationTestSet.is_active == is_active)

    return query.order_by(EvaluationTestSet.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{testset_id}", response_model=TestSetDetailResponse)
async def get_testset(testset_id: str, db: Session = Depends(get_db)):
    """取得測試集詳情（包含所有測試案例）"""
    testset = db.query(EvaluationTestSet).filter(
        EvaluationTestSet.id == uuid.UUID(testset_id)
    ).first()

    if not testset:
        raise HTTPException(status_code=404, detail="Test set not found")

    return testset


@router.put("/{testset_id}", response_model=TestSetResponse)
async def update_testset(
    testset_id: str,
    testset_update: TestSetUpdate,
    db: Session = Depends(get_db)
):
    """更新測試集"""
    testset = db.query(EvaluationTestSet).filter(
        EvaluationTestSet.id == uuid.UUID(testset_id)
    ).first()

    if not testset:
        raise HTTPException(status_code=404, detail="Test set not found")

    update_data = testset_update.model_dump(exclude_unset=True)

    # 如果更新 test_cases，要更新 total_cases
    if "test_cases" in update_data:
        test_cases_json = [case.model_dump() for case in testset_update.test_cases]
        update_data["test_cases"] = test_cases_json
        update_data["total_cases"] = len(test_cases_json)

    for field, value in update_data.items():
        setattr(testset, field, value)

    testset.updated_at = datetime.now()
    db.commit()
    db.refresh(testset)
    return testset


@router.delete("/{testset_id}")
async def delete_testset(testset_id: str, db: Session = Depends(get_db)):
    """刪除測試集"""
    testset = db.query(EvaluationTestSet).filter(
        EvaluationTestSet.id == uuid.UUID(testset_id)
    ).first()

    if not testset:
        raise HTTPException(status_code=404, detail="Test set not found")

    db.delete(testset)
    db.commit()
    return {"message": "Test set deleted successfully"}


@router.post("/{testset_id}/toggle")
async def toggle_testset(testset_id: str, db: Session = Depends(get_db)):
    """啟用/停用測試集"""
    testset = db.query(EvaluationTestSet).filter(
        EvaluationTestSet.id == uuid.UUID(testset_id)
    ).first()

    if not testset:
        raise HTTPException(status_code=404, detail="Test set not found")

    testset.is_active = not testset.is_active
    testset.updated_at = datetime.now()
    db.commit()

    return {"is_active": testset.is_active}


@router.post("/{testset_id}/duplicate", response_model=TestSetResponse)
async def duplicate_testset(testset_id: str, db: Session = Depends(get_db)):
    """複製測試集"""
    original = db.query(EvaluationTestSet).filter(
        EvaluationTestSet.id == uuid.UUID(testset_id)
    ).first()

    if not original:
        raise HTTPException(status_code=404, detail="Test set not found")

    new_testset = EvaluationTestSet(
        name=f"{original.name} (副本)",
        description=original.description,
        category=original.category,
        test_cases=original.test_cases,
        total_cases=original.total_cases,
        is_active=False
    )

    db.add(new_testset)
    db.commit()
    db.refresh(new_testset)
    return new_testset
