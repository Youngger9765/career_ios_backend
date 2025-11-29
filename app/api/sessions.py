"""
Sessions (逐字稿) API
"""
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session
from app.repositories.session_repository import SessionRepository
from app.schemas.session import (
    AnalysisLogEntry,
    AnalysisLogsResponse,
    AppendRecordingRequest,
    AppendRecordingResponse,
    KeywordAnalysisRequest,
    KeywordAnalysisResponse,
    ReflectionRequest,
    ReflectionResponse,
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
    SessionTimelineResponse,
    SessionUpdateRequest,
)
from app.services.gemini_service import GeminiService
from app.services.recording_service import RecordingService
from app.services.reflection_service import ReflectionService
from app.services.session_service import SessionService
from app.services.timeline_service import TimelineService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


# Note: All schemas moved to app/schemas/session.py


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: SessionCreateRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionResponse:
    """
    創建逐字稿記錄 (不生成報告)

    Refactored to use SessionService for business logic.
    """
    service = SessionService(db)
    repo = SessionRepository(db)

    try:
        # Create session using service layer
        session = service.create_session(request, current_user, tenant_id)

        # Get related data for response
        case = repo.get_case_by_id(session.case_id, tenant_id)
        client = repo.get_client_by_id(case.client_id)

        return SessionResponse(
            id=session.id,
            client_id=client.id,
            client_name=client.name,
            case_id=case.id,
            session_number=session.session_number,
            session_date=session.session_date,
            name=session.name,
            start_time=session.start_time,
            end_time=session.end_time,
            transcript_text=session.transcript_text,
            duration_minutes=session.duration_minutes,
            notes=session.notes,
            reflection=session.reflection,
            recordings=session.recordings,
            has_report=False,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}",
        )


@router.get("", response_model=SessionListResponse)
def list_sessions(
    client_id: Optional[UUID] = Query(None, description="Filter by client"),
    search: Optional[str] = Query(None, description="Search by client name or code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionListResponse:
    """
    列出會談記錄

    Refactored to use SessionService for business logic.
    """
    service = SessionService(db)

    # Get sessions using service layer - returns (Session, Case, Client, has_report) tuples
    session_data, total = service.list_sessions(
        counselor=current_user,
        tenant_id=tenant_id,
        client_id=client_id,
        search=search,
        skip=skip,
        limit=limit,
    )

    # Build response items from joined data (no N+1 queries)
    items = []
    for session, case, client, has_report in session_data:
        items.append(
            SessionResponse(
                id=session.id,
                client_id=client.id,
                client_name=client.name,
                client_code=client.code,
                case_id=case.id,
                session_number=session.session_number,
                session_date=session.session_date,
                name=session.name,
                start_time=session.start_time,
                end_time=session.end_time,
                transcript_text=session.transcript_text,
                summary=session.summary,
                duration_minutes=session.duration_minutes,
                notes=session.notes,
                reflection=session.reflection,
                recordings=session.recordings,
                has_report=has_report,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
        )

    return SessionListResponse(total=total, items=items)


@router.get("/timeline", response_model=SessionTimelineResponse)
def get_session_timeline(
    client_id: UUID = Query(..., description="個案 UUID"),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionTimelineResponse:
    """
    取得個案的會談歷程時間線

    Refactored to use TimelineService.
    """
    service = TimelineService(db)

    try:
        client, timeline_items = service.get_session_timeline(
            client_id, current_user.id, tenant_id
        )

        return SessionTimelineResponse(
            client_id=client.id,
            client_name=client.name,
            client_code=client.code,
            total_sessions=len(timeline_items),
            sessions=timeline_items,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionResponse:
    """
    取得單一逐字稿

    Refactored to use SessionService.get_session_with_details().
    """
    service = SessionService(db)
    result = service.get_session_with_details(session_id, current_user, tenant_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session, client, case, has_report = result

    return SessionResponse(
        id=session.id,
        client_id=client.id,
        client_name=client.name,
        client_code=client.code,
        case_id=case.id,
        session_number=session.session_number,
        session_date=session.session_date,
        name=session.name,
        start_time=session.start_time,
        end_time=session.end_time,
        transcript_text=session.transcript_text,
        summary=session.summary,
        duration_minutes=session.duration_minutes,
        notes=session.notes,
        reflection=session.reflection,
        recordings=session.recordings,
        has_report=has_report,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: UUID,
    request: SessionUpdateRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionResponse:
    """
    更新逐字稿

    Refactored to use SessionService.update_session() with complex
    session number recalculation logic.
    """
    service = SessionService(db)

    try:
        session, client, case, has_report = service.update_session(
            session_id, request, current_user, tenant_id
        )

        return SessionResponse(
            id=session.id,
            client_id=client.id,
            client_name=client.name,
            client_code=client.code,
            case_id=case.id,
            session_number=session.session_number,
            session_date=session.session_date,
            name=session.name,
            start_time=session.start_time,
            end_time=session.end_time,
            transcript_text=session.transcript_text,
            summary=session.summary,
            duration_minutes=session.duration_minutes,
            notes=session.notes,
            reflection=session.reflection,
            recordings=session.recordings,
            has_report=has_report,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {str(e)}",
        )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
):
    """
    軟刪除逐字稿 (設定 deleted_at 時間戳，如果有關聯報告會失敗)

    Args:
        session_id: Session UUID
        current_user: 當前諮商師
        tenant_id: 租戶 ID
        db: 數據庫 session

    Raises:
        HTTPException: 404 if not found, 400 if has reports, 403 if non-admin tries to delete other's session, 500 if deletion fails
    """
    from datetime import datetime, timezone

    from app.models.counselor import CounselorRole

    # Build query conditions
    conditions = [
        Session.id == session_id,
        Client.tenant_id == tenant_id,
        Session.deleted_at.is_(None),
    ]

    # Non-admin users can only delete their own sessions
    if current_user.role != CounselorRole.ADMIN:
        conditions.append(Client.counselor_id == current_user.id)

    result = db.execute(
        select(Session, Client, Case)
        .join(Case, Session.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(*conditions)
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session, _, case = row

    # 檢查是否有報告
    has_report_result = db.execute(
        select(func.count()).select_from(
            select(1)
            .where(Session.id == session.id)
            .where(Session.reports.any())
            .subquery()
        )
    )
    has_report = (has_report_result.scalar() or 0) > 0

    if has_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete session with associated reports",
        )

    try:
        # Soft delete: set deleted_at timestamp
        session.deleted_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )


# Reflection CRUD Endpoints
@router.get("/{session_id}/reflection", response_model=ReflectionResponse)
def get_reflection(
    session_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> ReflectionResponse:
    """
    取得會談的諮商師反思

    Args:
        session_id: Session UUID
        current_user: 當前諮商師
        tenant_id: 租戶 ID
        db: 數據庫 session

    Returns:
        反思內容

    Raises:
        HTTPException: 404 if not found
    """
    service = ReflectionService(db)
    try:
        reflection = service.get_reflection(session_id, current_user.id, tenant_id)
        # Get session to get updated_at timestamp
        repo = SessionRepository(db)
        session = repo.get_by_id(session_id)

        return ReflectionResponse(
            session_id=session_id,
            reflection=reflection,
            updated_at=session.updated_at or session.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )


@router.put("/{session_id}/reflection", response_model=ReflectionResponse)
def update_reflection(
    session_id: UUID,
    reflection_data: ReflectionRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> ReflectionResponse:
    """
    更新或建立會談的諮商師反思

    Args:
        session_id: Session UUID
        reflection_data: 反思內容
        current_user: 當前諮商師
        tenant_id: 租戶 ID
        db: 數據庫 session

    Returns:
        更新後的反思內容

    Raises:
        HTTPException: 404 if session not found, 500 if update fails
    """
    service = ReflectionService(db)
    try:
        reflection = service.update_reflection(
            session_id, reflection_data.reflection, current_user.id, tenant_id
        )
        # Get session to get updated_at timestamp
        repo = SessionRepository(db)
        session = repo.get_by_id(session_id)

        return ReflectionResponse(
            session_id=session_id,
            reflection=reflection,
            updated_at=session.updated_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update reflection: {str(e)}",
        )


# Recording Append Endpoint
@router.post("/{session_id}/recordings/append", response_model=AppendRecordingResponse)
def append_recording(
    session_id: UUID,
    request: AppendRecordingRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> AppendRecordingResponse:
    """
    在 session 中 append 新的 recording segment（iOS 友善版本）

    自動計算 segment_number，不需要 iOS 提供
    自動重新聚合 transcript_text

    Args:
        session_id: Session UUID
        request: 錄音片段資料（不含 segment_number）
        current_user: 當前諮商師
        tenant_id: 租戶 ID
        db: 數據庫 session

    Returns:
        更新後的 session 資訊

    Raises:
        HTTPException: 404 if session not found, 500 if append fails

    Example:
        POST /api/v1/sessions/{session_id}/recordings/append
        {
            "start_time": "2025-01-15 10:00",
            "end_time": "2025-01-15 10:30",
            "duration_seconds": 1800,
            "transcript_text": "今天我們聊到...",
            "transcript_sanitized": "今天我們聊到..."
        }
    """
    service = RecordingService(db)
    try:
        session, new_recording, total_recordings = service.append_recording(
            session_id, request, current_user.id, tenant_id
        )

        return AppendRecordingResponse(
            session_id=session.id,
            recording_added=new_recording,
            total_recordings=total_recordings,
            transcript_text=session.transcript_text,
            updated_at=session.updated_at or session.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to append recording: {str(e)}",
        )


# RESTful Keyword Analysis Endpoint
@router.post(
    "/{session_id}/analyze-keywords",
    response_model=KeywordAnalysisResponse,
    summary="Analyze transcript keywords using session context",
    description="Extract keywords from transcript segment using AI with full context from session -> case -> client. Includes counselor insights.",
)
async def analyze_session_keywords(
    session_id: UUID,
    request: KeywordAnalysisRequest,
    db: DBSession = Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> KeywordAnalysisResponse:
    """
    Analyze transcript segment for keywords using session context (RESTful).

    This endpoint automatically fetches session, case, and client information
    to provide context-aware keyword analysis.

    Args:
        session_id: Session UUID
        request: Keyword analysis request with transcript segment
        db: Database session
        current_user: Authenticated user
        tenant_id: Tenant ID

    Returns:
        KeywordAnalysisResponse with keywords, categories, confidence, and counselor insights

    Raises:
        HTTPException: 404 if session not found
    """
    # Fetch session with case and client through relationships
    result = db.execute(
        select(Session, Client, Case)
        .join(Case, Session.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(
            Session.id == session_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
            Session.deleted_at.is_(None),
            Case.deleted_at.is_(None),
            Client.deleted_at.is_(None),
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session, client, case = row

    # Use the RAG-based keyword analysis service for fast response
    # keyword_service = get_keyword_analysis_service()  # Reserved for future RAG implementation

    # Convert sync DB session to async for RAG operations
    # Note: For now we'll use the synchronous Gemini service directly
    # In production, we should use async database session throughout
    try:
        # For now, fall back to direct AI analysis without RAG
        # (RAG requires async DB session which needs infrastructure changes)
        # This still provides fast response by using optimized prompting

        # Build AI prompt context from session -> case -> client
        context_parts = []

        # Add client information
        client_info = f"案主資訊: {client.name}"
        if client.current_status:
            client_info += f", 當前狀況: {client.current_status}"
        if client.notes:
            client_info += f", 備註: {client.notes}"
        context_parts.append(client_info)

        # Add case information
        case_info = f"案例目標: {case.goals or '未設定'}"
        if case.problem_description:
            case_info += f", 問題敘述: {case.problem_description}"
        context_parts.append(case_info)

        # Add session information
        session_info = f"會談次數: 第 {session.session_number} 次"
        if session.notes:
            session_info += f", 會談備註: {session.notes}"
        context_parts.append(session_info)

        # Build complete prompt (optimized for speed)
        context_str = "\n".join(context_parts)

        # Use shorter, more focused prompt for faster response
        prompt = f"""快速分析以下逐字稿，提取關鍵詞和洞見。

背景：
{context_str}

逐字稿：
{request.transcript_segment[:500]}  # Limit to 500 chars for speed

JSON回應（精簡）：
{{
    "keywords": ["詞1", "詞2", "詞3", "詞4", "詞5"],
    "categories": ["類別1", "類別2", "類別3"],
    "confidence": 0.85,
    "counselor_insights": "簡短洞見（50字內）"
}}"""

        # Call Gemini with lower temperature for consistency
        gemini_service = GeminiService()
        ai_response = await gemini_service.generate_text(
            prompt, temperature=0.3, response_format={"type": "json_object"}
        )

        # Parse AI response
        if isinstance(ai_response, str):
            try:
                json_start = ai_response.find("{")
                json_end = ai_response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = ai_response[json_start:json_end]
                    result_data = json.loads(json_str)
                else:
                    # Quick fallback based on common patterns
                    result_data = {
                        "keywords": ["情緒", "壓力", "工作", "關係", "目標"],
                        "categories": ["情緒管理", "職涯發展"],
                        "confidence": 0.7,
                        "counselor_insights": "關注案主情緒變化與職涯困擾。",
                    }
            except json.JSONDecodeError:
                # Ultra-fast fallback
                result_data = {
                    "keywords": ["探索中", "情緒", "發展"],
                    "categories": ["一般諮商"],
                    "confidence": 0.5,
                    "counselor_insights": "持續觀察案主狀態。",
                }
        else:
            result_data = ai_response

        # Build response
        response = KeywordAnalysisResponse(
            keywords=result_data.get("keywords", ["分析中"])[:10],  # Max 10 keywords
            categories=result_data.get("categories", ["一般"])[:5],  # Max 5 categories
            confidence=result_data.get("confidence", 0.5),
            counselor_insights=result_data.get(
                "counselor_insights", "請根據逐字稿內容判斷。"
            )[:200],  # Max 200 chars
        )

        # Save analysis log to session
        from datetime import datetime, timezone

        analysis_log_entry = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "transcript_segment": request.transcript_segment[
                :200
            ],  # Save first 200 chars
            "keywords": response.keywords,
            "categories": response.categories,
            "confidence": response.confidence,
            "counselor_insights": response.counselor_insights,
            "counselor_id": str(current_user.id),
        }

        # Append to analysis_logs
        if session.analysis_logs is None:
            session.analysis_logs = []
        session.analysis_logs.append(analysis_log_entry)

        # Mark as modified for SQLAlchemy to detect changes
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(session, "analysis_logs")

        # Commit to database
        db.commit()
        db.refresh(session)

        return response

    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        # Intelligent fallback: Extract keywords using simple rules
        transcript = request.transcript_segment[:500]

        # Common counseling keywords (情緒、關係、職涯、壓力等)
        emotion_keywords = [
            "焦慮",
            "壓力",
            "緊張",
            "難過",
            "開心",
            "害怕",
            "生氣",
            "沮喪",
            "無助",
            "迷惘",
            "困擾",
            "擔心",
            "自卑",
        ]
        work_keywords = [
            "工作",
            "主管",
            "同事",
            "公司",
            "職涯",
            "轉職",
            "離職",
            "上班",
            "加班",
            "業績",
            "升遷",
        ]
        relationship_keywords = [
            "家人",
            "父母",
            "伴侶",
            "朋友",
            "關係",
            "溝通",
            "衝突",
            "相處",
            "家庭",
        ]
        development_keywords = [
            "目標",
            "方向",
            "成就",
            "發展",
            "規劃",
            "未來",
            "改變",
            "學習",
            "成長",
        ]

        # Extract keywords found in transcript
        found_keywords = []
        categories = set()

        for word in emotion_keywords:
            if word in transcript:
                found_keywords.append(word)
                categories.add("情緒管理")

        for word in work_keywords:
            if word in transcript:
                found_keywords.append(word)
                categories.add("職涯發展")

        for word in relationship_keywords:
            if word in transcript:
                found_keywords.append(word)
                categories.add("人際關係")

        for word in development_keywords:
            if word in transcript:
                found_keywords.append(word)
                categories.add("自我探索")

        # If no keywords found, use general ones
        if not found_keywords:
            found_keywords = ["探索中", "諮商進行"]
            categories = {"一般諮商"}

        # Generate simple insights based on found keywords
        if "焦慮" in found_keywords or "壓力" in found_keywords:
            insights = "案主表達情緒困擾，建議關注壓力來源及因應策略。"
        elif "工作" in found_keywords or "職涯" in found_keywords:
            insights = "案主提及職涯議題，可探索工作價值觀與發展方向。"
        elif any(k in found_keywords for k in relationship_keywords):
            insights = "案主談及人際關係，建議探索互動模式與溝通方式。"
        else:
            insights = f"案主提及 {', '.join(found_keywords[:3])}，持續關注案主需求。"

        # Build fallback response
        response = KeywordAnalysisResponse(
            keywords=found_keywords[:10],  # Max 10
            categories=list(categories)[:5],  # Max 5
            confidence=0.6,  # Rule-based has moderate confidence
            counselor_insights=insights,
        )

        # Save analysis log to session (even for fallback)
        from datetime import datetime, timezone

        analysis_log_entry = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "transcript_segment": request.transcript_segment[:200],
            "keywords": response.keywords,
            "categories": response.categories,
            "confidence": response.confidence,
            "counselor_insights": response.counselor_insights,
            "counselor_id": str(current_user.id),
            "fallback": True,  # Mark as fallback analysis
        }

        # Append to analysis_logs
        if session.analysis_logs is None:
            session.analysis_logs = []
        session.analysis_logs.append(analysis_log_entry)

        # Mark as modified for SQLAlchemy to detect changes
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(session, "analysis_logs")

        # Commit to database
        db.commit()
        db.refresh(session)

        return response


@router.get(
    "/{session_id}/analysis-logs",
    response_model=AnalysisLogsResponse,
    summary="Get analysis logs for a session",
    description="Retrieve all keyword analysis logs for a session, ordered from oldest to newest.",
)
def get_analysis_logs(
    session_id: UUID,
    db: DBSession = Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> AnalysisLogsResponse:
    """
    Get all analysis logs for a session.

    Returns analysis logs in chronological order (oldest first).

    Args:
        session_id: Session UUID
        db: Database session
        current_user: Authenticated user
        tenant_id: Tenant ID

    Returns:
        AnalysisLogsResponse with all logs

    Raises:
        HTTPException: 404 if session not found
    """
    # Fetch session with authorization check
    result = db.execute(
        select(Session, Client, Case)
        .join(Case, Session.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(
            Session.id == session_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
            Session.deleted_at.is_(None),
            Case.deleted_at.is_(None),
            Client.deleted_at.is_(None),
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        )

    session = row[0]

    # Get analysis_logs (defaults to empty list if None)
    logs_data = session.analysis_logs or []

    # Convert to response format with log indices
    log_entries = [
        AnalysisLogEntry(
            log_index=idx,
            analyzed_at=log.get("analyzed_at", ""),
            transcript_segment=log.get("transcript_segment", ""),
            keywords=log.get("keywords", []),
            categories=log.get("categories", []),
            confidence=log.get("confidence", 0.0),
            counselor_insights=log.get("counselor_insights", ""),
            counselor_id=log.get("counselor_id", ""),
            fallback=log.get("fallback", False),
        )
        for idx, log in enumerate(logs_data)
    ]

    return AnalysisLogsResponse(
        session_id=session.id,
        total_logs=len(log_entries),
        logs=log_entries,
    )


@router.delete(
    "/{session_id}/analysis-logs/{log_index}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specific analysis log entry",
    description="Delete an analysis log entry by its index (0-based).",
)
def delete_analysis_log(
    session_id: UUID,
    log_index: int,
    db: DBSession = Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    Delete a specific analysis log entry.

    Args:
        session_id: Session UUID
        log_index: Index of log to delete (0-based)
        db: Database session
        current_user: Authenticated user
        tenant_id: Tenant ID

    Raises:
        HTTPException: 404 if session or log not found, 400 if invalid index
    """
    # Fetch session with authorization check
    result = db.execute(
        select(Session, Client, Case)
        .join(Case, Session.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(
            Session.id == session_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
            Session.deleted_at.is_(None),
            Case.deleted_at.is_(None),
            Client.deleted_at.is_(None),
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        )

    session = row[0]

    # Get analysis_logs
    logs_data = session.analysis_logs or []

    # Validate index
    if log_index < 0 or log_index >= len(logs_data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid log index: {log_index}. Valid range: 0-{len(logs_data)-1}",
        )

    # Remove the log entry
    logs_data.pop(log_index)

    # Update session
    session.analysis_logs = logs_data

    # Mark as modified for SQLAlchemy to detect changes
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(session, "analysis_logs")

    db.commit()

    return None  # 204 No Content
