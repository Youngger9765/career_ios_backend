"""
Session Usage Schemas - Analysis Logs and Usage Tracking
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# SessionAnalysisLog Schemas
class SessionAnalysisLogCreate(BaseModel):
    """Create session analysis log request"""

    analysis_type: str = Field(..., description="Type of analysis performed")
    transcript: Optional[str] = Field(None, description="Transcript analyzed")
    analysis_result: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Analysis results"
    )
    safety_level: Optional[str] = Field(
        None, description="Safety level: green, yellow, red"
    )
    risk_indicators: Optional[List[str]] = Field(
        default_factory=list, description="Risk indicators identified"
    )
    rag_documents: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="RAG documents used"
    )
    rag_sources: Optional[List[str]] = Field(
        default_factory=list, description="RAG source references"
    )
    token_usage: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Token usage details"
    )


class SessionAnalysisLogResponse(BaseModel):
    """Session analysis log response"""

    id: UUID
    session_id: UUID
    counselor_id: UUID
    tenant_id: str
    analysis_type: str
    transcript: Optional[str]
    analysis_result: Optional[Dict[str, Any]]
    safety_level: Optional[str]
    risk_indicators: Optional[List[str]]
    rag_documents: Optional[List[Dict[str, Any]]]
    rag_sources: Optional[List[str]]
    token_usage: Optional[Dict[str, Any]]
    analyzed_at: datetime

    class Config:
        from_attributes = True


class SessionAnalysisLogListResponse(BaseModel):
    """Session analysis log list response"""

    total: int
    items: List[SessionAnalysisLogResponse]


# SessionUsage Schemas
class SessionUsageCreate(BaseModel):
    """Create session usage request"""

    usage_type: str = Field(
        ..., description="Type of usage: voice_call, text_analysis, etc."
    )
    status: str = Field(
        default="in_progress", description="Status: in_progress, completed, failed"
    )
    start_time: Optional[datetime] = Field(None, description="When usage started")
    end_time: Optional[datetime] = Field(None, description="When usage ended")
    pricing_rule: Dict[str, Any] = Field(
        ...,
        description="Pricing configuration: {unit: 'minute'|'token'|'analysis', rate: float}",
    )
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds")
    analysis_count: Optional[int] = Field(None, description="Number of analyses")
    token_usage: Optional[Dict[str, Any]] = Field(
        None, description="Token usage details"
    )


class SessionUsageUpdate(BaseModel):
    """Update session usage request"""

    status: Optional[str] = Field(
        None, description="Status: in_progress, completed, failed"
    )
    end_time: Optional[datetime] = Field(None, description="When usage ended")
    duration_seconds: Optional[int] = Field(None, description="Duration in seconds")
    analysis_count: Optional[int] = Field(None, description="Number of analyses")
    total_tokens: Optional[int] = Field(None, description="Total tokens")
    credits_consumed: Optional[float] = Field(None, description="Credits consumed")
    credit_deducted: Optional[bool] = Field(
        None, description="Whether credits deducted"
    )


class SessionUsageResponse(BaseModel):
    """Session usage response"""

    id: UUID
    session_id: UUID
    counselor_id: UUID
    tenant_id: str
    usage_type: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    analysis_count: Optional[int]
    token_usage: Optional[Dict[str, Any]]
    pricing_rule: Dict[str, Any]
    credits_deducted: float
    credit_deducted: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
