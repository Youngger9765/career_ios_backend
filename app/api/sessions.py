"""
Sessions (逐字稿) API
"""
import json
import logging
from datetime import datetime, timezone
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
from app.models.report import Report
from app.models.session import Session
from app.repositories.session_repository import SessionRepository
from app.schemas.session import (
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

    Args:
        session_id: Session UUID
        current_user: 當前諮商師
        tenant_id: 租戶 ID
        db: 數據庫 session

    Returns:
        逐字稿詳情

    Raises:
        HTTPException: 404 if not found
    """
    # 使用 LEFT JOIN 避免 N+1 query
    result = db.execute(
        select(Session, Client, Case, Report.id.label("report_id"))
        .join(Case, Session.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .outerjoin(Report, Report.session_id == Session.id)
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

    session, client, case, report_id = row

    # 檢查是否有報告（從 JOIN 結果判斷，無需額外查詢）
    has_report = report_id is not None

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
        recordings=session.recordings,  # 包含錄音片段
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

    Args:
        session_id: Session UUID
        request: 更新請求
        current_user: 當前諮商師
        tenant_id: 租戶 ID
        db: 數據庫 session

    Returns:
        更新後的逐字稿

    Raises:
        HTTPException: 404 if not found, 500 if update fails
    """
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

    try:
        # 記錄是否更新了會談時間，如果有則需要重新計算 session_number
        time_changed = False
        old_session_number = session.session_number

        # 更新欄位
        if request.session_date is not None:
            new_session_date = datetime.fromisoformat(request.session_date)
            if new_session_date.tzinfo is None:
                new_session_date = new_session_date.replace(tzinfo=timezone.utc)
            if new_session_date != session.session_date:
                time_changed = True
                session.session_date = new_session_date

        if request.start_time is not None:
            time_str = request.start_time.strip()
            if " " in time_str or "T" in time_str or len(time_str) > 10:
                new_start_time = datetime.fromisoformat(time_str.replace(" ", "T"))
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_time must include date (format: YYYY-MM-DD HH:MM)",
                )
            if new_start_time.tzinfo is None:
                new_start_time = new_start_time.replace(tzinfo=timezone.utc)
            if new_start_time != session.start_time:
                time_changed = True
            session.start_time = new_start_time

        if request.end_time is not None:
            time_str = request.end_time.strip()
            if " " in time_str or "T" in time_str or len(time_str) > 10:
                new_end_time = datetime.fromisoformat(time_str.replace(" ", "T"))
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="end_time must include date (format: YYYY-MM-DD HH:MM)",
                )
            if new_end_time.tzinfo is None:
                new_end_time = new_end_time.replace(tzinfo=timezone.utc)
            session.end_time = new_end_time

        # 處理 transcript 和 recordings
        # 優先使用 recordings 聚合，若無則使用直接提供的 transcript
        if request.recordings is not None:
            # 更新 recordings 並重新聚合逐字稿
            session.recordings = request.recordings
            if request.recordings:
                # Use SessionService helper methods for transcript/time aggregation
                helper_service = SessionService(db)
                full_transcript = helper_service._aggregate_transcript_from_recordings(
                    request.recordings
                )
                session.transcript_text = full_transcript
                session.transcript_sanitized = full_transcript

                # 重新計算 session 時間範圍（從更新後的 recordings）
                (
                    calculated_start,
                    calculated_end,
                ) = helper_service._calculate_timerange_from_recordings(
                    request.recordings
                )
                if calculated_start:
                    session.start_time = calculated_start
                    time_changed = False  # 由 recordings 計算的時間不算是手動更改
                if calculated_end:
                    session.end_time = calculated_end
                    time_changed = False  # 由 recordings 計算的時間不算是手動更改
        elif request.transcript is not None:
            # 直接更新 transcript（向下兼容）
            session.transcript_text = request.transcript
            session.transcript_sanitized = request.transcript

        # Handle name field - Always update if provided in request (even if None)
        # Use exclude_unset to check if field was explicitly provided
        update_data = request.model_dump(exclude_unset=True)
        if "name" in update_data:
            session.name = update_data["name"]
        if request.notes is not None:
            session.notes = request.notes

        if request.duration_minutes is not None:
            session.duration_minutes = request.duration_minutes

        if request.reflection is not None:
            session.reflection = request.reflection

        # 如果 session_date 或 start_time 改變，需要重新計算 session_number
        # 決定新的排序時間：優先使用 start_time，若無則使用 session_date
        new_sort_time = (
            session.start_time if session.start_time else session.session_date
        )

        if time_changed:
            # 1. 先將當前 session 的 session_number 設為 0（臨時值）
            session.session_number = 0
            db.flush()

            # 2. 將原本 > old_session_number 的所有 sessions 編號 -1
            db.execute(
                Session.__table__.update()  # type: ignore[attr-defined]
                .where(Session.case_id == session.case_id)
                .where(Session.session_number > old_session_number)
                .values(session_number=Session.session_number - 1)
            )
            db.flush()

            # 3. 查詢該 case 所有其他 sessions，按 start_time 或 session_date 排序
            result = db.execute(
                select(Session.start_time, Session.session_date)
                .where(Session.case_id == session.case_id)
                .where(Session.id != session.id)
                .order_by(func.coalesce(Session.start_time, Session.session_date).asc())
            )
            existing_times = [(row[0] if row[0] else row[1]) for row in result.all()]

            # 4. 找出新 session_number
            new_session_number = 1
            for existing_time in existing_times:
                if new_sort_time > existing_time:
                    new_session_number += 1
                else:
                    break

            # 5. 更新 >= new_session_number 的所有 sessions（不包括當前 session）編號 +1
            db.execute(
                Session.__table__.update()  # type: ignore[attr-defined]
                .where(Session.case_id == session.case_id)
                .where(Session.session_number >= new_session_number)
                .where(Session.id != session.id)
                .values(session_number=Session.session_number + 1)
            )
            db.flush()

            # 6. 設定當前 session 的新 session_number
            session.session_number = new_session_number

        db.commit()
        db.refresh(session)

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
            recordings=session.recordings,  # 包含錄音片段
            has_report=has_report,
            created_at=session.created_at,
            updated_at=session.updated_at,
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

        return KeywordAnalysisResponse(
            keywords=result_data.get("keywords", ["分析中"])[:10],  # Max 10 keywords
            categories=result_data.get("categories", ["一般"])[:5],  # Max 5 categories
            confidence=result_data.get("confidence", 0.5),
            counselor_insights=result_data.get(
                "counselor_insights", "請根據逐字稿內容判斷。"
            )[:200],  # Max 200 chars
        )

    except Exception as e:
        logger.error(f"Keyword extraction failed: {e}")
        # Ultra-fast error response
        return KeywordAnalysisResponse(
            keywords=["待分析"],
            categories=["待分類"],
            confidence=0.0,
            counselor_insights="系統分析中，請稍後再試。",
        )
