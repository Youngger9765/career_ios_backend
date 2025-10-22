from typing import Optional
from uuid import UUID

from app.models.case import CaseStatus
from app.schemas.base import BaseResponse, BaseSchema


class CaseBase(BaseSchema):
    case_number: str
    status: CaseStatus = CaseStatus.ACTIVE
    summary: Optional[str] = None
    goals: Optional[str] = None


class CaseCreate(CaseBase):
    counselor_id: UUID
    visitor_id: UUID


class CaseUpdate(BaseSchema):
    status: Optional[CaseStatus] = None
    summary: Optional[str] = None
    goals: Optional[str] = None


class CaseResponse(BaseResponse, CaseBase):
    counselor_id: UUID
    visitor_id: UUID
