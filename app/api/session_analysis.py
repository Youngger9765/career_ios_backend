"""
Session Analysis API - Deep analysis, quick feedback, and report generation
"""
import json
import logging
import re
import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.core.exceptions import BadRequestError, InternalServerError, NotFoundError
from app.models.counselor import Counselor
from app.schemas.session import (
    ParentsReportResponse,
    ProviderMetadata,
    QuickFeedbackResponse,
    RAGSource,
    RealtimeAnalyzeResponse,
)
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions - Analysis"])


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

        # Get recordings from session
        recordings = session.recordings or []
        if not recordings:
            raise BadRequestError(
                detail="Session has no recordings",
                instance=instance,
            )

        # Get the LATEST recording as "recent transcript"
        # Sort by segment_number to ensure correct order
        sorted_recordings = sorted(recordings, key=lambda r: r.get("segment_number", 0))
        latest_recording = sorted_recordings[-1]
        recent_transcript = latest_recording.get("transcript_text", "")

        if not recent_transcript:
            raise BadRequestError(
                detail="Latest recording has no transcript",
                instance=instance,
            )

        # Call quick feedback service with mode (practice vs emergency)
        feedback_result = await quick_feedback_service.get_quick_feedback(
            recent_transcript=recent_transcript,
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
    深層分析逐字稿

    - 從 session 自動讀取逐字稿
    - 使用 KeywordAnalysisService 進行分析
    - 返回 safety_level, summary, suggestions
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

        # Get recordings from session
        recordings = session.recordings or []
        if not recordings:
            raise BadRequestError(
                detail="Session has no recordings",
                instance=instance,
            )

        # Sort recordings by segment_number
        sorted_recordings = sorted(recordings, key=lambda r: r.get("segment_number", 0))

        # Separate: current segment vs past context
        latest_recording = sorted_recordings[-1]
        previous_recordings = (
            sorted_recordings[:-1] if len(sorted_recordings) > 1 else []
        )

        # Current segment to analyze
        current_segment = latest_recording.get("transcript_text", "")
        if not current_segment:
            raise BadRequestError(
                detail="Latest recording has no transcript",
                instance=instance,
            )

        # Full transcript (all segments)
        full_transcript = session.transcript_text or current_segment

        # Context = previous segments (history for AI to understand conversation flow)
        context = "\n\n".join(
            [
                r.get("transcript_text", "")
                for r in previous_recordings
                if r.get("transcript_text")
            ]
        )

        # Initialize keyword service
        keyword_service = KeywordAnalysisService(db)

        # Call analysis service with proper separation
        logger.info(
            f"Deep analyze session {session_id}: tenant={tenant_id}, mode={mode}, use_rag={use_rag}"
        )
        logger.info(f"  - Current segment: {len(current_segment)} chars")
        logger.info(f"  - Context (history): {len(context)} chars")
        logger.info(f"  - Full transcript: {len(full_transcript)} chars")

        analysis_result = await keyword_service.analyze_keywords(
            session_id=str(session_id),
            transcript_segment=current_segment,  # ← 當前片段
            full_transcript=full_transcript,  # ← 完整逐字稿
            context=context,  # ← 過去的脈絡
            analysis_type=tenant_id,
            mode=mode,
            db=db,
            use_rag=use_rag,
        )

        # Extract results
        quick_suggestions = analysis_result.get("quick_suggestions", [])

        response_data = {
            "safety_level": analysis_result.get("safety_level", "green"),
            "summary": analysis_result.get("display_text", "分析完成"),
            "alerts": [],
            "suggestions": quick_suggestions,
        }

        # Add alerts from action_suggestion
        action_suggestion = analysis_result.get("action_suggestion", "")
        if action_suggestion:
            response_data["alerts"].append(action_suggestion)

        # Extract RAG sources
        rag_documents = analysis_result.get("rag_documents", [])
        rag_sources = [
            RAGSource(
                title=doc.get("title", ""),
                content=doc.get("content", "")[:300],
                score=round(float(doc.get("relevance_score", 0)), 2),
                theory="其他",
            )
            for doc in rag_documents
        ]

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        provider_metadata = ProviderMetadata(
            provider="gemini", latency_ms=latency_ms, model="gemini-3-flash-preview"
        )

        return RealtimeAnalyzeResponse(
            safety_level=response_data["safety_level"],
            summary=response_data["summary"],
            alerts=response_data["alerts"],
            suggestions=response_data["suggestions"],
            time_range="0:00-2:00",
            timestamp=datetime.now(timezone.utc).isoformat(),
            rag_sources=rag_sources,
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
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> ParentsReportResponse:
    """
    生成親子對話報告

    - 從 session 自動讀取逐字稿
    - 分析對話並提供：摘要、亮點、改進建議
    """
    from app.services.gemini_service import GeminiService

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

        # Build analysis prompt
        analysis_prompt = f"""你是專業的親子溝通分析師，負責分析家長與孩子的對話，提供建設性的回饋。

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

        return ParentsReportResponse(
            encouragement=analysis.get("encouragement", "感謝你願意花時間與孩子溝通。"),
            issue=analysis.get("issue", ""),
            analyze=analysis.get("analyze", ""),
            suggestion=analysis.get("suggestion", ""),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    except (NotFoundError, BadRequestError, InternalServerError):
        raise
    except Exception as e:
        logger.error(
            f"Report generation failed for session {session_id}: {e}", exc_info=True
        )
        _handle_generic_error(e, "generate report", instance)
