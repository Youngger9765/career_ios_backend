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

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.core.exceptions import BadRequestError, InternalServerError, NotFoundError
from app.models.counselor import Counselor
from app.models.report import Report, ReportStatus
from app.schemas.session import (
    ParentsReportReference,
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

        # Build scenario context for analysis
        scenario_context = ""
        if session.scenario or session.scenario_description:
            scenario_context = f"【家長煩惱情境】{session.scenario or ''}"
            if session.scenario_description:
                scenario_context += f"\n{session.scenario_description}"

        # Call quick feedback service with both transcripts + scenario
        feedback_result = await quick_feedback_service.get_quick_feedback(
            recent_transcript=recent_transcript,
            full_transcript=full_transcript,
            tenant_id=tenant_id,
            mode=session_mode,
            scenario_context=scenario_context,
        )

        # Schedule logging as background task (runs AFTER response returned)
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
        # Use REAL token usage from Gemini response
        prompt_tokens = feedback_result.get("prompt_tokens", 0)
        completion_tokens = feedback_result.get("completion_tokens", 0)
        total_tokens = feedback_result.get(
            "total_tokens", prompt_tokens + completion_tokens
        )
        token_usage_data = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": total_tokens * 0.000001,  # Gemini Flash pricing
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
    from app.services.analysis.keyword_analysis_service import KeywordAnalysisService

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

        # Build scenario context for analysis
        scenario_context = ""
        if session.scenario or session.scenario_description:
            scenario_context = f"【家長煩惱情境】{session.scenario or ''}"
            if session.scenario_description:
                scenario_context += f"\n{session.scenario_description}"

        # Call SIMPLIFIED analysis with both transcripts + scenario
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

        # Schedule logging as background task (runs AFTER response returned)
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
        # Use REAL token usage from Gemini response
        prompt_tokens = analysis_result.get("prompt_tokens", 0)
        completion_tokens = analysis_result.get("completion_tokens", 0)
        total_tokens = analysis_result.get(
            "total_tokens", prompt_tokens + completion_tokens
        )
        token_usage_data = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": total_tokens * 0.000001,  # Gemini Flash pricing
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
    from app.services.external.gemini_service import GeminiService
    from app.services.external.openai_service import OpenAIService
    from app.services.rag.rag_retriever import RAGRetriever

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

                # Build a more effective search query
                # Include scenario info + key parts of transcript
                scenario_info = session.scenario or ""
                scenario_desc = session.scenario_description or ""
                search_query = f"{scenario_info} {scenario_desc}\n{transcript[:800]}"
                logger.info(
                    f"RAG search query (first 200 chars): {search_query[:200]}..."
                )

                # Search for parenting-related theories
                rag_results = await rag_retriever.search(
                    query=search_query,
                    top_k=5,
                    threshold=0.25,  # Lower threshold for better recall
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
                else:
                    logger.warning(
                        "RAG search returned no results - "
                        "check if parenting documents exist in vector DB"
                    )
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

        # Calculate transcript duration hint
        transcript_length = len(transcript)
        duration_hint = (
            "短對話"
            if transcript_length < 500
            else "中等對話"
            if transcript_length < 2000
            else "長對話"
        )

        # Build scenario context for report
        scenario_section = ""
        if session.scenario or session.scenario_description:
            scenario_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【家長煩惱情境】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{session.scenario or ''}
{session.scenario_description or ''}

⚠️ 請圍繞上述家長的煩惱情境進行分析，提供針對性的建議。
"""

        analysis_prompt = f"""你是專業的親子溝通分析師，精通 8 大教養流派（阿德勒正向教養、薩提爾、ABA行為分析、Dan Siegel 全腦教養、Gottman 情緒輔導、Ross Greene 協作問題解決、Dr. Becky Kennedy、社會意識教養），負責分析家長與孩子的對話，提供建設性的回饋。
{scenario_section}{rag_context}{rag_instruction}
【對話逐字稿】（{duration_hint}，共 {transcript_length} 字）
{transcript}

【分析要求】
請以中性、客觀、溫和的立場**深入分析**這次對話。
⚠️ 重要：請根據對話長度提供**相應深度的分析**：
- 短對話（< 500 字）：提供基本分析
- 中等對話（500-2000 字）：提供詳細分析，包含多個觀察點
- 長對話（> 2000 字）：提供完整、深入的分析，涵蓋對話中的各個關鍵時刻

請提供以下 4 個部分：

1. **鼓勵標題**（encouragement）
   - 一段正向鼓勵的話，肯定家長願意溝通的心意
   - 具體指出家長做得好的地方
   - 例如：「這次你已經做了一件重要的事：願意好好跟孩子談。當你說『我想聽聽你的想法』時，展現了開放的態度。」

2. **待解決的議題**（issue）
   - 指出這次對話中最需要改進的地方
   - 客觀描述，不批判
   - 如果對話較長，可以列出多個議題

3. **溝通內容分析**（analyze）
   - **深入分析**為何這樣的溝通方式可能有問題
   - 解釋背後的心理學或教養理論原理
   - 引用相關教養流派的觀點（如：薩提爾冰山理論、阿德勒歸屬感、Gottman 情緒輔導等）
   - 分析對話中的情緒動態、權力關係、溝通模式
   - ⚠️ 對於長對話，請提供完整、詳盡的分析（300-500 字）

4. **建議下次可以這樣說**（suggestion）
   - 提供具體、可直接使用的替代說法
   - 用「」標示建議的話語
   - 提供多個情境下的建議話術
   - 解釋為什麼這樣說更有效
   - ⚠️ 對於長對話，提供多種情境的建議（200-400 字）

【語氣要求】
- 溫和、同理、建設性
- 避免批判或讓家長感到被指責
- 展現專業深度，讓家長感受到「有料」的分析

【輸出格式】
請以 JSON 格式回應：

{{
  "encouragement": "正向鼓勵標題（包含具體觀察）",
  "issue": "待解決的議題（可以是多點，用換行分隔）",
  "analyze": "溝通內容深入分析（根據對話長度，提供 150-500 字的分析）",
  "suggestion": "建議下次可以這樣說（提供多個情境的具體話術，150-400 字）"
}}

請開始深入分析。"""

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

        # Create or update Report record for has_report flag
        try:
            existing_report = db.execute(
                select(Report).where(
                    Report.session_id == session_id,
                    Report.deleted_at.is_(None),
                )
            ).scalar_one_or_none()

            # Build content for Report
            report_content_json = {
                "encouragement": analysis.get("encouragement", ""),
                "issue": analysis.get("issue", ""),
                "analyze": analysis.get("analyze", ""),
                "suggestion": analysis.get("suggestion", ""),
                "references": [ref.model_dump() for ref in rag_references],
            }

            # Build markdown content
            report_content_markdown = f"""# 親子對話報告

## 🌟 鼓勵
{analysis.get("encouragement", "")}

## 💡 待解決的議題
{analysis.get("issue", "")}

## 📊 溝通內容分析
{analysis.get("analyze", "")}

## 💬 建議下次可以這樣說
{analysis.get("suggestion", "")}
"""

            if existing_report:
                # Update existing report
                existing_report.content_json = report_content_json
                existing_report.content_markdown = report_content_markdown
                existing_report.status = ReportStatus.DRAFT
                existing_report.prompt_tokens = gemini_response.get("prompt_tokens", 0)
                existing_report.completion_tokens = gemini_response.get(
                    "completion_tokens", 0
                )
                logger.info(f"Updated existing Report for session {session_id}")
            else:
                # Create new report
                new_report = Report(
                    session_id=session_id,
                    client_id=client.id,
                    created_by_id=current_user.id,
                    tenant_id=tenant_id,
                    status=ReportStatus.DRAFT,
                    mode="island_parents",
                    content_json=report_content_json,
                    content_markdown=report_content_markdown,
                    prompt_tokens=gemini_response.get("prompt_tokens", 0),
                    completion_tokens=gemini_response.get("completion_tokens", 0),
                )
                db.add(new_report)
                logger.info(f"Created new Report for session {session_id}")

            db.commit()
        except Exception as e:
            # Report creation failure should not block response
            logger.error(f"Failed to create/update Report record: {e}", exc_info=True)
            db.rollback()

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
