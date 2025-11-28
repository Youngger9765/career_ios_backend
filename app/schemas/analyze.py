"""Schemas for analysis endpoints."""
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TranscriptAnalysisContext(BaseModel):
    """Context options for transcript analysis."""

    include_client_profile: bool = Field(
        default=True,
        description="Include client profile in AI context",
    )
    include_case_goals: bool = Field(
        default=True,
        description="Include case goals in AI context",
    )


class TranscriptKeywordRequest(BaseModel):
    """Request schema for transcript keyword analysis."""

    client_id: UUID
    case_id: UUID
    transcript_segment: str = Field(
        ...,
        min_length=1,
        description="Partial transcript text to analyze",
    )
    context: TranscriptAnalysisContext = Field(
        default_factory=TranscriptAnalysisContext
    )

    @field_validator("transcript_segment")
    @classmethod
    def validate_transcript(cls, v: str) -> str:
        """Validate transcript segment is not empty."""
        if not v or not v.strip():
            raise ValueError("Transcript segment cannot be empty")
        return v.strip()


class TranscriptKeywordResponse(BaseModel):
    """Response schema for transcript keyword analysis."""

    keywords: list[str] = Field(description="Extracted keywords from transcript")
    categories: list[str] = Field(description="Categories of extracted keywords")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score of keyword extraction",
    )
    segment_id: str = Field(description="Temporary UUID for this segment (not stored)")
