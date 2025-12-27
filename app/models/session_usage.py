"""
SessionUsage Model - Flexible session usage and credit tracking
Supports multiple pricing models: time-based, token-based, analysis-based
"""
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)

from app.core.database import Base
from app.models.base import GUID, BaseModel


class SessionUsage(Base, BaseModel):
    """
    Track session usage with flexible pricing models.
    One record per session. Stores raw metrics and pricing configuration.
    BigQuery-compatible field types.
    """

    __tablename__ = "session_usages"

    # Core identifiers (session_id is UNIQUE - one usage record per session)
    session_id = Column(
        GUID(),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Session being tracked (one-to-one relationship)",
    )
    counselor_id = Column(
        GUID(),
        ForeignKey("counselors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Counselor who owns this session",
    )
    tenant_id = Column(
        String,
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenancy isolation",
    )

    # Usage metadata
    usage_type = Column(
        String(50),
        nullable=True,
        comment="Type: voice_call, text_analysis, keyword_analysis, etc.",
    )
    status = Column(
        String(20),
        nullable=False,
        index=True,
        default="in_progress",
        comment="Status: in_progress, completed, failed",
    )

    # Time tracking
    start_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When usage started",
    )
    end_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When usage ended",
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Alternative started timestamp",
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When status changed to completed",
    )

    # Raw metrics (always preserved for recalculation)
    duration_seconds = Column(
        Integer,
        nullable=True,
        comment="Duration in seconds (calculated from start_time and end_time)",
    )
    analysis_count = Column(
        Integer,
        nullable=True,
        default=0,
        comment="Number of analyses performed",
    )

    # Token metrics (raw data)
    total_prompt_tokens = Column(
        Integer,
        nullable=True,
        default=0,
        comment="Total prompt tokens across all analyses",
    )
    total_completion_tokens = Column(
        Integer,
        nullable=True,
        default=0,
        comment="Total completion tokens across all analyses",
    )
    total_tokens = Column(
        Integer,
        nullable=True,
        default=0,
        comment="Total tokens (prompt + completion)",
    )
    total_cached_tokens = Column(
        Integer,
        nullable=True,
        default=0,
        comment="Total cached tokens",
    )

    # Token usage detail (JSON for flexibility)
    token_usage = Column(
        JSON,
        nullable=True,
        default=dict,
        comment="Detailed token usage: {prompt_tokens, completion_tokens, total_tokens, model}",
    )

    # Cost estimation
    estimated_cost_usd = Column(
        Numeric(10, 6),
        nullable=True,
        comment="Estimated cost in USD",
    )

    # Flexible pricing configuration (CRITICAL: NO hardcoded logic)
    # Examples:
    # - Time-based: {"unit": "minute", "rate": 1.0}
    # - Token-based: {"unit": "token", "rate": 0.001}
    # - Analysis-based: {"unit": "analysis", "rate": 2.0}
    pricing_rule = Column(
        JSON,
        nullable=True,
        comment="Pricing configuration: {unit: 'minute'|'token'|'analysis', rate: float}",
    )

    # Credit tracking
    credits_consumed = Column(
        Numeric(10, 2),
        nullable=True,
        default=0,
        comment="Credits consumed (calculated, not deducted yet)",
    )
    credits_deducted = Column(
        Numeric(10, 2),
        nullable=False,
        default=0,
        comment="Credits actually deducted from counselor account",
    )
    credit_deducted = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether credits have been deducted",
    )
    credit_deducted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When credits were deducted",
    )

    # Incremental billing tracking (for ceiling rounding)
    last_billed_minutes = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Last billed minutes (for incremental billing with ceiling rounding)",
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_session_usages_counselor_status", "counselor_id", "status"),
    )
