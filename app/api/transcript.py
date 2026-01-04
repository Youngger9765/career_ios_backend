"""
Transcript Analysis API - 逐字稿分析統一入口

新的統一 API 結構：
- POST /api/v1/transcript/deep-analyze    深層分析
- POST /api/v1/transcript/quick-feedback  快速反饋
- POST /api/v1/transcript/report          親子對話報告

所有 endpoint 都接受 tenant_id 參數（預設 island_parents）
"""
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.session import (
    CounselingMode,
    ImprovementSuggestion,
    ParentsReportResponse,
    ProviderMetadata,
    QuickFeedbackResponse,
    RAGSource,
    RealtimeAnalyzeResponse,
)
from app.services.gemini_service import GeminiService
from app.services.quick_feedback_service import quick_feedback_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/transcript", tags=["Transcript Analysis"])

# Initialize services
gemini_service = GeminiService()


# ============== Request Schemas ==============


class DeepAnalyzeRequest(BaseModel):
    """深層分析請求"""

    transcript: str = Field(..., min_length=1, description="逐字稿內容")
    session_id: Optional[str] = Field(
        None, description="Session ID（選填，有的話從 DB 取 transcript）"
    )
    mode: CounselingMode = Field(
        default=CounselingMode.practice, description="分析模式"
    )
    use_rag: bool = Field(default=False, description="是否使用 RAG 知識庫")
    tenant_id: str = Field(default="island_parents", description="租戶 ID")
    speakers: Optional[list] = Field(
        default=None, description="Speaker 片段列表（選填）"
    )
    time_range: str = Field(default="0:00-2:00", description="時間範圍")


class QuickFeedbackRequest(BaseModel):
    """快速反饋請求"""

    transcript: str = Field(..., min_length=1, description="最近的逐字稿")
    session_id: Optional[str] = Field(None, description="Session ID（選填）")
    tenant_id: str = Field(default="island_parents", description="租戶 ID")


class ReportRequest(BaseModel):
    """親子對話報告請求"""

    transcript: str = Field(..., min_length=1, description="完整對話逐字稿")
    session_id: Optional[str] = Field(None, description="Session ID（選填）")
    tenant_id: str = Field(default="island_parents", description="租戶 ID")


# ============== Helper Functions ==============


async def _get_transcript_from_session(session_id: str, db: Session) -> Optional[str]:
    """從 session 取得逐字稿"""
    from app.models.session import Session as SessionModel

    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if session and session.transcript_text:
        return session.transcript_text
    return None


async def write_to_gbq_async(data: dict) -> None:
    """Write to BigQuery asynchronously (non-blocking)"""
    from app.services.gbq_service import gbq_service

    try:
        await gbq_service.write_analysis_log(data)
    except Exception as e:
        logger.error(f"Failed to write to BigQuery (non-blocking): {str(e)}")


# ============== Endpoints ==============


@router.post("/deep-analyze", response_model=RealtimeAnalyzeResponse)
async def deep_analyze(
    request: DeepAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    深層分析逐字稿

    - 使用 KeywordAnalysisService 進行分析
    - 返回 safety_level, summary, suggestions
    - 支援 session_id 自動取得逐字稿
    """
    start_time = time.time()

    try:
        from app.services.keyword_analysis_service import KeywordAnalysisService

        # Get transcript (from request or session)
        transcript = request.transcript
        if request.session_id:
            session_transcript = await _get_transcript_from_session(
                request.session_id, db
            )
            if session_transcript:
                transcript = session_transcript

        # Initialize service
        keyword_service = KeywordAnalysisService(db)

        # Get mode value
        mode_value = (
            request.mode.value if hasattr(request.mode, "value") else request.mode
        )

        # Call analysis service
        logger.info(
            f"Deep analyze: tenant={request.tenant_id}, mode={mode_value}, use_rag={request.use_rag}"
        )
        analysis_result = await keyword_service.analyze_keywords(
            session_id=request.session_id,
            transcript_segment=transcript,
            full_transcript=transcript,
            context="",
            analysis_type=request.tenant_id,  # Use tenant_id as analysis_type
            mode=mode_value,
            db=db,
            use_rag=request.use_rag,
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

        # Prepare GBQ data
        metadata = analysis_result.get("_metadata", {})
        gbq_data = {
            "id": str(uuid.uuid4()),
            "tenant_id": request.tenant_id,
            "session_id": request.session_id,
            "analyzed_at": datetime.now(timezone.utc),
            "analysis_type": "deep_analyze",
            "mode": mode_value,
            "safety_level": response_data["safety_level"],
            "matched_suggestions": quick_suggestions,
            "transcript_segment": transcript[:1000],
            "response_time_ms": latency_ms,
            "created_at": datetime.now(timezone.utc),
            "prompt_tokens": metadata.get("prompt_tokens", 0),
            "completion_tokens": metadata.get("completion_tokens", 0),
            "total_tokens": metadata.get("total_tokens", 0),
            "estimated_cost_usd": metadata.get("estimated_cost_usd", 0.0),
            "rag_used": request.use_rag,
            "rag_sources": metadata.get("rag_sources", []),
        }

        background_tasks.add_task(write_to_gbq_async, gbq_data)

        return RealtimeAnalyzeResponse(
            safety_level=response_data["safety_level"],
            summary=response_data["summary"],
            alerts=response_data["alerts"],
            suggestions=response_data["suggestions"],
            time_range=request.time_range,
            timestamp=datetime.now(timezone.utc).isoformat(),
            rag_sources=rag_sources,
            cache_metadata=None,
            provider_metadata=provider_metadata,
        )

    except Exception as e:
        logger.error(f"Deep analyze failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-feedback", response_model=QuickFeedbackResponse)
async def quick_feedback(request: QuickFeedbackRequest, db: Session = Depends(get_db)):
    """
    快速反饋（輕量級，~8秒）

    - 使用 QuickFeedbackService 生成簡短鼓勵訊息
    - 返回 1 句話（20字內）
    """
    try:
        # Get transcript (from request or session)
        transcript = request.transcript
        if request.session_id:
            session_transcript = await _get_transcript_from_session(
                request.session_id, db
            )
            if session_transcript:
                transcript = session_transcript

        # Call quick feedback service
        result = await quick_feedback_service.get_quick_feedback(
            recent_transcript=transcript
        )

        return QuickFeedbackResponse(
            message=result["message"],
            type=result["type"],
            timestamp=result["timestamp"],
            latency_ms=result["latency_ms"],
        )

    except Exception as e:
        logger.error(f"Quick feedback failed: {e}", exc_info=True)
        return QuickFeedbackResponse(
            message="繼續保持，你做得很好",
            type="fallback_error",
            timestamp=datetime.now().isoformat(),
            latency_ms=0,
        )


@router.post("/report", response_model=ParentsReportResponse)
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    生成親子對話報告

    - 分析對話並提供：摘要、亮點、改進建議
    - 可選使用 RAG 知識庫
    """
    import json
    import re

    start_time = datetime.now(timezone.utc)
    _rag_start_time = None  # Reserved for future RAG timing
    llm_start_time = None

    try:
        # Get transcript (from request or session)
        transcript = request.transcript
        if request.session_id:
            session_transcript = await _get_transcript_from_session(
                request.session_id, db
            )
            if session_transcript:
                transcript = session_transcript

        # Build analysis prompt
        analysis_prompt = f"""你是專業的親子溝通分析師，負責分析家長與孩子的對話，提供建設性的回饋。

【對話逐字稿】
{transcript}

【分析要求】
請以中性、客觀、溫和的立場分析這次對話，提供以下 4 個部分：

1. **對話主題與摘要**（summary）
   - 簡短說明這次對話的主題是什麼
   - 中性立場，不批判，讓家長知道「這次到底說了什麼」
   - 1-2 句話即可

2. **溝通亮點**（highlights）
   - 列出家長在溝通中做得好的地方
   - 用正向、鼓勵的語氣
   - 3-5 個亮點，每個 ≤ 30 字

3. **改進建議**（improvements）
   - 指出值得更好的地方
   - 提供具體、可操作的建議
   - 每個建議包含：
     * issue: 需要改進的地方（≤ 40 字）
     * suggestion: 具體建議（≤ 60 字）
   - 2-4 個建議

【語氣要求】
- 溫和、同理、建設性
- 避免批判或讓家長感到被指責

【輸出格式】
請以 JSON 格式回應：

{{
  "summary": "對話主題摘要（1-2 句）",
  "highlights": ["亮點1", "亮點2", "亮點3"],
  "improvements": [
    {{"issue": "需要改進的地方", "suggestion": "具體建議"}}
  ]
}}

請開始分析。"""

        # Call Gemini
        llm_start_time = time.time()
        gemini_response = await gemini_service.chat_completion(
            prompt=analysis_prompt,
            temperature=0.7,
            return_metadata=True,
        )
        llm_end_time = time.time()
        llm_call_time_ms = int((llm_end_time - llm_start_time) * 1000)

        llm_raw_response = gemini_response["text"]
        _usage_metadata = gemini_response.get(
            "usage_metadata", {}
        )  # Reserved for future logging

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
            logger.error(f"Failed to parse response: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse AI response")

        # Build response
        improvements_list = [
            ImprovementSuggestion(
                issue=item.get("issue", ""), suggestion=item.get("suggestion", "")
            )
            for item in analysis.get("improvements", [])
        ]

        response = ParentsReportResponse(
            summary=analysis.get("summary", ""),
            highlights=analysis.get("highlights", []),
            improvements=improvements_list,
            rag_references=[],  # No RAG for now
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # GBQ logging
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        gbq_data = {
            "id": str(uuid.uuid4()),
            "tenant_id": request.tenant_id,
            "session_id": request.session_id,
            "analyzed_at": start_time,
            "analysis_type": "transcript_report",
            "mode": "report",
            "safety_level": "green",
            "transcript": transcript[:1000],
            "duration_ms": duration_ms,
            "llm_call_time_ms": llm_call_time_ms,
            "created_at": end_time,
        }

        background_tasks.add_task(write_to_gbq_async, gbq_data)

        logger.info(f"Report generated in {duration_ms}ms")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
