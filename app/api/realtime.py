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
    RAGSource,
    RealtimeAnalyzeRequest,
    RealtimeAnalyzeResponse,
)
from app.services.gemini_service import GeminiService
from app.services.openai_service import OpenAIService
from app.services.rag_chat_service import RAGChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["Realtime Counseling"])

# Initialize services
gemini_service = GeminiService()
openai_service = OpenAIService()

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
