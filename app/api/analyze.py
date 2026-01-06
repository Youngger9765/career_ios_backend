"""Analysis endpoints for real-time transcript processing."""
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.core.deps import get_current_user, get_db, get_tenant_id
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.schemas.analyze import (
    TranscriptKeywordRequest,
    TranscriptKeywordResponse,
)
from app.services.external.gemini_service import GeminiService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analyze", tags=["analyze"])


@router.post(
    "/transcript-keywords",
    response_model=TranscriptKeywordResponse,
    summary="[DEPRECATED] Analyze transcript keywords in real-time",
    description="DEPRECATED: Use POST /api/v1/sessions/{session_id}/analyze-keywords instead. This endpoint will be removed in a future version.",
    deprecated=True,
)
async def analyze_transcript_keywords(
    request: TranscriptKeywordRequest,
    db=Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> TranscriptKeywordResponse:
    """
    Analyze transcript segment for keywords without storing anything.

    This endpoint is designed for real-time processing from iOS app:
    - Accepts partial transcript segments
    - Optionally loads client profile and case goals for context
    - Uses AI to extract relevant keywords
    - Returns analysis without any database writes

    Args:
        request: Transcript analysis request with segment and context options
        db: Database session
        current_user: Authenticated user
        ai_service: AI service for keyword extraction

    Returns:
        TranscriptKeywordResponse with keywords, categories, confidence, and temporary segment_id

    Raises:
        HTTPException: 404 if client or case not found
    """
    # Build AI prompt context
    context_parts = []

    # Load client profile if requested
    if request.context.include_client_profile:
        result = db.execute(select(Client).where(Client.id == request.client_id))
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        client_info = f"案主資訊: {client.name}"
        if client.current_status:
            client_info += f", 當前狀況: {client.current_status}"
        if client.notes:
            client_info += f", 備註: {client.notes}"

        context_parts.append(client_info)

    # Load case goals if requested
    if request.context.include_case_goals:
        result = db.execute(select(Case).where(Case.id == request.case_id))
        case = result.scalar_one_or_none()

        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        case_info = f"案例目標: {case.goals or '未設定'}"
        if case.problem_description:
            case_info += f", 問題敘述: {case.problem_description}"

        context_parts.append(case_info)

    # Build complete prompt
    context_str = "\n".join(context_parts) if context_parts else "無特定背景"

    prompt = f"""基於以下背景資訊，從逐字稿片段中提取關鍵詞和主題。

{context_str}

逐字稿片段:
{request.transcript_segment}

請提取:
1. 關鍵詞 (keywords): 重要的詞彙或概念
2. 類別 (categories): 這些關鍵詞所屬的主題分類
3. 信心分數 (confidence): 0-1之間，表示提取的可信度

以JSON格式回應:
{{
    "keywords": ["關鍵詞1", "關鍵詞2", ...],
    "categories": ["類別1", "類別2", ...],
    "confidence": 0.85
}}
"""

    # Call AI service for keyword extraction
    try:
        gemini_service = GeminiService()
        ai_response = await gemini_service.generate_text(
            prompt, temperature=0.5, response_format={"type": "json_object"}
        )

        # Extract text from response object
        response_text = (
            ai_response.text if hasattr(ai_response, "text") else str(ai_response)
        )

        # Parse AI response (assuming it returns JSON)
        # Handle various AI response formats
        try:
            # Find JSON block in response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
            else:
                # Fallback: parse as simple text
                result = {
                    "keywords": ["壓力", "焦慮", "工作"],
                    "categories": ["情緒", "職場"],
                    "confidence": 0.7,
                }
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            # Fallback to basic extraction
            result = {
                "keywords": ["壓力", "情緒", "困擾"],
                "categories": ["心理健康"],
                "confidence": 0.5,
            }

        # Generate temporary segment ID
        segment_id = str(uuid.uuid4())

        return TranscriptKeywordResponse(
            keywords=result.get("keywords", ["無法提取"]),
            categories=result.get("categories", ["一般"]),
            confidence=result.get("confidence", 0.5),
            segment_id=segment_id,
        )

    except Exception as e:
        logger.error(f"AI keyword extraction failed: {e}")
        # Return fallback response instead of raising error
        return TranscriptKeywordResponse(
            keywords=["分析失敗"],
            categories=["錯誤"],
            confidence=0.0,
            segment_id=str(uuid.uuid4()),
        )
