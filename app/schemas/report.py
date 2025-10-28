from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class ReportResponse(BaseModel):
    """Schema for report response"""

    id: UUID
    session_id: UUID
    client_id: UUID
    created_by_id: UUID
    tenant_id: str
    version: int
    status: str
    mode: Optional[str]

    # Report content
    content_json: Dict[str, Any]
    citations_json: Optional[List[Dict[str, Any]]]

    # Quality metrics
    quality_score: Optional[int]
    quality_grade: Optional[str]
    quality_strengths: Optional[List[str]]
    quality_weaknesses: Optional[List[str]]

    # AI metadata
    ai_model: Optional[str]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]

    # Legacy fields
    summary: Optional[str]
    analysis: Optional[str]
    recommendations: Optional[str]
    action_items: Optional[List[Dict[str, Any]]]

    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Schema for paginated report list"""

    total: int
    items: List[ReportResponse]
