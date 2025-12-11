"""
Realtime STT Counseling API
"""
import logging
import os
from datetime import datetime, timezone
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.realtime import (
    CacheMetadata,
    ProviderMetadata,
    RAGSource,
    RealtimeAnalyzeRequest,
    RealtimeAnalyzeResponse,
)
from app.services.cache_manager import CacheManager
from app.services.gemini_service import GeminiService
from app.services.openai_service import OpenAIService
from app.services.rag_chat_service import RAGChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["Realtime Counseling"])

# Initialize services
gemini_service = GeminiService()
openai_service = OpenAIService()
cache_manager = CacheManager()

# System instruction for cache (固定不變的部分)
CACHE_SYSTEM_INSTRUCTION = """你是專業諮詢督導，分析即時諮詢對話。你的角色是站在案主與諮詢師之間，提供溫暖、同理且具體可行的專業建議。

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

【語氣要求】溫和、同理、簡潔，避免批判或過度說教。
"""

# Parenting-related keywords that trigger RAG search
PARENTING_KEYWORDS = [
    "親子",
    "孩子",
    "小孩",
    "兒童",
    "青少年",
    "教養",
    "育兒",
    "管教",
    "溝通",
    "情緒",
    "行為",
    "學習",
    "發展",
    "成長",
    "叛逆",
    "青春期",
    "親職",
    "家庭",
    "父母",
    "媽媽",
    "爸爸",
    "教育",
    "陪伴",
    "關係",
    "衝突",
]


def _detect_parenting_keywords(transcript: str) -> bool:
    """Detect if transcript contains parenting-related keywords.

    Args:
        transcript: The transcript text

    Returns:
        True if parenting keywords detected, False otherwise
    """
    transcript_lower = transcript.lower()
    for keyword in PARENTING_KEYWORDS:
        if keyword in transcript_lower:
            logger.info(f"Parenting keyword detected: {keyword}")
            return True
    return False


def _detect_parenting_theory(title: str) -> str:
    """Detect which parenting theory a document belongs to based on title.

    Args:
        title: Document title

    Returns:
        Theory name in Chinese (e.g., "正向教養", "情緒教養")
    """
    # Theory keyword mappings (Chinese and English)
    theory_mappings = {
        "正向教養": ["正向教養", "Positive Discipline"],
        "情緒教養": ["情緒教養", "Emotional Coaching", "Emotion Coaching"],
        "依附理論": ["依附理論", "Attachment Theory"],
        "認知發展理論": ["認知發展", "Cognitive Development"],
        "自我決定論": ["自我決定", "Self-Determination"],
    }

    # Check each theory's keywords
    for theory_name, keywords in theory_mappings.items():
        for keyword in keywords:
            if keyword in title:
                return theory_name

    # Default if no match found
    return "其他"


async def _search_rag_knowledge(
    transcript: str, db: Session, top_k: int = 3, similarity_threshold: float = 0.7
) -> List[RAGSource]:
    """Search RAG knowledge base for relevant parenting content.

    Args:
        transcript: The transcript text to search
        db: Database session
        top_k: Number of top results to return
        similarity_threshold: Minimum similarity score

    Returns:
        List of RAG sources with title, content, and score
    """
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


async def _analyze_with_codeer(
    transcript: str,
    speakers: List[dict],
    rag_context: str,
    db: Session,
    session_id: str = "",
    model: str = "gpt5-mini",
) -> dict:
    """Analyze transcript using Codeer 親子專家 agent.

    Args:
        transcript: Full transcript text
        speakers: List of speaker segments
        rag_context: RAG knowledge context
        db: Database session
        session_id: Session ID for session pooling (optional)
        model: Codeer model selection (claude-sonnet, gemini-flash, or gpt5-mini)

    Returns:
        Dict with summary, alerts, suggestions
    """
    import json

    from app.services.codeer_client import CodeerClient, get_codeer_agent_id
    from app.services.codeer_session_pool import get_codeer_session_pool

    # Get agent ID based on model selection
    try:
        agent_id = get_codeer_agent_id(model)
        logger.info(f"Using Codeer model: {model}, agent_id: {agent_id}")
    except Exception as e:
        logger.error(f"Failed to get Codeer agent ID: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Create client with longer timeout for analysis
    client = CodeerClient()
    # Extend timeout to 60 seconds for LLM response
    client.client.timeout = httpx.Timeout(60.0)

    try:
        # Build analysis prompt similar to Gemini's
        # Format: system instruction + RAG context + transcript
        prompt = f"""{CACHE_SYSTEM_INSTRUCTION}

{rag_context if rag_context else ""}

【最新對話逐字稿】
{transcript}

【Speaker 片段】
{json.dumps(speakers, ensure_ascii=False, indent=2)}

請分析以上對話，提供 JSON 格式回應。
"""

        # Create or reuse chat session with selected agent
        if session_id:
            # Use session pool for reuse
            pool = get_codeer_session_pool()
            chat = await pool.get_or_create_session(
                session_id, client, agent_id=agent_id
            )
            logger.info(f"Using session pool for {session_id} with agent {agent_id}")
        else:
            # Fallback: create new chat with selected agent
            # Use microsecond precision + model name to ensure unique chat names
            import uuid

            unique_suffix = (
                f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
            )
            chat = await client.create_chat(
                name=f"Realtime-{model}-{unique_suffix}",
                agent_id=agent_id,
            )
            logger.info(
                f"Created new chat (no session_id) with agent {agent_id}: {chat['name']}"
            )

        # Send message to Codeer agent (non-streaming for now)
        # CRITICAL: Must pass agent_id to match the agent used to create the chat
        try:
            response = await client.send_message(
                chat_id=chat["id"], message=prompt, stream=False, agent_id=agent_id
            )
        except Exception as api_error:
            # Handle Codeer API errors (e.g., agent mismatch, timeout, rate limit)
            logger.error(f"Codeer send_message failed: {api_error}")
            return {
                "summary": "Codeer 分析失敗",
                "alerts": [f"⚠️ API 錯誤: {str(api_error)}"],
                "suggestions": ["💡 請檢查 Codeer API 連線或稍後再試"],
            }

        # Parse Codeer response
        # Codeer returns dict with 'content', 'text', or 'message' field
        try:
            # Extract text from response
            if isinstance(response, dict):
                response_text = (
                    response.get("content")
                    or response.get("text")
                    or response.get("message")
                    or str(response)
                )
            else:
                response_text = str(response)

            # Extract JSON from response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "{" in response_text:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_text = response_text[json_start:json_end]
            else:
                # Fallback: treat as plain text
                json_text = response_text

            analysis = json.loads(json_text)

            # Ensure required fields exist
            if "summary" not in analysis:
                analysis["summary"] = "分析結果"
            if "alerts" not in analysis:
                analysis["alerts"] = []
            if "suggestions" not in analysis:
                analysis["suggestions"] = []

            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Codeer response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}")

            # Fallback response
            return {
                "summary": "Codeer 回應解析失敗",
                "alerts": [f"⚠️ 無法解析回應: {str(e)}"],
                "suggestions": ["💡 請檢查 Codeer agent 設定"],
            }

    finally:
        # Always close the client
        await client.close()


@router.post("/analyze", response_model=RealtimeAnalyzeResponse)
async def analyze_transcript(
    request: RealtimeAnalyzeRequest, db: Session = Depends(get_db)
):
    """Analyze realtime counseling transcript with AI supervision.

    Returns summary, alerts, and suggestions for the counselor based on
    the conversation in the past 60 seconds.

    Supports multiple LLM providers: Gemini (default) and Codeer.
    Gemini supports explicit context caching for improved performance.

    This is a demo feature with no authentication required.
    """
    import time

    start_time = time.time()

    try:
        # Convert speakers to dict format for service
        speakers_dict = [
            {"speaker": s.speaker, "text": s.text} for s in request.speakers
        ]

        # Detect parenting keywords and trigger RAG if needed
        rag_sources = []
        rag_context = ""

        if _detect_parenting_keywords(request.transcript):
            logger.info("Parenting keywords detected, triggering RAG search")
            rag_sources = await _search_rag_knowledge(
                transcript=request.transcript, db=db, top_k=3, similarity_threshold=0.7
            )

            # Build RAG context for Gemini prompt
            if rag_sources:
                rag_context_parts = ["\n\n📚 相關親子教養知識庫內容（供參考）：\n"]
                for idx, source in enumerate(rag_sources, 1):
                    rag_context_parts.append(
                        f"[{idx}] {source.title}: {source.content[:200]}..."
                    )
                rag_context = "\n".join(rag_context_parts)

        # Initialize variables
        analysis = {}
        cache_metadata = None
        provider_metadata = None

        # Route to appropriate provider
        if request.provider == "codeer":
            logger.info(
                f"Using Codeer provider for analysis (model: {request.codeer_model})"
            )
            analysis = await _analyze_with_codeer(
                transcript=request.transcript,
                speakers=speakers_dict,
                rag_context=rag_context,
                db=db,
                session_id=request.session_id,
                model=request.codeer_model,
            )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            provider_metadata = ProviderMetadata(
                provider="codeer",
                latency_ms=latency_ms,
                model=f"親子專家 ({request.codeer_model})",
            )

        # Default to Gemini
        else:
            logger.info("Using Gemini provider for analysis")

            # Use cache if enabled and session_id is provided
            if request.use_cache and request.session_id:
                try:
                    logger.info(
                        f"Cache enabled for session {request.session_id}, "
                        f"attempting to get or create cache"
                    )

                    # Get or create cache with accumulated transcript
                    cached_content, is_new = await cache_manager.get_or_create_cache(
                        session_id=request.session_id,
                        system_instruction=CACHE_SYSTEM_INSTRUCTION,
                        accumulated_transcript=request.transcript,
                        ttl_seconds=7200,  # 2 hours
                    )

                    # Check if content is too short for caching
                    if cached_content is None:
                        logger.info(
                            "Content too short for caching, using standard analysis"
                        )
                        analysis = await gemini_service.analyze_realtime_transcript(
                            transcript=request.transcript,
                            speakers=speakers_dict,
                            rag_context=rag_context,
                        )
                        cache_metadata = CacheMetadata(
                            cache_name="",
                            cache_created=False,
                            cached_tokens=0,
                            prompt_tokens=0,
                            message="對話內容較短，尚未啟用 cache（需 >= 1024 tokens）",
                        )
                    else:
                        # Analyze with cache
                        analysis = await gemini_service.analyze_with_cache(
                            cached_content=cached_content,
                            transcript=request.transcript,
                            speakers=speakers_dict,
                            rag_context=rag_context,
                        )

                        # Extract cache metadata from usage_metadata
                        usage_metadata = analysis.get("usage_metadata", {})
                        cache_metadata = CacheMetadata(
                            cache_name=cached_content.name,
                            cache_created=is_new,
                            cached_tokens=usage_metadata.get(
                                "cached_content_token_count", 0
                            ),
                            prompt_tokens=usage_metadata.get("prompt_token_count", 0),
                        )

                        logger.info(
                            f"Cache analysis completed. Cache created: {is_new}, "
                            f"Cached tokens: {cache_metadata.cached_tokens}, "
                            f"Prompt tokens: {cache_metadata.prompt_tokens}"
                        )

                except Exception as cache_error:
                    # Cache failed, fallback to non-cached analysis
                    logger.warning(
                        f"Cache analysis failed, falling back to non-cached: {cache_error}"
                    )
                    analysis = await gemini_service.analyze_realtime_transcript(
                        transcript=request.transcript,
                        speakers=speakers_dict,
                        rag_context=rag_context,
                    )
                    cache_metadata = CacheMetadata(
                        cache_name="",
                        cache_created=False,
                        cached_tokens=0,
                        prompt_tokens=0,
                        error=str(cache_error),
                    )
            else:
                # Cache disabled or no session_id, use standard analysis
                logger.info("Cache disabled or no session_id, using standard analysis")
                analysis = await gemini_service.analyze_realtime_transcript(
                    transcript=request.transcript,
                    speakers=speakers_dict,
                    rag_context=rag_context,
                )

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            provider_metadata = ProviderMetadata(
                provider="gemini", latency_ms=latency_ms, model="gemini-2.5-flash"
            )

        # Build response
        return RealtimeAnalyzeResponse(
            summary=analysis.get("summary", ""),
            alerts=analysis.get("alerts", []),
            suggestions=analysis.get("suggestions", []),
            time_range=request.time_range,
            timestamp=datetime.now(timezone.utc).isoformat(),
            rag_sources=rag_sources,
            cache_metadata=cache_metadata,
            provider_metadata=provider_metadata,
        )
    except Exception as e:
        logger.error(f"Realtime analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
