"""
Session Analysis API - Deep analysis, quick feedback, and report generation
"""
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.core.exceptions import BadRequestError, InternalServerError, NotFoundError
from app.models.counselor import Counselor
from app.schemas.session import (
    ParentsReportReference,
    ParentsReportResponse,
    ProviderMetadata,
    QuickFeedbackResponse,
    RealtimeAnalyzeResponse,
)
from app.services.keyword_analysis_service import KeywordAnalysisService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions - Analysis"])


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
    mode: str = "practice",
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
        mode: "practice" (練習模式，無孩子在場) 或 "emergency" (實戰模式，有孩子在場)
    """
    from app.services.quick_feedback_service import quick_feedback_service

    instance = str(request.url.path)

    try:
        # Get session and verify authorization
        service = SessionService(db)
        result = service.get_session_with_details(session_id, current_user, tenant_id)
        if not result:
            raise NotFoundError(detail="Session not found", instance=instance)

        session, client, case, has_report = result

        # Extract recent (last 15s) and full transcript from recordings
        # This allows LLM to focus on recent content while having full context
        recordings = session.recordings or []
        recent_transcript, full_transcript = _extract_transcripts_by_time(
            recordings, seconds_ago=15
        )

        # Fallback to transcript_text if no recordings
        if not full_transcript:
            full_transcript = session.transcript_text or ""
        if not recent_transcript:
            recent_transcript = full_transcript  # Use full if no recent

        if not full_transcript:
            raise BadRequestError(
                detail="Session has no transcript",
                instance=instance,
            )

        logger.info(
            f"Quick feedback: recent={len(recent_transcript)} chars, "
            f"full={len(full_transcript)} chars"
        )

        # Call quick feedback service with both transcripts
        feedback_result = await quick_feedback_service.get_quick_feedback(
            recent_transcript=recent_transcript,
            full_transcript=full_transcript,
            tenant_id=tenant_id,
            mode=mode,
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
    mode: str = "practice",
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
    from app.services.keyword_analysis_service import KeywordAnalysisService

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
        # This allows LLM to focus on recent content while having full context
        recordings = session.recordings or []
        recent_transcript, full_transcript = _extract_transcripts_by_time(
            recordings, seconds_ago=60
        )

        # Fallback to transcript_text if no recordings
        if not full_transcript:
            full_transcript = session.transcript_text or ""
        if not recent_transcript:
            recent_transcript = full_transcript  # Use full if no recent

        if not full_transcript:
            raise BadRequestError(
                detail="Session has no transcript",
                instance=instance,
            )

        # Initialize keyword service
        keyword_service = KeywordAnalysisService(db)

        # Call SIMPLIFIED analysis with both transcripts
        logger.info(
            f"Deep analyze (simplified) session {session_id}: "
            f"tenant={tenant_id}, mode={mode}, "
            f"recent={len(recent_transcript)} chars, full={len(full_transcript)} chars"
        )

        analysis_result = await keyword_service.analyze_keywords_simplified(
            transcript_segment=recent_transcript,
            full_transcript=full_transcript,
            mode=mode,
            tenant_id=tenant_id,
        )

        # Extract results
        quick_suggestions = analysis_result.get("quick_suggestions", [])

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        provider_metadata = ProviderMetadata(
            provider="gemini", latency_ms=latency_ms, model="gemini-3-flash-preview"
        )

        logger.info(f"Deep analyze completed in {latency_ms}ms")

        return RealtimeAnalyzeResponse(
            safety_level=analysis_result.get("safety_level", "green"),
            summary=analysis_result.get("display_text", "分析完成"),
            alerts=[],
            suggestions=quick_suggestions,
            time_range="0:00-2:00",
            timestamp=datetime.now(timezone.utc).isoformat(),
            rag_sources=[],  # Simplified version doesn't use RAG
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
    from app.services.gemini_service import GeminiService
    from app.services.openai_service import OpenAIService
    from app.services.rag_retriever import RAGRetriever

    instance = str(request.url.path)
    start_time = time.time()

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

        # RAG: Retrieve relevant parenting theories
        rag_context = ""
        rag_sources = []  # List of document names for logging
        rag_references = []  # List of ParentsReportReference for response
        if use_rag:
            try:
                openai_service = OpenAIService()
                rag_retriever = RAGRetriever(openai_service)
                # Search for parenting-related theories
                rag_results = await rag_retriever.search(
                    query=transcript[:500],  # Use first 500 chars as query
                    top_k=5,
                    threshold=0.3,  # Lower threshold for better recall
                    db=db,
                    category="parenting",
                )
                if rag_results:
                    rag_context = "\n\n【參考理論】\n"
                    for i, theory in enumerate(rag_results, 1):
                        theory_text = theory.get("text", "")[:200]
                        theory_doc = theory.get("document", "")
                        theory_title = theory.get("title", theory_doc)
                        theory_category = theory.get("category", "教養理論")

                        rag_context += f"{i}. {theory_text}... (來源: {theory_doc})\n"
                        rag_sources.append(theory_doc)

                        # Build reference for response
                        rag_references.append(
                            ParentsReportReference(
                                title=theory_title,
                                content=theory_text,
                                source=theory_doc,
                                theory=theory_category,
                            )
                        )
                    logger.info(f"RAG found {len(rag_results)} theories for report")
            except Exception as e:
                # RAG failure should not block report generation
                logger.warning(f"RAG search failed (continuing without RAG): {e}")
                rag_context = ""

        # Build analysis prompt with optional RAG context
        rag_instruction = ""
        if rag_context:
            rag_instruction = """
【重要】請參考上述理論來支持你的分析和建議。在 analyze 和 suggestion 中可以引用相關理論。
"""

        analysis_prompt = f"""你是專業的親子溝通分析師，負責分析家長與孩子的對話，提供建設性的回饋。
{rag_context}{rag_instruction}
【對話逐字稿】
{transcript}

【分析要求】
請以中性、客觀、溫和的立場分析這次對話，提供以下 4 個部分：

1. **鼓勵標題**（encouragement）
   - 一句正向鼓勵的話，肯定家長願意溝通的心意
   - 例如：「這次你已經做了一件重要的事：願意好好跟孩子談。」
   - ≤ 40 字

2. **待解決的議題**（issue）
   - 指出這次對話中最需要改進的地方
   - 客觀描述，不批判
   - ≤ 50 字

3. **溝通內容分析**（analyze）
   - 分析為何這樣的溝通方式可能有問題
   - 解釋背後的心理或教養原理
   - ≤ 100 字

4. **建議下次可以這樣說**（suggestion）
   - 提供具體、可直接使用的替代說法
   - 用引號標示建議的話語
   - ≤ 80 字

【語氣要求】
- 溫和、同理、建設性
- 避免批判或讓家長感到被指責

【輸出格式】
請以 JSON 格式回應：

{{
  "encouragement": "正向鼓勵標題",
  "issue": "待解決的議題",
  "analyze": "溝通內容分析",
  "suggestion": "建議下次可以這樣說"
}}

請開始分析。"""

        # Call Gemini
        gemini_service = GeminiService()
        gemini_response = await gemini_service.chat_completion(
            prompt=analysis_prompt,
            temperature=0.7,
            return_metadata=True,
        )

        llm_raw_response = gemini_response["text"]

        # Parse response
        try:
            if "```json" in llm_raw_response:
                json_start = llm_raw_response.find("```json") + 7
                json_end = llm_raw_response.find("```", json_start)
                json_text = llm_raw_response[json_start:json_end].strip()
            elif "{" in llm_raw_response:
                json_start = llm_raw_response.find("{")
                json_end = llm_raw_response.rfind("}") + 1
                json_text = llm_raw_response[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")

            json_text = re.sub(r",(\s*[}\]])", r"\1", json_text)
            analysis = json.loads(json_text)

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse report response: {e}")
            raise InternalServerError(
                detail="Failed to parse AI response",
                instance=instance,
            )

        # Build response
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Report generated for session {session_id} in {latency_ms}ms")

        # Billing: Save analysis log and deduct credits
        try:
            keyword_service = KeywordAnalysisService(db)

            # Get token usage from Gemini response
            token_usage_data = {
                "prompt_tokens": gemini_response.get("prompt_tokens", 0),
                "completion_tokens": gemini_response.get("completion_tokens", 0),
                "total_tokens": gemini_response.get("total_tokens", 0),
                "estimated_cost_usd": gemini_response.get("estimated_cost_usd", 0),
            }

            # Build result data for logging
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
                    "token_usage": token_usage_data,
                    "llm_raw_response": llm_raw_response,
                },
            }

            # Save to session_analysis_logs and update billing
            keyword_service.save_analysis_log_and_usage(
                session_id=session_id,
                counselor_id=current_user.id,
                tenant_id=tenant_id,
                transcript_segment=transcript,
                result_data=result_data,
                rag_documents=[{"source": s} for s in rag_sources],
                rag_sources=rag_sources,
                token_usage_data=token_usage_data,
            )
            logger.info(f"Billing recorded for report session {session_id}")
        except Exception as e:
            # Billing failure should not block report response
            logger.error(f"Failed to record billing for report: {e}", exc_info=True)

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
    except Exception as e:
        logger.error(
            f"Report generation failed for session {session_id}: {e}", exc_info=True
        )
        _handle_generic_error(e, "generate report", instance)
