from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseSchema


# Recording-related schemas
class RecordingSegment(BaseModel):
    """錄音片段"""

    segment_number: int
    start_time: str
    end_time: str
    duration_seconds: int
    transcript_text: str
    transcript_sanitized: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "segment_number": 1,
                    "start_time": "2025-01-15 10:00",
                    "end_time": "2025-01-15 10:30",
                    "duration_seconds": 1800,
                    "transcript_text": "諮詢師：今天想聊什麼？\n個案：我最近對未來感到很迷惘...",
                    "transcript_sanitized": "諮詢師：今天想聊什麼？\n個案：我最近對未來感到很迷惘...",
                }
            ]
        }
    }


class AppendRecordingRequest(BaseModel):
    """Append 錄音片段請求（iOS 友善版本）"""

    start_time: str
    end_time: str
    duration_seconds: int
    transcript_text: str
    transcript_sanitized: Optional[str] = None


class AppendRecordingResponse(BaseModel):
    """Append 錄音片段響應"""

    session_id: UUID
    recording_added: RecordingSegment
    total_recordings: int
    transcript_text: str
    updated_at: datetime


# Session CRUD schemas
class SessionCreateRequest(BaseModel):
    """創建會談記錄請求"""

    case_id: UUID
    session_date: str
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    transcript: Optional[str] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    reflection: Optional[dict] = None
    recordings: Optional[List[RecordingSegment]] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "case_id": "123e4567-e89b-12d3-a456-426614174000",
                    "session_date": "2025-01-15",
                    "start_time": "2025-01-15 10:00",
                    "end_time": "2025-01-15 11:30",
                    "notes": "個案對職涯選擇表現出積極態度",
                }
            ]
        }
    }


class SessionUpdateRequest(BaseModel):
    """更新會談記錄請求"""

    session_date: Optional[str] = None
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    transcript: Optional[str] = None
    notes: Optional[str] = None
    duration_minutes: Optional[int] = None
    reflection: Optional[dict] = None
    recordings: Optional[List[RecordingSegment]] = None


class SessionResponse(BaseModel):
    """會談記錄響應"""

    id: UUID
    client_id: UUID
    client_name: Optional[str] = None
    client_code: Optional[str] = None
    case_id: UUID
    session_number: int
    session_date: datetime
    name: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    transcript_text: Optional[str] = None
    summary: Optional[str] = None
    duration_minutes: Optional[int]
    notes: Optional[str]
    reflection: Optional[dict] = None
    recordings: Optional[List[RecordingSegment]] = None
    has_report: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """會談記錄列表響應"""

    total: int
    items: List[SessionResponse]


# Timeline schemas
class TimelineSessionItem(BaseModel):
    """單次會談的時間線資訊"""

    session_id: UUID
    session_number: int
    date: str
    time_range: Optional[str] = None
    summary: Optional[str] = None
    has_report: bool
    report_id: Optional[UUID] = None


class SessionTimelineResponse(BaseModel):
    """會談歷程時間線響應"""

    client_id: UUID
    client_name: str
    client_code: str
    total_sessions: int
    sessions: List[TimelineSessionItem]


# Reflection schemas
class ReflectionRequest(BaseModel):
    """諮詢師反思請求"""

    reflection: dict


class ReflectionResponse(BaseModel):
    """諮詢師反思響應"""

    session_id: UUID
    reflection: Optional[dict] = None
    updated_at: datetime


# Legacy schemas (for backward compatibility)
class SessionBase(BaseSchema):
    session_date: datetime
    duration_minutes: Optional[int] = None
    room_number: Optional[str] = None
    notes: Optional[str] = None
    key_points: Optional[str] = None


class SessionCreate(SessionBase):
    case_id: UUID
    session_number: int


class AudioUpload(BaseSchema):
    session_id: UUID
    file_name: str
    file_size: int
    duration_seconds: Optional[int] = None


class KeywordAnalysisRequest(BaseModel):
    """Request for session-based keyword analysis (RESTful)."""

    transcript_segment: str = Field(
        ...,
        min_length=1,
        description="Partial transcript text to analyze",
    )

    @field_validator("transcript_segment")
    @classmethod
    def validate_transcript(cls, v: str) -> str:
        """Validate transcript segment is not empty."""
        if not v or not v.strip():
            raise ValueError("Transcript segment cannot be empty")
        return v.strip()


class KeywordAnalysisResponse(BaseModel):
    """Response for session-based keyword analysis with counselor insights."""

    keywords: list[str] = Field(description="Extracted keywords from transcript")
    categories: list[str] = Field(description="Categories of extracted keywords")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score of keyword extraction",
    )
    counselor_insights: str = Field(
        description="Insights and reminders for the counselor based on the analysis"
    )


class AnalysisLogEntry(BaseModel):
    """Single analysis log entry"""

    log_index: int = Field(description="Index of this log in the array (0-based)")
    analyzed_at: str = Field(description="ISO 8601 timestamp of analysis")
    transcript_segment: str = Field(description="Analyzed transcript segment")
    keywords: list[str] = Field(description="Extracted keywords")
    categories: list[str] = Field(description="Categories")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    counselor_insights: str = Field(description="Counselor insights")
    counselor_id: str = Field(description="ID of counselor who performed analysis")
    fallback: Optional[bool] = Field(
        default=False, description="Whether this was a fallback analysis"
    )


class AnalysisLogsResponse(BaseModel):
    """Response for GET analysis logs"""

    session_id: UUID
    total_logs: int = Field(description="Total number of analysis logs")
    logs: list[AnalysisLogEntry] = Field(description="List of analysis logs")
