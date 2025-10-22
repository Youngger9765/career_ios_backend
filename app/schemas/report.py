from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models.report import ReportStatus
from app.schemas.base import BaseResponse, BaseSchema


class ReportBase(BaseSchema):
    summary: str
    analysis: str
    recommendations: str
    action_items: List[Dict[str, Any]] = []


class ReportCreate(ReportBase):
    session_id: UUID
    created_by_id: UUID


class ReportUpdate(BaseSchema):
    status: Optional[ReportStatus] = None
    summary: Optional[str] = None
    analysis: Optional[str] = None
    recommendations: Optional[str] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    review_notes: Optional[str] = None


class ReportResponse(BaseResponse, ReportBase):
    session_id: UUID
    created_by_id: UUID
    version: int
    status: ReportStatus
    ai_model: Optional[str] = None
    reviewed_by_id: Optional[UUID] = None
    review_notes: Optional[str] = None
