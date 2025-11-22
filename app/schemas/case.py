from typing import Optional
from uuid import UUID

from app.models.case import CaseStatus
from app.schemas.base import BaseResponse, BaseSchema


class CaseBase(BaseSchema):
    case_number: Optional[str] = None
    status: CaseStatus = CaseStatus.NOT_STARTED
    summary: Optional[str] = None
    goals: Optional[str] = None
    problem_description: Optional[str] = None


class CaseCreate(CaseBase):
    client_id: UUID


class CaseUpdate(BaseSchema):
    status: Optional[CaseStatus] = None
    summary: Optional[str] = None
    goals: Optional[str] = None
    problem_description: Optional[str] = None


class CaseResponse(BaseResponse, CaseBase):
    counselor_id: UUID
    client_id: UUID
