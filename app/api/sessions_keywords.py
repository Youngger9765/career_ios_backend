"""
Sessions Keyword Analysis API - Multi-tenant support

Endpoints:
- POST /{session_id}/analyze-partial - New multi-tenant analysis
- POST /{session_id}/analyze-keywords - Legacy backward-compatible endpoint
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Union
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.counselor import Counselor
from app.schemas.analysis import (
    AnalyzePartialRequest,
    CareerAnalysisResponse,
    IslandParentAnalysisResponse,
)
from app.schemas.session import KeywordAnalysisRequest, KeywordAnalysisResponse
from app.services.analysis.keyword_analysis_service import KeywordAnalysisService
from app.services.core.session_service import SessionService

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions - Keywords"])
logger = logging.getLogger(__name__)


def save_analysis_log_and_gbq(
    session_id: UUID,
    counselor_id: UUID,
    tenant_id: str,
    transcript_segment: str,
    result_data: Dict,
    db: DBSession,
) -> None:
    """
    Background task: Save SessionAnalysisLog to PostgreSQL and GBQ

    Note: Accepts db session as parameter to work with test dependency overrides.

    Args:
        session_id: Session UUID
        counselor_id: Counselor UUID
        tenant_id: Tenant identifier
        transcript_segment: Transcript segment
        result_data: Analysis results with _metadata
        db: Database session (injected from endpoint)
    """
    import asyncio

    from app.services.external.gbq_service import gbq_service

    try:
        # Extract metadata
        metadata = result_data.get("_metadata", {})
        rag_documents = result_data.get("rag_documents", [])
        rag_sources = metadata.get("rag_sources", [])

        # 1. Save to PostgreSQL
        keyword_service = KeywordAnalysisService(db)
        keyword_service.save_analysis_log_and_usage(
            session_id=session_id,
            counselor_id=counselor_id,
            tenant_id=tenant_id,
            transcript_segment=transcript_segment,
            result_data=result_data,
            rag_documents=rag_documents,
            rag_sources=rag_sources,
            token_usage_data={
                "prompt_tokens": metadata.get("prompt_tokens", 0),
                "completion_tokens": metadata.get("completion_tokens", 0),
                "total_tokens": metadata.get("total_tokens", 0),
                "estimated_cost_usd": metadata.get("estimated_cost_usd", 0),
            },
        )

        # 2. Write to GBQ (complete schema alignment with SessionAnalysisLog)
        analyzed_at = metadata.get("end_time") or datetime.now(timezone.utc)
        gbq_data = {
            # Core identifiers
            "id": metadata.get("request_id", str(uuid.uuid4())),
            "session_id": str(session_id),
            "tenant_id": tenant_id,
            "counselor_id": str(counselor_id),
            # Timestamps
            "analyzed_at": analyzed_at,
            "created_at": analyzed_at,
            "start_time": metadata.get("start_time"),
            "end_time": metadata.get("end_time"),
            # Request metadata
            "request_id": metadata.get("request_id", str(uuid.uuid4())),
            "mode": metadata.get("mode", "analyze_partial"),
            # Input data
            "transcript": transcript_segment,
            "time_range": metadata.get("time_range"),
            "speakers": metadata.get("speakers"),
            # Prompts
            "system_prompt": metadata.get("system_prompt"),
            "user_prompt": metadata.get("user_prompt"),
            "prompt_template": metadata.get("prompt_template"),
            # Analysis type and result
            "analysis_type": "partial_analysis",
            "safety_level": result_data.get("safety_level", "green"),
            "severity": str(result_data.get("severity"))
            if result_data.get("severity")
            else None,
            "display_text": result_data.get("display_text"),
            "action_suggestion": result_data.get("action_suggestion"),
            "analysis_result": result_data,
            "analysis_reasoning": metadata.get("analysis_reasoning"),
            "matched_suggestions": metadata.get("matched_suggestions", []),
            # RAG information
            "rag_used": metadata.get("rag_used", False),
            "rag_query": metadata.get("rag_query"),
            "rag_documents": rag_documents,
            "rag_sources": rag_sources,
            "rag_top_k": metadata.get("rag_top_k", 3),
            "rag_similarity_threshold": metadata.get("rag_similarity_threshold", 0.7),
            "rag_search_time_ms": metadata.get("rag_search_time_ms"),
            # Model information
            "provider": metadata.get("provider", "gemini"),
            "model_name": metadata.get("model_name", "gemini-3-flash-preview"),
            "model_version": metadata.get("model_version", "3.0"),
            # Timing breakdown
            "duration_ms": metadata.get("duration_ms"),
            "api_response_time_ms": metadata.get("api_response_time_ms"),
            "llm_call_time_ms": metadata.get("llm_call_time_ms"),
            # LLM response
            "llm_raw_response": metadata.get("llm_raw_response"),
            # Token usage
            "prompt_tokens": metadata.get("prompt_tokens", 0),
            "completion_tokens": metadata.get("completion_tokens", 0),
            "total_tokens": metadata.get("total_tokens", 0),
            "cached_tokens": metadata.get("cached_tokens", 0),
            "estimated_cost_usd": metadata.get("estimated_cost_usd", 0),
            # Cache info
            "use_cache": metadata.get("use_cache", False),
            "cache_hit": metadata.get("cache_hit"),
            "cache_key": metadata.get("cache_key"),
            "gemini_cache_ttl": metadata.get("gemini_cache_ttl"),
        }

        # Run async GBQ write in event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(gbq_service.write_analysis_log(gbq_data))
        logger.info(
            f"Background task completed: saved to PostgreSQL and GBQ for session {session_id}"
        )

    except Exception as e:
        logger.error(f"Background task failed: {e}", exc_info=True)
        # Don't close db session - it's managed by the endpoint/test


@router.post(
    "/{session_id}/analyze-partial",
    response_model=Union[CareerAnalysisResponse, IslandParentAnalysisResponse],
)
async def analyze_partial(
    session_id: UUID,
    request: AnalyzePartialRequest,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> Union[CareerAnalysisResponse, IslandParentAnalysisResponse]:
    """
    即時片段分析（Multi-Tenant）

    根據租戶（tenant_id）自動選擇：
    - RAG 知識庫（career 職涯 vs island_parents 親子教養）
    - Prompt template
    - Response 格式

    **Island Parents 租戶**：
    - 回傳紅黃綠燈安全等級
    - 建議下次分析間隔時間
    - 親子教養相關建議

    **Career 租戶**：
    - 回傳關鍵字、分類
    - 諮詢師洞察
    - 職涯相關建議

    **向後兼容**：舊的 /analyze-keywords 仍可用
    """
    # Get session with context
    service = SessionService(db)
    result = service.get_session_with_context(session_id, current_user, tenant_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session, client, case = result

    # Use KeywordAnalysisService for AI-powered analysis (non-blocking)
    keyword_service = KeywordAnalysisService(db)
    result_data = await keyword_service.analyze_partial(
        session,
        client,
        case,
        request.transcript_segment,
        current_user.id,
        tenant_id,
        mode=request.mode,
    )

    # Schedule background task: Save to PostgreSQL + GBQ
    background_tasks.add_task(
        save_analysis_log_and_gbq,
        session_id=session.id,
        counselor_id=current_user.id,
        tenant_id=tenant_id,
        transcript_segment=request.transcript_segment,
        result_data=result_data,
        db=db,
    )

    # Extract token usage from metadata
    metadata = result_data.get("_metadata", {})
    token_usage = metadata.get("token_usage")

    # Return tenant-specific response immediately (non-blocking)
    if tenant_id == "island_parents":
        return IslandParentAnalysisResponse(
            safety_level=result_data.get("safety_level", "green"),
            severity=result_data.get("severity", 1),
            display_text=result_data.get("display_text", "分析中"),
            action_suggestion=result_data.get("action_suggestion", "持續觀察"),
            suggested_interval_seconds=result_data.get(
                "suggested_interval_seconds", 15
            ),
            rag_documents=result_data.get("rag_documents", []),
            keywords=result_data.get("keywords", []),
            categories=result_data.get("categories", []),
            token_usage=token_usage,
            detailed_scripts=result_data.get("detailed_scripts"),
            theoretical_frameworks=result_data.get("theoretical_frameworks"),
        )
    else:  # career (default)
        return CareerAnalysisResponse(
            keywords=result_data.get("keywords", ["分析中"])[:10],
            categories=result_data.get("categories", ["一般"])[:5],
            confidence=result_data.get("confidence", 0.5),
            counselor_insights=result_data.get("counselor_insights", "持續觀察")[:200],
            safety_level=result_data.get("safety_level"),
            severity=result_data.get("severity"),
            display_text=result_data.get("display_text"),
            action_suggestion=result_data.get("action_suggestion"),
            rag_documents=result_data.get("rag_documents"),
            token_usage=token_usage,
        )


@router.post("/{session_id}/analyze-keywords", response_model=KeywordAnalysisResponse)
async def analyze_session_keywords(
    session_id: UUID,
    request: KeywordAnalysisRequest,
    db: DBSession = Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> KeywordAnalysisResponse:
    """
    舊版關鍵字分析 API（向後兼容）

    Legacy backward-compatible endpoint for keyword analysis.
    Internally calls analyze_partial and returns career format (keywords only).

    **建議**：新開發請使用 /analyze-partial 以支援多租戶格式

    **向後兼容行為**：
    - 內部調用 analyze_partial
    - 固定回傳 career 格式（關鍵字 + 類別 + 信心分數 + 洞察）
    - 不含 island_parents 特有的紅黃綠燈評估
    """
    # Get session with context
    service = SessionService(db)
    result = service.get_session_with_context(session_id, current_user, tenant_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session, client, case = result

    # Use new analyze_partial internally
    keyword_service = KeywordAnalysisService(db)
    result_data = await keyword_service.analyze_partial(
        session,
        client,
        case,
        request.transcript_segment,
        current_user.id,
        tenant_id,
    )

    # Save to SessionAnalysisLog (for backward compatibility)
    from datetime import datetime, timezone

    from app.models.session_analysis_log import SessionAnalysisLog

    log = SessionAnalysisLog(
        session_id=session_id,
        counselor_id=current_user.id,
        tenant_id=tenant_id,
        analysis_type="keyword_analysis",
        transcript=request.transcript_segment,
        analysis_result=result_data,
        safety_level="safe",  # Default for career tenant
        risk_indicators=[],
        rag_documents=result_data.get("rag_documents", []),
        rag_sources=result_data.get("rag_sources", []),
        token_usage=result_data.get("token_usage", {}),
        analyzed_at=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()

    # Return legacy format (backward compatible)
    return KeywordAnalysisResponse(
        keywords=result_data.get("keywords", ["分析中"])[:10],
        categories=result_data.get("categories", ["一般"])[:5],
        confidence=result_data.get("confidence", 0.5),
        counselor_insights=result_data.get(
            "counselor_insights", "請根據逐字稿內容判斷。"
        )[:200],
    )
