"""
Sessions Keyword Analysis API
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.counselor import Counselor
from app.schemas.session import KeywordAnalysisRequest, KeywordAnalysisResponse
from app.services.keyword_analysis_service import KeywordAnalysisService
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions - Keywords"])


@router.post("/{session_id}/analyze-keywords", response_model=KeywordAnalysisResponse)
async def analyze_session_keywords(
    session_id: UUID,
    request: KeywordAnalysisRequest,
    db: DBSession = Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> KeywordAnalysisResponse:
    """使用AI分析逐字稿關鍵字（含個案情境）"""
    service = SessionService(db)
    result = service.get_session_with_context(session_id, current_user, tenant_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session, client, case = result

    # Use KeywordAnalysisService for AI-powered analysis
    keyword_service = KeywordAnalysisService(db)
    result_data = await keyword_service.analyze_transcript_keywords(
        session, client, case, request.transcript_segment, current_user.id
    )

    # Build response
    return KeywordAnalysisResponse(
        keywords=result_data.get("keywords", ["分析中"])[:10],
        categories=result_data.get("categories", ["一般"])[:5],
        confidence=result_data.get("confidence", 0.5),
        counselor_insights=result_data.get(
            "counselor_insights", "請根據逐字稿內容判斷。"
        )[:200],
    )
