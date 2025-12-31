"""
Realtime STT Counseling API
"""
import logging
import os
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.realtime import (
    ImprovementSuggestion,
    ParentsReportRequest,
    ParentsReportResponse,
    ProviderMetadata,
    QuickFeedbackRequest,
    QuickFeedbackResponse,
    RAGSource,
    RealtimeAnalyzeRequest,
    RealtimeAnalyzeResponse,
)
from app.services.gbq_service import gbq_service
from app.services.gemini_service import GeminiService
from app.services.openai_service import OpenAIService
from app.services.quick_feedback_service import quick_feedback_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["Realtime Counseling"])

# Initialize services (still needed for generate_parents_report)
gemini_service = GeminiService()
openai_service = OpenAIService()

# REMOVED: SAFETY_WINDOW_SPEAKER_TURNS, SAFETY_WINDOW_CHARACTERS, ANNOTATED_SAFETY_WINDOW_TURNS
# These constants are now defined in KeywordAnalysisService

# REMOVED: CACHE_SYSTEM_INSTRUCTION
# System instruction is now part of keyword_analysis_service prompt templates

# Legacy system instruction (kept for reference, but no longer used by analyze_transcript)
_LEGACY_CACHE_SYSTEM_INSTRUCTION = """你是專業諮詢督導，分析即時諮詢對話。你的角色是站在案主與諮詢師之間，提供溫暖、同理且具體可行的專業建議。

【角色定義】CRITICAL - 必須嚴格遵守：
- "counselor" = 諮詢師/輔導師（專業助人者，提供協助的一方）
- "client" = 案主/個案/家長（求助者，有困擾需要協助的一方）
- 所有問題、困擾、症狀都是「案主/個案」面臨的，不是諮詢師的問題
- 分析焦點：案主的狀況、需求、風險
- 建議對象：給諮詢師的專業建議（如何協助案主）

【分析範圍】CRITICAL - 必須嚴格遵守：
🎯 **主要分析焦點**：最新一分鐘內的對話內容
   - 你會收到完整的對話記錄（可能長達數十分鐘）
   - 但你的分析必須聚焦在「最後出現的對話」（最新一分鐘）
   - 前面的對話僅作為背景脈絡參考，幫助你理解前因後果

【安全等級評估規則】CRITICAL - 必須嚴格遵守：
⚠️ **僅根據「【最近對話 - 用於安全評估】」區塊判斷安全等級**
   - 標註區塊顯示最近 5-10 個對話輪次
   - 不要因為完整逐字稿中出現過的危險詞就評估為高風險
   - 如果最近對話已經緩和、正向，即使之前有危險內容，也應評估為較低風險
   - 安全等級反映當前狀態，不是歷史狀態

🎯 **建議內容**：
   - 可以參考完整對話歷史，提供更有深度的建議
   - 但要聚焦在最近對話的當前狀態

【核心原則】同理優先、溫和引導、具體行動：

1. **同理與理解為先**
   - 永遠先理解與同理案主（家長）的感受和處境
   - 認可教養壓力、情緒失控是正常的人性反應
   - 避免批判、指責或讓案主感到被否定

2. **溫和、非批判的語氣**
   - ❌ 禁止用語：「表達出對孩子使用身體暴力的衝動」「可能造成傷害」「不當管教」
   - ✅ 建議用語：「理解到在教養壓力下，父母有時會感到情緒失控是很正常的」
   - ✅ 使用：「可以考慮」「或許」「試試看」等柔和引導詞
   - ✅ 焦點放在「如何調整」而非「哪裡做錯」

3. **具體、簡潔的建議**
   - 建議要具體可行，但保持簡短（不超過 50 字）
   - 避免抽象概念，用具體做法
   - 不要冗長的步驟說明或對話範例

【輸出格式】請提供以下 JSON 格式回應：

{
  "summary": "案主處境簡述（1-2 句）",
  "alerts": [
    "💡 同理案主感受（1 句）",
    "⚠️ 需關注的部分（1 句）"
  ],
  "suggestions": [
    "💡 核心建議（簡短，< 50 字）",
    "💡 具體做法（簡短，< 50 字）"
  ]
}

【語氣要求】溫和、同理、簡潔，避免批判或過度說教

【RAG 使用要求】CRITICAL - 必須嚴格遵守：
- 當分析涉及親子教養、兒童發展、管教策略等專業知識時，必須參考上方提供的「📚 相關親子教養知識庫內容」
- 優先使用知識庫中的理論、方法、建議（如正向教養、情緒教養等）
- 不要僅憑一般常識或想像回答專業問題
- 如果知識庫內容相關，請在建議中融入（不需明確標注來源）
"""

# REMOVED: PARENTING_KEYWORDS, _detect_parenting_keywords(), _detect_parenting_theory()
# These functions are now handled by keyword_analysis_service.analyze_keywords()


# Note: _search_rag_knowledge() is kept for generate_parents_report endpoint
def _detect_parenting_theory(title: str) -> str:
    """Detect which parenting theory a document belongs to based on title.

    Args:
        title: Document title

    Returns:
        Theory name in Chinese (e.g., "正向教養", "情緒教養")
    """
    # Theory keyword mappings (Chinese, English, and file name patterns)
    theory_mappings = {
        "正向教養": ["正向教養", "Positive Discipline", "positive_discipline"],
        "情緒教養": [
            "情緒教養",
            "Emotional Coaching",
            "Emotion Coaching",
            "emotional_coaching",
        ],
        "依附理論": ["依附理論", "Attachment Theory", "attachment_theory"],
        "認知發展理論": ["認知發展", "Cognitive Development", "cognitive_development"],
        "自我決定論": ["自我決定", "Self-Determination", "self_determination"],
    }

    # Check each theory's keywords (case-insensitive)
    title_lower = title.lower()
    for theory_name, keywords in theory_mappings.items():
        for keyword in keywords:
            if keyword.lower() in title_lower:
                return theory_name

    # Default if no match found
    return "其他"


async def _search_rag_knowledge(
    transcript: str, db: Session, top_k: int = 3, similarity_threshold: float = 0.5
):
    """Search RAG knowledge base for relevant parenting content.

    NOTE: Only used by generate_parents_report endpoint.
    analyze_transcript now uses keyword_analysis_service which has built-in RAG.

    Args:
        transcript: The transcript text to search
        db: Database session
        top_k: Number of top results to return
        similarity_threshold: Minimum similarity score

    Returns:
        List of RAG sources with title, content, and score
    """
    from app.services.rag_chat_service import RAGChatService

    try:
        # Initialize RAG service
        rag_service = RAGChatService(db=db)

        # Generate embedding for transcript
        query_embedding = await openai_service.create_embedding(transcript)

        # Search similar chunks with parenting category filter
        rows = await rag_service.search_similar_chunks(
            query_embedding=query_embedding,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            category="parenting",  # Filter for parenting documents only
        )

        # Build RAG sources response
        rag_sources = []
        for row in rows:
            # Detect theory from document title
            theory = _detect_parenting_theory(row.document_title)

            rag_sources.append(
                RAGSource(
                    title=row.document_title,
                    content=row.text[:300],  # Truncate to 300 chars
                    score=round(float(row.similarity_score), 2),
                    theory=theory,
                )
            )

        logger.info(f"RAG search found {len(rag_sources)} relevant sources")
        return rag_sources

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        # Return empty list on error (fallback)
        return []


# REMOVED: _assess_safety_level() and _build_annotated_transcript()
# These functions are now handled internally by keyword_analysis_service
# via the island_parents prompt templates which include sliding window logic


# REMOVED: _build_emergency_prompt() and _build_practice_prompt()
# These functions are now handled by keyword_analysis_service.analyze_keywords()
# which provides unified prompt management with 200 expert suggestions


def _calculate_gemini_cost(usage_metadata: dict) -> float:
    """Calculate estimated cost for Gemini API usage

    Gemini 3 Flash pricing (as of Dec 2025):
    - Input: $0.50 per 1M tokens
    - Output: $3.00 per 1M tokens
    - Cached input: $0.125 per 1M tokens (75% discount)
    """
    prompt_tokens = usage_metadata.get("prompt_token_count", 0)
    completion_tokens = usage_metadata.get("candidates_token_count", 0)
    cached_tokens = usage_metadata.get("cached_content_token_count", 0)

    # Subtract cached tokens from prompt tokens
    non_cached_prompt = max(0, prompt_tokens - cached_tokens)

    # Calculate costs (convert to per 1K tokens)
    prompt_cost = (non_cached_prompt / 1000) * 0.0005  # $0.50/1M = $0.0005/1K
    cached_cost = (cached_tokens / 1000) * 0.000125  # $0.125/1M = $0.000125/1K
    completion_cost = (completion_tokens / 1000) * 0.003  # $3/1M = $0.003/1K

    return prompt_cost + cached_cost + completion_cost


async def write_to_gbq_async(data: dict) -> None:
    """Write realtime analysis result to BigQuery asynchronously

    This is a wrapper function that catches all exceptions to prevent
    GBQ write failures from affecting API response.

    Args:
        data: Analysis data to write to BigQuery
    """
    try:
        await gbq_service.write_analysis_log(data)
    except Exception as e:
        # Log error but don't raise - GBQ failures should not block API
        logger.error(
            f"Failed to write to BigQuery (non-blocking): {str(e)}", exc_info=True
        )


@router.post("/analyze", response_model=RealtimeAnalyzeResponse)
async def analyze_transcript(
    request: RealtimeAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Analyze realtime counseling transcript with AI supervision.

    Now uses unified keyword_analysis_service for consistency with session analysis.

    Returns summary, alerts, and suggestions for the counselor based on
    the conversation in the past 60 seconds.

    This is a demo feature with no authentication required.
    """
    import time

    start_time = time.time()

    try:
        # Import keyword_analysis_service
        from app.services.keyword_analysis_service import KeywordAnalysisService

        # Initialize service
        keyword_service = KeywordAnalysisService(db)

        # Convert mode to string value if needed
        mode_value = (
            request.mode.value if hasattr(request.mode, "value") else request.mode
        )

        # Call unified analysis service
        logger.info(f"Calling keyword_analysis_service with mode={mode_value}")
        analysis_result = await keyword_service.analyze_keywords(
            session_id=None,  # realtime doesn't have session concept
            transcript_segment=request.transcript,
            full_transcript=request.transcript,  # same as segment for realtime
            context="",  # no additional context for realtime
            analysis_type="island_parents",  # realtime is always island_parents
            mode=mode_value,  # "emergency" or "practice"
            db=db,
        )

        # Transform result to realtime API format
        # keyword_service returns: {safety_level, severity, quick_suggestions, detailed_scripts, ...}
        # realtime expects: {summary, alerts, suggestions, safety_level}

        # Extract quick_suggestions (from 200 expert sentences)
        quick_suggestions = analysis_result.get("quick_suggestions", [])

        # Build response_data
        response_data = {
            "safety_level": analysis_result.get("safety_level", "green"),
            "summary": analysis_result.get("display_text", "分析完成"),
            "alerts": [],  # Build from action_suggestion
            "suggestions": quick_suggestions,  # Use expert suggestions
        }

        # Add alerts from action_suggestion
        action_suggestion = analysis_result.get("action_suggestion", "")
        if action_suggestion:
            response_data["alerts"].append(action_suggestion)

        # Extract RAG sources for response
        rag_documents = analysis_result.get("rag_documents", [])
        rag_sources = [
            RAGSource(
                title=doc.get("title", ""),
                content=doc.get("content", "")[:300],  # Truncate to 300 chars
                score=round(float(doc.get("relevance_score", 0)), 2),
                theory="其他",  # Could detect theory from title if needed
            )
            for doc in rag_documents
        ]

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        provider_metadata = ProviderMetadata(
            provider="gemini", latency_ms=latency_ms, model="gemini-3-flash-preview"
        )

        # Calculate response time in milliseconds
        response_time_ms = latency_ms

        # Prepare data for BigQuery (asynchronous write)
        metadata = analysis_result.get("_metadata", {})
        gbq_data = {
            "id": str(uuid.uuid4()),
            "tenant_id": "island_parents",  # Fixed for web version
            "session_id": None,  # Web version has no session concept
            "analyzed_at": datetime.now(timezone.utc),
            "analysis_type": "realtime_analysis",  # Fixed: analysis method type
            "mode": mode_value,  # "emergency" or "practice"
            "safety_level": response_data[
                "safety_level"
            ],  # "green", "yellow", or "red"
            "matched_suggestions": quick_suggestions,
            "transcript_segment": request.transcript[:1000],  # Limit to 1000 chars
            "response_time_ms": response_time_ms,
            "created_at": datetime.now(timezone.utc),
            # Additional metadata from keyword_service
            "prompt_tokens": metadata.get("prompt_tokens", 0),
            "completion_tokens": metadata.get("completion_tokens", 0),
            "total_tokens": metadata.get("total_tokens", 0),
            "estimated_cost_usd": metadata.get("estimated_cost_usd", 0.0),
            "rag_used": metadata.get("rag_used", False),
            "rag_sources": metadata.get("rag_sources", []),
        }

        # Schedule GBQ write as background task (non-blocking)
        background_tasks.add_task(write_to_gbq_async, gbq_data)

        # Build response
        return RealtimeAnalyzeResponse(
            safety_level=response_data["safety_level"],
            summary=response_data["summary"],
            alerts=response_data["alerts"],
            suggestions=response_data["suggestions"],
            time_range=request.time_range,
            timestamp=datetime.now(timezone.utc).isoformat(),
            rag_sources=rag_sources,
            cache_metadata=None,  # Cache not used anymore
            provider_metadata=provider_metadata,
        )
    except Exception as e:
        logger.error(f"Realtime analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick-feedback", response_model=QuickFeedbackResponse)
async def get_quick_feedback(request: QuickFeedbackRequest):
    """Generate quick AI-powered encouragement for 10-15 second intervals.

    This lightweight endpoint provides instant feedback while waiting for
    full analysis. Uses AI to read current context and respond appropriately.

    Example usage:
    - iOS polls every 10-15 seconds with recent transcript
    - Gets back a short encouragement message (< 20 chars)
    - Displays to user while waiting for 60-second full analysis

    Returns:
        QuickFeedbackResponse with AI-generated message and latency info
    """
    try:
        # Call quick feedback service
        result = await quick_feedback_service.get_quick_feedback(
            recent_transcript=request.recent_transcript
        )

        # Return response
        return QuickFeedbackResponse(
            message=result["message"],
            type=result["type"],
            timestamp=result["timestamp"],
            latency_ms=result["latency_ms"],
        )

    except Exception as e:
        logger.error(f"Quick feedback failed: {e}", exc_info=True)
        # Return fallback instead of raising error
        import datetime

        return QuickFeedbackResponse(
            message="繼續保持，你做得很好",
            type="fallback_error",
            timestamp=datetime.datetime.now().isoformat(),
            latency_ms=0,
        )


@router.post("/elevenlabs-token")
async def generate_elevenlabs_token():
    """Generate a single-use token for ElevenLabs Speech-to-Text WebSocket.

    This endpoint calls ElevenLabs API to generate a temporary token that
    can be used by the frontend to connect to their WebSocket service.
    This approach keeps the API key secure on the server side.

    Returns:
        Dict with 'token' key containing the single-use token

    Raises:
        HTTPException: If token generation fails
    """
    try:
        # Get API key from environment
        api_key = os.getenv("ELEVEN_LABS_API_KEY")
        if not api_key:
            logger.error("ELEVEN_LABS_API_KEY not found in environment")
            raise HTTPException(
                status_code=500, detail="ElevenLabs API key not configured"
            )

        # Call ElevenLabs API to generate single-use token
        # Token type: "realtime_scribe" for speech-to-text WebSocket
        url = "https://api.elevenlabs.io/v1/single-use-token/realtime_scribe"
        headers = {"xi-api-key": api_key}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, timeout=30.0)

            if response.status_code != 200:
                logger.error(
                    f"ElevenLabs API error: {response.status_code} - {response.text}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate token: {response.text}",
                )

            token_data = response.json()
            logger.info("Successfully generated ElevenLabs token")

            return {"token": token_data.get("token")}

    except httpx.TimeoutException:
        logger.error("Timeout calling ElevenLabs API")
        raise HTTPException(
            status_code=504, detail="Timeout generating token from ElevenLabs"
        )
    except Exception as e:
        logger.error(f"Token generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Token generation failed: {e}")


@router.post("/parents-report", response_model=ParentsReportResponse)
async def generate_parents_report(
    request: ParentsReportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Generate a comprehensive parenting communication report.

    Analyzes parent-child conversation transcript and provides:
    1. Summary/theme of the conversation (neutral stance)
    2. Communication highlights (what went well)
    3. Areas for improvement with specific suggestions
    4. Relevant RAG references from parenting knowledge base

    This endpoint queries the parenting RAG knowledge base and uses
    Gemini to generate structured feedback.

    Results are persisted to BigQuery for analytics.
    """
    import json
    import time
    import uuid

    # Track timing for GBQ
    start_time = datetime.now(timezone.utc)
    rag_start_time = None
    rag_end_time = None
    llm_start_time = None
    llm_end_time = None

    try:
        # Step 1: Search RAG knowledge base for relevant parenting content
        logger.info("Searching RAG for parenting-related content")
        rag_start_time = time.time()
        rag_sources = await _search_rag_knowledge(
            transcript=request.transcript,
            db=db,
            top_k=5,  # Get more sources for comprehensive report
            similarity_threshold=0.5,
        )
        rag_end_time = time.time()
        rag_search_time_ms = int((rag_end_time - rag_start_time) * 1000)

        # Step 2: Build RAG context for prompt
        rag_context = ""
        if rag_sources:
            rag_context_parts = ["\n\n📚 相關親子教養知識庫內容（供參考）：\n"]
            for idx, source in enumerate(rag_sources, 1):
                rag_context_parts.append(
                    f"[{idx}] {source.title} ({source.theory}): {source.content}"
                )
            rag_context = "\n".join(rag_context_parts)
            logger.info(f"Found {len(rag_sources)} relevant RAG sources")
        else:
            logger.info("No RAG sources found, proceeding without context")

        # Step 3: Build analysis prompt
        analysis_prompt = f"""你是專業的親子溝通分析師，負責分析家長與孩子的對話，提供建設性的回饋。

【對話逐字稿】
{request.transcript}

{rag_context}

【分析要求】
請以中性、客觀、溫和的立場分析這次對話，提供以下 4 個部分：

1. **對話主題與摘要**（summary）
   - 簡短說明這次對話的主題是什麼
   - 中性立場，不批判，讓家長知道「這次到底說了什麼」
   - 1-2 句話即可

2. **溝通亮點**（highlights）
   - 列出家長在溝通中做得好的地方
   - 例如：展現同理心、願意傾聽、嘗試理解孩子感受等
   - 用正向、鼓勵的語氣
   - 3-5 個亮點，每個 ≤ 30 字

3. **改進建議**（improvements）
   - 指出值得更好的地方
   - 提供具體、可操作的建議或換句話說
   - 溫和、非批判的語氣
   - 每個建議包含：
     * issue: 需要改進的地方（具體描述，≤ 40 字）
     * suggestion: 具體建議或換句話說（≤ 60 字）
   - 2-4 個建議

4. **知識庫參考**（rag_references）
   - 已自動提供上方的 RAG 知識庫內容
   - 你不需要額外處理，只需在分析時參考即可

【語氣要求】
- 溫和、同理、建設性
- 避免批判或讓家長感到被指責
- 用「可以試試」「或許」「換個方式」等柔和引導詞
- 焦點放在「如何做得更好」而非「哪裡做錯」

【輸出格式】
請以 JSON 格式回應（不要用 markdown code block，直接輸出 JSON）：

{{
  "summary": "對話主題摘要（1-2 句）",
  "highlights": [
    "亮點1（≤ 30 字）",
    "亮點2（≤ 30 字）",
    "亮點3（≤ 30 字）"
  ],
  "improvements": [
    {{
      "issue": "需要改進的地方（≤ 40 字）",
      "suggestion": "具體建議或換句話說（≤ 60 字）"
    }}
  ]
}}

⚠️ 重要：請確保 JSON 格式正確，不要在最後一個元素後面加逗號（trailing comma）！

請開始分析。"""

        # Step 4: Call Gemini for analysis
        logger.info("Calling Gemini for report generation")
        llm_start_time = time.time()
        gemini_response = await gemini_service.chat_completion(
            prompt=analysis_prompt,
            temperature=0.7,  # Higher temperature for more natural language
            return_metadata=True,  # Get usage metadata for observability
        )
        llm_end_time = time.time()
        llm_call_time_ms = int((llm_end_time - llm_start_time) * 1000)

        # Extract response text and metadata
        llm_raw_response = gemini_response["text"]
        usage_metadata = gemini_response.get("usage_metadata", {})

        # Step 5: Parse Gemini response
        try:
            # Try to extract JSON from response
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

            # Remove trailing commas from JSON (common LLM mistake)
            import re

            json_text = re.sub(r",(\s*[}\]])", r"\1", json_text)

            analysis = json.loads(json_text)
            logger.info("Successfully parsed Gemini response")

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.error(f"Response text: {llm_raw_response[:500]}")
            raise HTTPException(
                status_code=500, detail="Failed to parse AI analysis response"
            )

        # Step 6: Build response
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
            rag_references=rag_sources,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Step 7: Prepare GBQ data for analytics
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Determine safety level based on number of improvements
        # More improvements = more issues = higher concern level
        safety_level = "green"  # Default
        if len(improvements_list) >= 4:
            safety_level = "yellow"  # Multiple areas to improve
        elif len(improvements_list) >= 2:
            safety_level = "green"  # Normal feedback
        # Note: parents_report doesn't have explicit "red" level like realtime

        # Prepare comprehensive GBQ data for observability
        gbq_data = {
            # IDs and metadata
            "id": str(uuid.uuid4()),
            "tenant_id": "island_parents",
            "session_id": request.session_id if request.session_id else None,
            "request_id": str(uuid.uuid4()),
            # Timestamps
            "analyzed_at": start_time,
            "start_time": start_time,
            "end_time": end_time,
            "created_at": end_time,
            # Analysis type and result
            "analysis_type": "parents_report",
            "safety_level": safety_level,
            "matched_suggestions": [
                f"{imp.issue} → {imp.suggestion}" for imp in improvements_list
            ],
            "analysis_result": analysis,  # Full parsed JSON
            # Input data
            "transcript": request.transcript,  # Store full transcript
            "speakers": None,  # Parents report doesn't have speaker info
            # Prompts
            "system_prompt": None,  # Gemini doesn't separate system/user in this call
            "user_prompt": analysis_prompt,  # The full prompt
            "prompt_template": "parents_report_v1",
            # RAG information
            "rag_used": len(rag_sources) > 0,
            "rag_query": request.transcript[
                :200
            ],  # First 200 chars used for RAG search
            "rag_documents": [
                {
                    "content": source.content[:500],
                    "source": source.title,
                    "similarity": source.score,
                }
                for source in rag_sources
            ]
            if rag_sources
            else None,
            "rag_sources": [source.title for source in rag_sources]
            if rag_sources
            else [],
            "rag_top_k": 5,
            "rag_similarity_threshold": 0.5,
            "rag_search_time_ms": rag_search_time_ms if rag_start_time else None,
            # Model information
            "provider": "gemini",
            "model_name": "gemini-3-flash-preview",
            "model_version": "3.0",
            # Timing breakdown
            "duration_ms": duration_ms,
            "api_response_time_ms": duration_ms,
            "llm_call_time_ms": llm_call_time_ms if llm_start_time else None,
            # LLM response
            "llm_raw_response": llm_raw_response,
            # Token usage (from Gemini usage_metadata)
            "prompt_tokens": usage_metadata.get("prompt_token_count"),
            "completion_tokens": usage_metadata.get("candidates_token_count"),
            "total_tokens": usage_metadata.get("total_token_count"),
            "cached_tokens": usage_metadata.get("cached_content_token_count"),
            "estimated_cost_usd": _calculate_gemini_cost(usage_metadata)
            if usage_metadata
            else None,
            # Cache info (not used in parents_report)
            "use_cache": False,
            "cache_hit": None,
            "cache_key": None,
            "gemini_cache_ttl": None,
            # Mode
            "mode": "parents_report",
        }

        # Schedule GBQ write as background task (non-blocking)
        background_tasks.add_task(write_to_gbq_async, gbq_data)

        logger.info(
            f"Parents report generated successfully in {duration_ms}ms with {len(improvements_list)} improvements"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Parents report generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
