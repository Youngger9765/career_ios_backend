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

    # Session info (for list display)
    client_name: Optional[str] = None  # 個案姓名
    session_number: Optional[int] = None  # 第幾次會談

    # Report content
    content_json: Optional[Dict[str, Any]]  # AI 原始生成 (處理中時為 None)
    content_markdown: Optional[str]  # AI 原始生成的 Markdown 格式
    edited_content_json: Optional[Dict[str, Any]]  # 諮商師編輯版本
    edited_content_markdown: Optional[str]  # 諮商師編輯後的 Markdown 格式
    edited_at: Optional[str]  # 最後編輯時間
    edit_count: Optional[int]  # 編輯次數
    citations_json: Optional[List[Dict[str, Any]]]

    # Quality metrics
    quality_score: Optional[int]
    quality_grade: Optional[str]
    quality_strengths: Optional[List[str]]
    quality_weaknesses: Optional[List[str]]

    # Error handling
    error_message: Optional[str]

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


class ReportUpdateRequest(BaseModel):
    """Schema for updating report content"""

    edited_content_json: Optional[Dict[str, Any]] = None  # 完整的編輯後報告 JSON（選填）
    edited_content_markdown: Optional[str] = None  # 前端編輯後的 Markdown 字串（選填）


class ReportUpdateResponse(BaseModel):
    """Schema for report update response"""

    id: UUID
    edited_content_json: Dict[str, Any]
    edited_content_markdown: str  # 儲存的 Markdown 格式
    edited_at: str
    edit_count: int
