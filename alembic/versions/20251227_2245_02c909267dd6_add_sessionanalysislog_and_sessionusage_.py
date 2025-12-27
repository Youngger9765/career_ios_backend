"""Add SessionAnalysisLog and SessionUsage with complete GBQ fields

Revision ID: 02c909267dd6
Revises: f9b8a56ce021
Create Date: 2025-12-27 22:45:18.805748

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "02c909267dd6"
down_revision: Union[str, None] = "f9b8a56ce021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create session_analysis_logs table with all GBQ-aligned fields
    op.create_table(
        "session_analysis_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Core identifiers
        sa.Column(
            "session_id", sa.UUID(), nullable=False, comment="Session being analyzed"
        ),
        sa.Column(
            "counselor_id",
            sa.UUID(),
            nullable=False,
            comment="Counselor who performed the analysis",
        ),
        sa.Column(
            "tenant_id",
            sa.String(),
            nullable=False,
            comment="Tenant ID for multi-tenancy isolation",
        ),
        # Analysis metadata
        sa.Column(
            "analysis_type",
            sa.String(length=100),
            nullable=False,
            comment="Type of analysis",
        ),
        sa.Column(
            "transcript", sa.Text(), nullable=True, comment="Transcript analyzed"
        ),
        sa.Column(
            "analysis_result",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Analysis results",
        ),
        # Safety and risk assessment
        sa.Column(
            "safety_level",
            sa.String(length=20),
            nullable=True,
            comment="Safety level: green, yellow, red",
        ),
        sa.Column(
            "severity", sa.Integer(), nullable=True, comment="Severity level 1-3"
        ),
        sa.Column(
            "display_text", sa.Text(), nullable=True, comment="Display text for client"
        ),
        sa.Column(
            "action_suggestion", sa.Text(), nullable=True, comment="Suggested action"
        ),
        sa.Column(
            "risk_indicators",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Risk indicators",
        ),
        # RAG information
        sa.Column(
            "rag_documents",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="RAG documents used",
        ),
        sa.Column(
            "rag_sources",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="RAG source references",
        ),
        # Technical metrics
        sa.Column(
            "transcript_length",
            sa.Integer(),
            nullable=True,
            comment="Transcript length in characters",
        ),
        sa.Column(
            "duration_seconds",
            sa.Integer(),
            nullable=True,
            comment="Analysis duration in seconds",
        ),
        sa.Column(
            "model_name", sa.String(length=100), nullable=True, comment="AI model name"
        ),
        # Token usage
        sa.Column(
            "token_usage",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Token usage details",
        ),
        sa.Column(
            "prompt_tokens", sa.Integer(), nullable=True, comment="Prompt tokens used"
        ),
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=True,
            comment="Completion tokens used",
        ),
        sa.Column(
            "total_tokens", sa.Integer(), nullable=True, comment="Total tokens used"
        ),
        sa.Column(
            "cached_tokens", sa.Integer(), nullable=True, comment="Cached tokens used"
        ),
        # Cost
        sa.Column(
            "estimated_cost_usd",
            sa.Numeric(precision=10, scale=6),
            nullable=True,
            comment="Estimated cost in USD",
        ),
        # GBQ alignment fields
        sa.Column(
            "request_id", sa.String(), nullable=True, comment="Request ID for tracing"
        ),
        sa.Column(
            "mode",
            sa.String(length=50),
            nullable=True,
            comment="Analysis mode: emergency, practice, analyze_partial",
        ),
        sa.Column(
            "time_range", sa.String(), nullable=True, comment="Time range analyzed"
        ),
        sa.Column(
            "speakers",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Speaker segments",
        ),
        sa.Column(
            "system_prompt", sa.Text(), nullable=True, comment="System prompt used"
        ),
        sa.Column("user_prompt", sa.Text(), nullable=True, comment="User prompt used"),
        sa.Column(
            "prompt_template",
            sa.String(length=100),
            nullable=True,
            comment="Prompt template version",
        ),
        sa.Column(
            "rag_used", sa.Boolean(), nullable=True, comment="Whether RAG was used"
        ),
        sa.Column(
            "rag_query", sa.Text(), nullable=True, comment="Query used for RAG search"
        ),
        sa.Column(
            "rag_top_k", sa.Integer(), nullable=True, comment="RAG top-k parameter"
        ),
        sa.Column(
            "rag_similarity_threshold",
            sa.Float(),
            nullable=True,
            comment="RAG similarity threshold",
        ),
        sa.Column(
            "rag_search_time_ms",
            sa.Integer(),
            nullable=True,
            comment="RAG search time in milliseconds",
        ),
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=True,
            comment="LLM provider: gemini, openai, codeer",
        ),
        sa.Column(
            "model_version",
            sa.String(length=50),
            nullable=True,
            comment="Model version",
        ),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=True,
            comment="Total duration in milliseconds",
        ),
        sa.Column("api_response_time_ms", sa.Integer(), nullable=True),
        sa.Column("llm_call_time_ms", sa.Integer(), nullable=True),
        sa.Column(
            "llm_raw_response",
            sa.Text(),
            nullable=True,
            comment="Raw LLM response text",
        ),
        sa.Column("analysis_reasoning", sa.Text(), nullable=True),
        sa.Column(
            "matched_suggestions", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("use_cache", sa.Boolean(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=True),
        sa.Column("cache_key", sa.String(), nullable=True),
        sa.Column("gemini_cache_ttl", sa.Integer(), nullable=True),
        # Timestamps
        sa.Column(
            "analyzed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["counselor_id"], ["counselors.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        "ix_session_analysis_logs_counselor_id",
        "session_analysis_logs",
        ["counselor_id"],
    )
    op.create_index(
        "ix_session_analysis_logs_session_id", "session_analysis_logs", ["session_id"]
    )
    op.create_index(
        "ix_session_analysis_logs_tenant_id", "session_analysis_logs", ["tenant_id"]
    )
    op.create_index(
        "ix_session_analysis_logs_safety_level",
        "session_analysis_logs",
        ["safety_level"],
    )
    op.create_index(
        "ix_session_analysis_logs_analyzed_at", "session_analysis_logs", ["analyzed_at"]
    )

    # Create session_usages table
    op.create_table(
        "session_usages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        # Core identifiers
        sa.Column(
            "session_id",
            sa.UUID(),
            nullable=False,
            comment="Session being tracked (one-to-one relationship)",
        ),
        sa.Column(
            "counselor_id",
            sa.UUID(),
            nullable=False,
            comment="Counselor who owns this session",
        ),
        sa.Column(
            "tenant_id",
            sa.String(),
            nullable=False,
            comment="Tenant ID for multi-tenancy isolation",
        ),
        # Usage metadata
        sa.Column(
            "usage_type",
            sa.String(length=50),
            nullable=True,
            comment="Type: voice_call, text_analysis, keyword_analysis, etc.",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="in_progress",
            comment="Status: in_progress, completed, failed",
        ),
        # Time tracking
        sa.Column(
            "start_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When usage started",
        ),
        sa.Column(
            "end_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When usage ended",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Alternative started timestamp",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When status changed to completed",
        ),
        # Raw metrics
        sa.Column(
            "duration_seconds",
            sa.Integer(),
            nullable=True,
            comment="Duration in seconds",
        ),
        sa.Column(
            "analysis_count",
            sa.Integer(),
            nullable=True,
            comment="Number of analyses performed",
        ),
        # Token metrics
        sa.Column(
            "total_prompt_tokens",
            sa.Integer(),
            nullable=True,
            comment="Total prompt tokens",
        ),
        sa.Column(
            "total_completion_tokens",
            sa.Integer(),
            nullable=True,
            comment="Total completion tokens",
        ),
        sa.Column("total_tokens", sa.Integer(), nullable=True, comment="Total tokens"),
        sa.Column(
            "total_cached_tokens",
            sa.Integer(),
            nullable=True,
            comment="Total cached tokens",
        ),
        sa.Column(
            "token_usage",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Detailed token usage",
        ),
        # Cost
        sa.Column(
            "estimated_cost_usd",
            sa.Numeric(precision=10, scale=6),
            nullable=True,
            comment="Estimated cost in USD",
        ),
        # Flexible pricing
        sa.Column(
            "pricing_rule",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="Pricing configuration",
        ),
        # Credit tracking
        sa.Column(
            "credits_consumed",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
            comment="Credits consumed",
        ),
        sa.Column(
            "credits_deducted",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
            comment="Credits actually deducted",
        ),
        sa.Column(
            "credit_deducted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether credits have been deducted",
        ),
        sa.Column(
            "credit_deducted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When credits were deducted",
        ),
        # Incremental billing tracking
        sa.Column(
            "last_billed_minutes",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Last billed minutes (for incremental billing with ceiling rounding)",
        ),
        sa.ForeignKeyConstraint(
            ["counselor_id"], ["counselors.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_session_usages_session_id"),
    )

    # Create indexes
    op.create_index(
        "ix_session_usages_counselor_id", "session_usages", ["counselor_id"]
    )
    op.create_index("ix_session_usages_session_id", "session_usages", ["session_id"])
    op.create_index("ix_session_usages_tenant_id", "session_usages", ["tenant_id"])
    op.create_index("ix_session_usages_status", "session_usages", ["status"])
    op.create_index(
        "ix_session_usages_counselor_status",
        "session_usages",
        ["counselor_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_session_usages_counselor_status", table_name="session_usages")
    op.drop_index("ix_session_usages_status", table_name="session_usages")
    op.drop_index("ix_session_usages_tenant_id", table_name="session_usages")
    op.drop_index("ix_session_usages_session_id", table_name="session_usages")
    op.drop_index("ix_session_usages_counselor_id", table_name="session_usages")
    op.drop_table("session_usages")

    op.drop_index(
        "ix_session_analysis_logs_analyzed_at", table_name="session_analysis_logs"
    )
    op.drop_index(
        "ix_session_analysis_logs_safety_level", table_name="session_analysis_logs"
    )
    op.drop_index(
        "ix_session_analysis_logs_tenant_id", table_name="session_analysis_logs"
    )
    op.drop_index(
        "ix_session_analysis_logs_session_id", table_name="session_analysis_logs"
    )
    op.drop_index(
        "ix_session_analysis_logs_counselor_id", table_name="session_analysis_logs"
    )
    op.drop_table("session_analysis_logs")
