"""
Realtime STT Counseling API
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.realtime import RealtimeAnalyzeRequest, RealtimeAnalyzeResponse
from app.services.gemini_service import GeminiService
from app.services.openai_service import OpenAIService
from app.services.rag_chat_service import RAGChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["Realtime Counseling"])

# Initialize services
gemini_service = GeminiService()
openai_service = OpenAIService()

# Career-related keywords that trigger RAG search
CAREER_KEYWORDS = [
    "轉職",
    "履歷",
    "面試",
    "職涯",
    "職涯規劃",
    "離職",
    "求職",
    "工作",
    "主管",
    "同事",
    "公司",
    "升遷",
    "加薪",
    "跳槽",
    "生涯",
    "興趣",
    "熱情",
    "目標",
    "發展",
    "規劃",
    "能力",
    "優勢",
    "專長",
    "技能",
    "價值觀",
]


def _detect_career_keywords(transcript: str) -> bool:
    """Detect if transcript contains career-related keywords.

    Args:
        transcript: The transcript text

    Returns:
        True if career keywords detected, False otherwise
    """
    transcript_lower = transcript.lower()
    for keyword in CAREER_KEYWORDS:
        if keyword in transcript_lower:
            logger.info(f"Career keyword detected: {keyword}")
            return True
    return False


async def _search_rag_knowledge(
    transcript: str, db: Session, top_k: int = 3, similarity_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """Search RAG knowledge base for relevant content.

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

        # Search similar chunks
        rows = await rag_service.search_similar_chunks(
            query_embedding=query_embedding,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        # Build RAG sources response
        rag_sources = []
        for row in rows:
            rag_sources.append(
                {
                    "title": row.document_title,
                    "content": row.text[:300],  # Truncate to 300 chars
                    "score": round(float(row.similarity_score), 2),
                }
            )

        logger.info(f"RAG search found {len(rag_sources)} relevant sources")
        return rag_sources

    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        # Return empty list on error (fallback)
        return []


@router.post("/analyze", response_model=RealtimeAnalyzeResponse)
async def analyze_transcript(
    request: RealtimeAnalyzeRequest, db: Session = Depends(get_db)
):
    """Analyze realtime counseling transcript with AI supervision.

    Returns summary, alerts, and suggestions for the counselor based on
    the conversation in the past 60 seconds.

    This is a demo feature with no authentication required.
    """
    try:
        # Convert speakers to dict format for service
        speakers_dict = [
            {"speaker": s.speaker, "text": s.text} for s in request.speakers
        ]

        # Detect career keywords and trigger RAG if needed
        rag_sources = []
        rag_context = ""

        if _detect_career_keywords(request.transcript):
            logger.info("Career keywords detected, triggering RAG search")
            rag_sources = await _search_rag_knowledge(
                transcript=request.transcript, db=db, top_k=3, similarity_threshold=0.7
            )

            # Build RAG context for Gemini prompt
            if rag_sources:
                rag_context_parts = ["\n\n📚 相關職涯知識庫內容（供參考）：\n"]
                for idx, source in enumerate(rag_sources, 1):
                    rag_context_parts.append(
                        f"[{idx}] {source['title']}: {source['content'][:200]}..."
                    )
                rag_context = "\n".join(rag_context_parts)

        # Call Gemini service for analysis (with optional RAG context)
        analysis = await gemini_service.analyze_realtime_transcript(
            transcript=request.transcript,
            speakers=speakers_dict,
            rag_context=rag_context,  # Pass RAG context to Gemini
        )

        # Build response
        return RealtimeAnalyzeResponse(
            summary=analysis.get("summary", ""),
            alerts=analysis.get("alerts", []),
            suggestions=analysis.get("suggestions", []),
            time_range=request.time_range,
            timestamp=datetime.now(timezone.utc).isoformat(),
            rag_sources=rag_sources,
        )
    except Exception as e:
        logger.error(f"Realtime analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
