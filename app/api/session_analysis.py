"""
Session Analysis API - Deep analysis, quick feedback, and report generation

Refactored to use specialized services for better modularity.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.core.exceptions import BadRequestError, InternalServerError, NotFoundError
from app.models.counselor import Counselor
from app.schemas.session import (
    ParentsReportResponse,
    ProviderMetadata,
    QuickFeedbackResponse,
    RealtimeAnalyzeResponse,
)
from app.services.analysis.keyword_analysis_service import KeywordAnalysisService
from app.services.core.session_service import SessionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions - Analysis"])


def _log_analysis_background(
    session_id: UUID,
    counselor_id: UUID,
    tenant_id: str,
    transcript_segment: str,
    result_data: dict,
    token_usage_data: dict,
    analysis_type: str,
):
    """Background task to log analysis to SessionAnalysisLog (runs AFTER response)"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        keyword_service = KeywordAnalysisService(db)
        keyword_service.save_analysis_log_and_usage(
            session_id=session_id,
            counselor_id=counselor_id,
            tenant_id=tenant_id,
            transcript_segment=transcript_segment,
            result_data=result_data,
            rag_documents=[],
            rag_sources=[],
            token_usage_data=token_usage_data,
        )
        logger.info(f"{analysis_type} logged for session {session_id} (background)")
    except Exception as e:
        logger.error(f"Failed to log {analysis_type} (background): {e}", exc_info=True)
    finally:
        db.close()


def _extract_transcripts_by_time(
    recordings: List[dict], seconds_ago: int
) -> Tuple[str, str]:
    """
    Extract recent transcript and full transcript from recordings.

    Args:
        recordings: List of recording segments with start_time, end_time, transcript_text
        seconds_ago: How many seconds back to consider as "recent" (e.g., 15 for Quick, 60 for Deep)

    Returns:
        Tuple of (recent_transcript, full_transcript)
        - recent_transcript: Segments from the last N seconds
        - full_transcript: All segments combined
    """
    if not recordings:
        return "", ""

    # Sort by segment_number
    sorted_recordings = sorted(recordings, key=lambda r: r.get("segment_number", 0))

    # Build full transcript
    full_parts = []
    for r in sorted_recordings:
        text = r.get("transcript_text", "")
        if text:
            full_parts.append(text)
    full_transcript = "\n".join(full_parts)

    # Calculate cutoff time
    now = datetime.now(timezone.utc)
    cutoff_time = now - timedelta(seconds=seconds_ago)

    # Extract recent segments (end_time >= cutoff_time)
    recent_parts = []
    for r in sorted_recordings:
        end_time_str = r.get("end_time")
        if not end_time_str:
            continue

        try:
            # Parse end_time (ISO 8601 format)
            if isinstance(end_time_str, str):
                end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
            elif isinstance(end_time_str, datetime):
                end_time = end_time_str
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
            else:
                continue

            # Check if this segment is recent
            if end_time >= cutoff_time:
                text = r.get("transcript_text", "")
                if text:
                    recent_parts.append(text)
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse end_time '{end_time_str}': {e}")
            continue

    recent_transcript = "\n".join(recent_parts) if recent_parts else ""

    # Fallback: if no recent segments found, use the last segment
    if not recent_transcript and sorted_recordings:
        last_segment = sorted_recordings[-1]
        recent_transcript = last_segment.get("transcript_text", "")

    return recent_transcript, full_transcript


def _handle_generic_error(e: Exception, operation: str, instance: str):
    raise InternalServerError(
        detail=f"Failed to {operation}: {str(e)}",
        instance=instance,
    )


@router.post("/{session_id}/quick-feedback", response_model=QuickFeedbackResponse)
async def session_quick_feedback(
    session_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session_mode: str = "practice",
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> QuickFeedbackResponse:
    """
    快速反饋（輕量級，~8秒）

    - 從 session 自動讀取逐字稿
    - 使用 QuickFeedbackService 生成簡短鼓勵訊息
    - 返回 1 句話（50字內）

    Args:
        session_mode: "practice" (練習模式，無孩子在場) 或 "emergency" (對談模式，有孩子在場)
    """
    from app.services.core.quick_feedback_service import quick_feedback_service

    instance = str(request.url.path)

    try:
        # Get session and verify authorization
        service = SessionService(db)
        result = service.get_session_with_details(session_id, current_user, tenant_id)
        if not result:
            raise NotFoundError(detail="Session not found", instance=instance)

        session, client, case, has_report = result

        # Extract recent (last 15s) and full transcript from recordings
        recordings = session.recordings or []
        recent_transcript, full_transcript = _extract_transcripts_by_time(
            recordings, seconds_ago=15
        )

        # Fallback to transcript_text if no recordings
        if not full_transcript:
            full_transcript = session.transcript_text or ""
        if not recent_transcript:
            recent_transcript = full_transcript

        if not full_transcript:
            raise BadRequestError(
                detail="Session has no transcript",
                instance=instance,
            )

        logger.info(
            f"Quick feedback: recent={len(recent_transcript)} chars, "
            f"full={len(full_transcript)} chars"
        )

        # Build scenario context for analysis
        scenario_context = ""
        if session.scenario or session.scenario_description:
            scenario_context = f"【家長煩惱情境】{session.scenario or ''}"
            if session.scenario_description:
                scenario_context += f"\n{session.scenario_description}"

        # Call quick feedback service
        feedback_result = await quick_feedback_service.get_quick_feedback(
            recent_transcript=recent_transcript,
            full_transcript=full_transcript,
            tenant_id=tenant_id,
            mode=session_mode,
            scenario_context=scenario_context,
        )

        # Schedule logging as background task
        result_data = {
            "analysis_type": "quick_feedback",
            "message": feedback_result["message"],
            "type": feedback_result["type"],
            "_metadata": {
                "session_mode": session_mode,
                "latency_ms": feedback_result["latency_ms"],
                "recent_transcript_length": len(recent_transcript),
                "full_transcript_length": len(full_transcript),
                "scenario": session.scenario,
            },
        }
        prompt_tokens = feedback_result.get("prompt_tokens", 0)
        completion_tokens = feedback_result.get("completion_tokens", 0)
        total_tokens = feedback_result.get(
            "total_tokens", prompt_tokens + completion_tokens
        )
        token_usage_data = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": total_tokens * 0.000001,
        }
        background_tasks.add_task(
            _log_analysis_background,
            session_id=session_id,
            counselor_id=current_user.id,
            tenant_id=tenant_id,
            transcript_segment=recent_transcript[:500],
            result_data=result_data,
            token_usage_data=token_usage_data,
            analysis_type="quick_feedback",
        )

        return QuickFeedbackResponse(
            message=feedback_result["message"],
            type=feedback_result["type"],
            timestamp=feedback_result["timestamp"],
            latency_ms=feedback_result["latency_ms"],
        )

    except (NotFoundError, BadRequestError):
        raise
    except Exception as e:
        logger.error(f"Quick feedback failed for session {session_id}: {e}")
        return QuickFeedbackResponse(
            message="繼續保持，你做得很好",
            type="fallback_error",
            timestamp=datetime.now().isoformat(),
            latency_ms=0,
        )


@router.post("/{session_id}/deep-analyze", response_model=RealtimeAnalyzeResponse)
async def session_deep_analyze(
    session_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    session_mode: str = "practice",
    use_rag: bool = False,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> RealtimeAnalyzeResponse:
    """
    深層分析逐字稿（優化版 - 單次 Gemini 呼叫）

    - 從 session 自動讀取逐字稿
    - 使用 KeywordAnalysisService.analyze_keywords_simplified() 進行分析
    - 返回 safety_level, summary, suggestions
    - 比原版快 ~50%（1 次呼叫 vs 2 次呼叫）
    """
    instance = str(request.url.path)
    start_time = time.time()

    try:
        # Get session and verify authorization
        service = SessionService(db)
        result = service.get_session_with_details(session_id, current_user, tenant_id)
        if not result:
            raise NotFoundError(detail="Session not found", instance=instance)

        session, client, case, has_report = result

        # Extract recent (last 60s) and full transcript from recordings
        recordings = session.recordings or []
        recent_transcript, full_transcript = _extract_transcripts_by_time(
            recordings, seconds_ago=60
        )

        # Fallback to transcript_text if no recordings
        if not full_transcript:
            full_transcript = session.transcript_text or ""
        if not recent_transcript:
            recent_transcript = full_transcript

        if not full_transcript:
            raise BadRequestError(
                detail="Session has no transcript",
                instance=instance,
            )

        # Initialize keyword service
        keyword_service = KeywordAnalysisService(db)

        # Build scenario context for analysis
        scenario_context = ""
        if session.scenario or session.scenario_description:
            scenario_context = f"【家長煩惱情境】{session.scenario or ''}"
            if session.scenario_description:
                scenario_context += f"\n{session.scenario_description}"

        # Call SIMPLIFIED analysis
        logger.info(
            f"Deep analyze (simplified) session {session_id}: "
            f"tenant={tenant_id}, session_mode={session_mode}, "
            f"recent={len(recent_transcript)} chars, full={len(full_transcript)} chars, "
            f"scenario={bool(scenario_context)}"
        )

        analysis_result = await keyword_service.analyze_keywords_simplified(
            transcript_segment=recent_transcript,
            full_transcript=full_transcript,
            mode=session_mode,
            tenant_id=tenant_id,
            scenario_context=scenario_context,
        )

        # Extract results
        quick_suggestions = analysis_result.get("quick_suggestions", [])

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        provider_metadata = ProviderMetadata(
            provider="gemini", latency_ms=latency_ms, model="gemini-3-flash-preview"
        )

        logger.info(f"Deep analyze completed in {latency_ms}ms")

        # Schedule logging as background task
        result_data = {
            "analysis_type": "deep_analyze",
            "safety_level": analysis_result.get("safety_level", "green"),
            "display_text": analysis_result.get("display_text", ""),
            "quick_suggestions": quick_suggestions,
            "_metadata": {
                "session_mode": session_mode,
                "use_rag": use_rag,
                "latency_ms": latency_ms,
                "recent_transcript_length": len(recent_transcript),
                "full_transcript_length": len(full_transcript),
                "scenario": session.scenario,
            },
        }
        prompt_tokens = analysis_result.get("prompt_tokens", 0)
        completion_tokens = analysis_result.get("completion_tokens", 0)
        total_tokens = analysis_result.get(
            "total_tokens", prompt_tokens + completion_tokens
        )
        token_usage_data = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": total_tokens * 0.000001,
        }
        background_tasks.add_task(
            _log_analysis_background,
            session_id=session_id,
            counselor_id=current_user.id,
            tenant_id=tenant_id,
            transcript_segment=recent_transcript[:1000],
            result_data=result_data,
            token_usage_data=token_usage_data,
            analysis_type="deep_analyze",
        )

        return RealtimeAnalyzeResponse(
            safety_level=analysis_result.get("safety_level", "green"),
            summary=analysis_result.get("display_text", "分析完成"),
            alerts=[],
            suggestions=quick_suggestions,
            time_range="0:00-2:00",
            timestamp=datetime.now(timezone.utc).isoformat(),
            rag_sources=[],
            cache_metadata=None,
            provider_metadata=provider_metadata,
        )

    except (NotFoundError, BadRequestError):
        raise
    except Exception as e:
        logger.error(
            f"Deep analyze failed for session {session_id}: {e}", exc_info=True
        )
        _handle_generic_error(e, "deep analyze session", instance)


@router.post("/{session_id}/report", response_model=ParentsReportResponse)
async def session_report(
    session_id: UUID,
    request: Request,
    use_rag: bool = True,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> ParentsReportResponse:
    """
    生成親子對話報告

    - 從 session 自動讀取逐字稿
    - 分析對話並提供：摘要、亮點、改進建議
    - use_rag=True 時會檢索相關教養理論作為參考
    """
    from app.services.analysis.parents_report_service import ParentsReportService

    instance = str(request.url.path)

    try:
        # Get session and verify authorization
        service = SessionService(db)
        result = service.get_session_with_details(session_id, current_user, tenant_id)
        if not result:
            raise NotFoundError(detail="Session not found", instance=instance)

        session, client, case, has_report = result

        # Get transcript from session
        transcript = session.transcript_text or ""
        if not transcript:
            raise BadRequestError(
                detail="Session has no transcript",
                instance=instance,
            )

        # Use ParentsReportService to generate report
        report_service = ParentsReportService(db)
        (
            analysis,
            rag_references,
            rag_sources,
            latency_ms,
            token_usage,
        ) = await report_service.generate_report(
            session=session,
            transcript=transcript,
            use_rag=use_rag,
        )

        logger.info(f"Report generated for session {session_id} in {latency_ms}ms")

        # Billing: Save analysis log and deduct credits
        try:
            keyword_service = KeywordAnalysisService(db)
            result_data = {
                "analysis_type": "report",
                "encouragement": analysis.get("encouragement", ""),
                "issue": analysis.get("issue", ""),
                "analyze": analysis.get("analyze", ""),
                "suggestion": analysis.get("suggestion", ""),
                "rag_sources": rag_sources,
                "_metadata": {
                    "duration_ms": latency_ms,
                    "use_rag": use_rag,
                    "rag_documents_count": len(rag_sources),
                    "transcript_length": len(transcript),
                    "token_usage": token_usage,
                    "llm_raw_response": token_usage.get("llm_raw_response", ""),
                },
            }
            keyword_service.save_analysis_log_and_usage(
                session_id=session_id,
                counselor_id=current_user.id,
                tenant_id=tenant_id,
                transcript_segment=transcript,
                result_data=result_data,
                rag_documents=[{"source": s} for s in rag_sources],
                rag_sources=rag_sources,
                token_usage_data=token_usage,
            )
            logger.info(f"Billing recorded for report session {session_id}")
        except Exception as e:
            logger.error(f"Failed to record billing for report: {e}", exc_info=True)

        # Save Report record
        report_service.save_report_record(
            session_id=session_id,
            client_id=client.id,
            counselor_id=current_user.id,
            tenant_id=tenant_id,
            analysis=analysis,
            rag_references=rag_references,
            token_usage=token_usage,
        )

        return ParentsReportResponse(
            encouragement=analysis.get("encouragement", "感謝你願意花時間與孩子溝通。"),
            issue=analysis.get("issue", ""),
            analyze=analysis.get("analyze", ""),
            suggestion=analysis.get("suggestion", ""),
            references=rag_references,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except (NotFoundError, BadRequestError, InternalServerError):
        raise
    except ValueError as e:
        # Parse errors from report service
        raise InternalServerError(
            detail=str(e),
            instance=instance,
        )
    except Exception as e:
        logger.error(
            f"Report generation failed for session {session_id}: {e}", exc_info=True
        )
        _handle_generic_error(e, "generate report", instance)
