"""
SessionAnalysisLog Model - Detailed analysis event tracking
Individual analysis records with RAG data, safety metrics, and token usage
"""
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.base import GUID, BaseModel


class SessionAnalysisLog(Base, BaseModel):
    """
    Store individual analysis records for sessions.
    Tracks analysis type, results, safety levels, RAG documents, and token metrics.
    BigQuery-compatible field types.
    """

    __tablename__ = "session_analysis_logs"

    # Core identifiers
    session_id = Column(
        GUID(),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Session being analyzed",
    )
    counselor_id = Column(
        GUID(),
        ForeignKey("counselors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Counselor who performed the analysis",
    )
    tenant_id = Column(
        String,
        nullable=False,
        index=True,
        comment="Tenant ID for multi-tenancy isolation",
    )

    # Analysis metadata
    analysis_type = Column(
        String(100),
        nullable=False,
        comment="Type of analysis: keyword_extraction, summarization, rag_query, etc.",
    )
    transcript = Column(
        Text,
        nullable=True,
        comment="Transcript analyzed",
    )
    analysis_result = Column(
        JSON,
        nullable=True,
        default=dict,
        comment="Analysis results (keywords, categories, answer, etc.)",
    )

    # Safety and risk assessment
    safety_level = Column(
        String(20),
        nullable=True,
        index=True,
        comment="Safety level: green, yellow, red",
    )
    severity = Column(
        String(20),
        nullable=True,
        comment="Severity level if applicable",
    )
    display_text = Column(
        Text,
        nullable=True,
        comment="Display text for UI",
    )
    action_suggestion = Column(
        Text,
        nullable=True,
        comment="Suggested actions based on analysis",
    )
    risk_indicators = Column(
        JSON,
        nullable=True,
        default=list,
        comment="List of risk indicators identified",
    )

    # RAG information (JSON fields supported in BigQuery since 2022)
    rag_documents = Column(
        JSON,
        nullable=True,
        default=list,
        comment="RAG documents used: [{'doc_id': ..., 'relevance': ..., 'title': ..., 'chunk_id': ...}]",
    )
    rag_sources = Column(
        JSON,
        nullable=True,
        default=list,
        comment="List of RAG source references",
    )

    # Technical metrics
    transcript_length = Column(
        Integer,
        nullable=True,
        comment="Length of transcript analyzed (characters)",
    )
    duration_seconds = Column(
        Integer,
        nullable=True,
        comment="Duration if time-based analysis",
    )
    model_name = Column(
        String(100),
        nullable=True,
        comment="AI model name used for analysis",
    )

    # Token usage (stored as JSON for flexibility)
    token_usage = Column(
        JSON,
        nullable=True,
        default=dict,
        comment="Token usage: {prompt_tokens, completion_tokens, total_tokens, model}",
    )

    # Individual token fields for easier querying
    prompt_tokens = Column(
        Integer,
        nullable=True,
        comment="Prompt tokens used",
    )
    completion_tokens = Column(
        Integer,
        nullable=True,
        comment="Completion tokens used",
    )
    total_tokens = Column(
        Integer,
        nullable=True,
        comment="Total tokens used",
    )
    cached_tokens = Column(
        Integer,
        nullable=True,
        comment="Cached tokens (if applicable)",
    )

    # Cost tracking
    estimated_cost_usd = Column(
        Numeric(10, 6),
        nullable=True,
        comment="Estimated cost in USD",
    )

    # Request metadata
    request_id = Column(
        String,
        nullable=True,
        comment="Request ID for tracing",
    )
    mode = Column(
        String(50),
        nullable=True,
        comment="Analysis mode: emergency, practice, analyze_partial",
    )

    # Input data
    time_range = Column(
        String,
        nullable=True,
        comment="Time range analyzed (e.g., '0-60s')",
    )
    speakers = Column(
        JSON,
        nullable=True,
        comment="Speaker segments (for realtime)",
    )

    # Prompts
    system_prompt = Column(
        Text,
        nullable=True,
        comment="System prompt used",
    )
    user_prompt = Column(
        Text,
        nullable=True,
        comment="User prompt used",
    )
    prompt_template = Column(
        String(100),
        nullable=True,
        comment="Prompt template version",
    )

    # RAG metadata (extended)
    rag_used = Column(
        Boolean,
        nullable=True,
        comment="Whether RAG was used",
    )
    rag_query = Column(
        Text,
        nullable=True,
        comment="Query used for RAG search",
    )
    rag_top_k = Column(
        Integer,
        nullable=True,
        comment="RAG top-k parameter",
    )
    rag_similarity_threshold = Column(
        Float,
        nullable=True,
        comment="RAG similarity threshold",
    )
    rag_search_time_ms = Column(
        Integer,
        nullable=True,
        comment="RAG search time in milliseconds",
    )

    # Model metadata (extended)
    provider = Column(
        String(50),
        nullable=True,
        comment="LLM provider: gemini, openai",
    )
    model_version = Column(
        String(50),
        nullable=True,
        comment="Model version",
    )

    # Timing breakdown
    start_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Analysis start time",
    )
    end_time = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Analysis end time",
    )
    duration_ms = Column(
        Integer,
        nullable=True,
        comment="Total duration in milliseconds",
    )
    api_response_time_ms = Column(
        Integer,
        nullable=True,
        comment="API response time in milliseconds",
    )
    llm_call_time_ms = Column(
        Integer,
        nullable=True,
        comment="LLM call time in milliseconds",
    )

    # LLM response
    llm_raw_response = Column(
        Text,
        nullable=True,
        comment="Raw LLM response text",
    )
    analysis_reasoning = Column(
        Text,
        nullable=True,
        comment="Analysis reasoning (if provided)",
    )
    matched_suggestions = Column(
        JSON,
        nullable=True,
        comment="Matched suggestions from expert pool",
    )

    # Cache metadata
    use_cache = Column(
        Boolean,
        nullable=True,
        comment="Whether cache was used",
    )
    cache_hit = Column(
        Boolean,
        nullable=True,
        comment="Whether cache hit occurred",
    )
    cache_key = Column(
        String,
        nullable=True,
        comment="Cache key used",
    )
    gemini_cache_ttl = Column(
        Integer,
        nullable=True,
        comment="Gemini cache TTL in seconds",
    )

    # Timestamp
    analyzed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="When the analysis was performed",
    )

    # Composite index for common query patterns
    __table_args__ = (
        Index(
            "ix_session_analysis_logs_session_safety",
            "session_id",
            "safety_level",
        ),
    )
