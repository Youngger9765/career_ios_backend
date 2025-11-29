"""
Reports API Schemas
Request/response models for report generation and management
"""
from uuid import UUID

from pydantic import BaseModel


class GenerateReportRequest(BaseModel):
    """Request schema for generating report"""

    session_id: UUID
    report_type: str = "enhanced"  # enhanced | legacy
    rag_system: str = "openai"  # openai | gemini


class ProcessingStatus(BaseModel):
    """Report processing status"""

    status: str  # "processing"
    message: str


class GenerateReportResponse(BaseModel):
    """Async report generation response (HTTP 202)"""

    session_id: UUID
    report_id: UUID
    report: ProcessingStatus
    quality_summary: None = None
