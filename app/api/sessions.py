"""
Sessions (逐字稿) API
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.report import Report, ReportStatus
from app.models.session import Session

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


# Helper functions
def aggregate_transcript_from_recordings(recordings: list) -> str:
    """
    從 recordings 聚合完整逐字稿

    Args:
        recordings: 錄音片段列表，每個包含 transcript_text

    Returns:
        聚合後的完整逐字稿
    """
    if not recordings:
        return ""

    # 按 segment_number 排序（如果有的話）
    sorted_recordings = sorted(recordings, key=lambda r: r.get("segment_number", 0))

    # 聚合所有 transcript_text
    transcripts = [
        r.get("transcript_text", "")
        for r in sorted_recordings
        if r.get("transcript_text")
    ]

    # 用兩個換行符分隔不同段落
    return "\n\n".join(transcripts)


# Schemas
class RecordingSegment(BaseModel):
    """錄音片段"""

    segment_number: int
    start_time: str
    end_time: str
    duration_seconds: int
    transcript_text: str
    transcript_sanitized: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "segment_number": 1,
                    "start_time": "2025-01-15 10:00",
                    "end_time": "2025-01-15 10:30",
                    "duration_seconds": 1800,
                    "transcript_text": "諮商師：今天想聊什麼？\n個案：我最近對未來感到很迷惘...",
                    "transcript_sanitized": "諮商師：今天想聊什麼？\n個案：我最近對未來感到很迷惘...",
                }
            ]
        }
    }


class AppendRecordingRequest(BaseModel):
    """
    Append 錄音片段請求（iOS 友善版本）

    不需要提供 segment_number，系統會自動計算
    """

    start_time: str  # ISO format: YYYY-MM-DD HH:MM or YYYY-MM-DDTHH:MM:SS
    end_time: str  # ISO format: YYYY-MM-DD HH:MM or YYYY-MM-DDTHH:MM:SS
    duration_seconds: int
    transcript_text: str
    transcript_sanitized: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_time": "2025-01-15 10:00",
                    "end_time": "2025-01-15 10:30",
                    "duration_seconds": 1800,
                    "transcript_text": "諮商師：今天想聊什麼？\n個案：我最近對未來感到很迷惘，不知道該選擇什麼工作...",
                    "transcript_sanitized": "諮商師：今天想聊什麼？\n個案：我最近對未來感到很迷惘，不知道該選擇什麼工作...",
                }
            ]
        }
    }


class SessionCreateRequest(BaseModel):
    """
    創建會談記錄請求

    - transcript 與 recordings 二選一：
      - transcript: 直接提供完整逐字稿（傳統方式）
      - recordings: 提供分段錄音逐字稿（推薦），系統會自動聚合成 transcript_text
    """

    case_id: UUID
    session_date: str  # YYYY-MM-DD
    start_time: Optional[str] = None  # YYYY-MM-DD HH:MM
    end_time: Optional[str] = None  # YYYY-MM-DD HH:MM
    transcript: Optional[str] = None  # 與 recordings 二選一
    duration_minutes: Optional[int] = None  # 保留向下兼容
    notes: Optional[str] = None
    reflection: Optional[dict] = None  # 諮商師反思（JSON 格式，彈性支援不同租戶需求）
    recordings: Optional[
        list[RecordingSegment]
    ] = None  # 錄音片段（推薦），系統會自動聚合成 transcript_text

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "case_id": "123e4567-e89b-12d3-a456-426614174000",
                    "session_date": "2025-01-15",
                    "start_time": "2025-01-15 10:00",
                    "end_time": "2025-01-15 11:30",
                    "notes": "個案對職涯選擇表現出積極態度",
                    "recordings": [
                        {
                            "segment_number": 1,
                            "start_time": "2025-01-15 10:00",
                            "end_time": "2025-01-15 10:30",
                            "duration_seconds": 1800,
                            "transcript_text": "諮商師：今天想聊什麼？\n個案：我最近對未來感到很迷惘...",
                            "transcript_sanitized": "諮商師：今天想聊什麼？\n個案：我最近對未來感到很迷惘...",
                        },
                        {
                            "segment_number": 2,
                            "start_time": "2025-01-15 10:30",
                            "end_time": "2025-01-15 11:00",
                            "duration_seconds": 1800,
                            "transcript_text": "諮商師：那我們來探索一下你的興趣...\n個案：我對科技和教育都有興趣...",
                            "transcript_sanitized": "諮商師：那我們來探索一下你的興趣...\n個案：我對科技和教育都有興趣...",
                        },
                    ],
                }
            ]
        }
    }


class SessionUpdateRequest(BaseModel):
    """
    更新會談記錄請求

    - 更新時 transcript 與 recordings 二選一（與創建邏輯相同）
    """

    session_date: Optional[str] = None  # YYYY-MM-DD
    start_time: Optional[str] = None  # YYYY-MM-DD HH:MM
    end_time: Optional[str] = None  # YYYY-MM-DD HH:MM
    transcript: Optional[str] = None
    notes: Optional[str] = None
    duration_minutes: Optional[int] = None  # 保留向下兼容
    reflection: Optional[dict] = None  # 諮商師反思
    recordings: Optional[
        list[RecordingSegment]
    ] = None  # 錄音片段（更新時也支援從 recordings 聚合）


class SessionResponse(BaseModel):
    """
    會談記錄響應

    - transcript_text: 完整逐字稿（若提供 recordings 則自動聚合）
    - recordings: 原始錄音片段數組
    """

    id: UUID
    client_id: UUID
    client_name: Optional[str] = None  # 個案姓名
    client_code: Optional[str] = None  # 個案代碼
    case_id: UUID
    session_number: int
    session_date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    transcript_text: Optional[str] = None  # 完整逐字稿（自動從 recordings 聚合）
    summary: Optional[str] = None  # 會談摘要（AI 生成）
    duration_minutes: Optional[int]
    notes: Optional[str]
    reflection: Optional[dict] = None  # 諮商師反思（人類撰寫）
    recordings: Optional[list[RecordingSegment]] = None  # 錄音片段數組
    has_report: bool  # 是否已生成報告
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """會談記錄列表響應"""

    total: int
    items: list[SessionResponse]


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: SessionCreateRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionResponse:
    """
    創建逐字稿記錄 (不生成報告)

    Args:
        request: 逐字稿創建請求
        current_user: 當前諮商師
        tenant_id: 租戶 ID
        db: 數據庫 session

    Returns:
        創建的逐字稿記錄

    Raises:
        HTTPException: 404 if client not found, 500 if creation fails
    """
    # 驗證 Case 存在且屬於當前租戶
    result = db.execute(
        select(Case).where(
            Case.id == request.case_id,
            Case.tenant_id == tenant_id,
            Case.deleted_at.is_(None),
        )
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found or access denied",
        )

    try:
        # Parse start_time and end_time if provided
        start_time = None
        end_time = None
        if request.start_time:
            # Handle both "YYYY-MM-DD HH:MM" and "HH:MM" formats
            time_str = request.start_time.strip()
            if " " in time_str or "T" in time_str or len(time_str) > 10:
                # Full datetime string
                start_time = datetime.fromisoformat(time_str.replace(" ", "T"))
            else:
                # Only time provided, combine with session_date
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_time must include date (format: YYYY-MM-DD HH:MM)",
                )
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)

        if request.end_time:
            # Handle both "YYYY-MM-DD HH:MM" and "HH:MM" formats
            time_str = request.end_time.strip()
            if " " in time_str or "T" in time_str or len(time_str) > 10:
                # Full datetime string
                end_time = datetime.fromisoformat(time_str.replace(" ", "T"))
            else:
                # Only time provided, combine with session_date
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="end_time must include date (format: YYYY-MM-DD HH:MM)",
                )
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)

        # Parse session_date
        new_session_date = datetime.fromisoformat(request.session_date)
        if new_session_date.tzinfo is None:
            new_session_date = new_session_date.replace(tzinfo=timezone.utc)

        # 決定排序時間：優先使用 start_time，若無則使用 session_date
        new_sort_time = start_time if start_time else new_session_date

        # 計算 session_number (該個案的第幾次會談，按會談時間排序)
        # 查詢該 case 所有現有的 sessions，按 start_time 或 session_date 排序
        result = db.execute(
            select(Session.id, Session.start_time, Session.session_date)
            .where(Session.case_id == case.id)
            .order_by(
                func.coalesce(Session.start_time, Session.session_date).asc(),
                Session.created_at.asc(),  # 同一時間則按創建時間排序
            )
        )
        existing_sessions = [
            (row[0], row[1] if row[1] else row[2]) for row in result.all()
        ]

        # 找出新會談應該排在第幾次
        session_number = 1
        for session_id, existing_time in existing_sessions:
            if new_sort_time > existing_time:
                session_number += 1
            else:
                break

        # 如果新會談插入到中間，需要更新後續所有 sessions 的 session_number
        if session_number <= len(existing_sessions):
            # 更新所有 >= session_number 的 sessions，將它們的編號 +1
            db.execute(
                Session.__table__.update()  # type: ignore[attr-defined]
                .where(Session.case_id == case.id)
                .where(Session.session_number >= session_number)
                .values(session_number=Session.session_number + 1)
            )
            db.flush()

        # 從 case 獲取 client 信息
        client_result = db.execute(select(Client).where(Client.id == case.client_id))
        client = client_result.scalar_one()

        # 處理逐字稿：優先從 recordings 聚合，若無則使用直接提供的 transcript
        recordings_list = request.recordings or []
        if recordings_list:
            # 從 recordings 自動聚合逐字稿
            full_transcript = aggregate_transcript_from_recordings(recordings_list)
        else:
            # 使用直接提供的 transcript（向下兼容）
            full_transcript = request.transcript

        # 創建 Session
        session = Session(
            case_id=case.id,
            tenant_id=tenant_id,
            session_number=session_number,
            session_date=new_session_date,
            start_time=start_time,
            end_time=end_time,
            transcript_text=full_transcript,
            transcript_sanitized=full_transcript,  # TODO: 串接 app.services.sanitizer_service（已實作）
            source_type="transcript",
            duration_minutes=request.duration_minutes,
            notes=request.notes,
            reflection=request.reflection or {},
            recordings=recordings_list,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # 檢查是否有報告
        result = db.execute(
            select(func.count()).where(
                select(1)
                .where(
                    Session.id == session.id,
                )
                .exists()
            )
        )

        return SessionResponse(
            id=session.id,
            client_id=client.id,
            client_name=client.name,
            case_id=case.id,
            session_number=session.session_number,
            session_date=session.session_date,
            start_time=session.start_time,
            end_time=session.end_time,
            transcript_text=session.transcript_text,
            duration_minutes=session.duration_minutes,
            notes=session.notes,
            reflection=session.reflection,
            recordings=session.recordings,  # 包含錄音片段
            has_report=False,  # 剛創建,還沒報告
            created_at=session.created_at,
            updated_at=session.updated_at,
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

    Args:
        client_id: 篩選特定個案
        search: 搜尋個案姓名或代碼
        skip: 分頁偏移
        limit: 每頁筆數
        current_user: 當前諮商師
        tenant_id: 租戶 ID
        db: 數據庫 session

    Returns:
        會談記錄列表
    """
    # 基礎查詢: 只查詢當前諮商師的 non-deleted sessions
    query = (
        select(Session, Client, Case)
        .join(Case, Session.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
            Session.deleted_at.is_(None),
            Case.deleted_at.is_(None),
            Client.deleted_at.is_(None),
        )
    )

    # 篩選特定個案
    if client_id:
        query = query.where(Client.id == client_id)

    # 搜尋功能（按個案姓名或代碼）
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Client.name.ilike(search_pattern),
                Client.code.ilike(search_pattern),
            )
        )

    # 計算總數
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar()

    # 分頁查詢 - 先按個案，再按會談時間排序（確保順序正確）
    query = (
        query.offset(skip)
        .limit(limit)
        .order_by(
            Case.id.asc(),
            func.coalesce(Session.start_time, Session.session_date).asc(),
            Session.created_at.asc(),  # 同一時間則按創建時間排序
        )
    )
    results = db.execute(query).all()

    items = []
    for session, client, case in results:
        # 檢查是否有報告
        has_report_result = db.execute(
            select(func.count())
            .select_from(Report)
            .where(Report.session_id == session.id)
        )
        has_report = (has_report_result.scalar() or 0) > 0

        items.append(
            SessionResponse(
                id=session.id,
                client_id=client.id,
                client_name=client.name,
                client_code=client.code,  # 加入個案代碼
                case_id=case.id,
                session_number=session.session_number,
                session_date=session.session_date,
                start_time=session.start_time,
                end_time=session.end_time,
                transcript_text=session.transcript_text,
                summary=session.summary,  # 加入會談摘要
                duration_minutes=session.duration_minutes,
                notes=session.notes,
                reflection=session.reflection,
                recordings=session.recordings,  # 包含錄音片段
                has_report=has_report,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
        )

    return SessionListResponse(total=total, items=items)


# Timeline Response Schemas
class TimelineSessionItem(BaseModel):
    """單次會談的時間線資訊"""

    session_id: UUID
    session_number: int
    date: str  # YYYY-MM-DD
    time_range: Optional[str] = None  # "HH:MM-HH:MM" or None
    summary: Optional[str] = None  # 會談摘要
    has_report: bool  # 是否有報告
    report_id: Optional[UUID] = None  # 報告 ID


class SessionTimelineResponse(BaseModel):
    """會談歷程時間線響應"""

    client_id: UUID
    client_name: str
    client_code: str
    total_sessions: int
    sessions: List[TimelineSessionItem]


@router.get("/timeline", response_model=SessionTimelineResponse)
def get_session_timeline(
    client_id: UUID = Query(..., description="個案 UUID"),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionTimelineResponse:
    """
    取得個案的會談歷程時間線

    回傳個案的所有會談記錄，包含：
    - 會談次數、日期、時間
    - 會談摘要（100字內）
    - 是否有報告

    Args:
        client_id: 個案 UUID (query parameter)
        current_user: 當前認證諮商師
        tenant_id: 租戶 ID
        db: Database session

    Returns:
        會談歷程時間線

    Raises:
        HTTPException: 404 if client not found

    Example:
        GET /api/v1/sessions/timeline?client_id=xxx-xxx-xxx
    """
    # 驗證 client 存在且屬於當前諮商師
    client_result = db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
        )
    )
    client = client_result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    # 查詢所有會談記錄（JOIN case + session + report）
    query = (
        select(Session, Report.id.label("report_id"))
        .join(Case, Session.case_id == Case.id)
        .outerjoin(
            Report,
            (Report.session_id == Session.id) & (Report.status == ReportStatus.DRAFT),
        )  # 只取 draft 狀態的報告
        .where(Case.client_id == client_id, Session.tenant_id == tenant_id)
        .order_by(Session.session_date.asc())  # 按日期排序
    )

    result = db.execute(query)
    rows = result.all()

    # 組裝時間線資料
    timeline_sessions = []
    for session, report_id in rows:
        # 格式化時間範圍
        time_range = None
        if session.start_time and session.end_time:
            start = session.start_time.strftime("%H:%M")
            end = session.end_time.strftime("%H:%M")
            time_range = f"{start}-{end}"

        timeline_sessions.append(
            TimelineSessionItem(
                session_id=session.id,
                session_number=session.session_number,
                date=session.session_date.strftime("%Y-%m-%d"),
                time_range=time_range,
                summary=session.summary,  # 來自 summary 欄位
                has_report=report_id is not None,
                report_id=report_id,
            )
        )

    return SessionTimelineResponse(
        client_id=client.id,
        client_name=client.name,
        client_code=client.code,
        total_sessions=len(timeline_sessions),
        sessions=timeline_sessions,
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
                full_transcript = aggregate_transcript_from_recordings(
                    request.recordings
                )
                session.transcript_text = full_transcript
                session.transcript_sanitized = full_transcript
        elif request.transcript is not None:
            # 直接更新 transcript（向下兼容）
            session.transcript_text = request.transcript
            session.transcript_sanitized = request.transcript

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
        HTTPException: 404 if not found, 400 if has reports, 500 if deletion fails
    """
    from datetime import datetime, timezone

    result = db.execute(
        select(Session, Client, Case)
        .join(Case, Session.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(
            Session.id == session_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
            Session.deleted_at.is_(None),
        )
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
class ReflectionRequest(BaseModel):
    """諮商師反思請求"""

    working_with_client: Optional[str] = None
    feeling_source: Optional[str] = None
    current_challenges: Optional[str] = None
    supervision_topics: Optional[str] = None


class ReflectionResponse(BaseModel):
    """諮商師反思響應"""

    session_id: UUID
    reflection: Optional[dict] = None
    updated_at: datetime


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
    result = db.execute(
        select(Session, Client)
        .join(Case, Session.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(
            Session.id == session_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session, _ = row

    return ReflectionResponse(
        session_id=session.id,
        reflection=session.reflection,
        updated_at=session.updated_at or session.created_at,
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
    result = db.execute(
        select(Session, Client)
        .join(Case, Session.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(
            Session.id == session_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    session, _ = row

    try:
        # Build reflection dict from request
        reflection = {}
        if reflection_data.working_with_client:
            reflection["working_with_client"] = reflection_data.working_with_client
        if reflection_data.feeling_source:
            reflection["feeling_source"] = reflection_data.feeling_source
        if reflection_data.current_challenges:
            reflection["current_challenges"] = reflection_data.current_challenges
        if reflection_data.supervision_topics:
            reflection["supervision_topics"] = reflection_data.supervision_topics

        session.reflection = reflection
        db.commit()
        db.refresh(session)

        return ReflectionResponse(
            session_id=session.id,
            reflection=session.reflection,
            updated_at=session.updated_at,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update reflection: {str(e)}",
        )


# Recording Append Endpoint
class AppendRecordingResponse(BaseModel):
    """Append 錄音片段響應"""

    session_id: UUID
    recording_added: RecordingSegment
    total_recordings: int
    transcript_text: str  # 更新後的完整逐字稿
    updated_at: datetime


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
    # 驗證 session 存在且屬於當前租戶
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

    session, _, _ = row

    try:
        # 重新從 DB 讀取確保取得最新 recordings（避免並發問題）
        db.refresh(session)

        # 取得現有 recordings（確保是 list，並創建新的 list 副本）
        existing_recordings = list(session.recordings) if session.recordings else []

        # 計算新的 segment_number（現有最大值 + 1）
        if existing_recordings:
            max_segment = max(r.get("segment_number", 0) for r in existing_recordings)
            new_segment_number = max_segment + 1
        else:
            new_segment_number = 1

        # 建立新的 recording segment
        new_recording = {
            "segment_number": new_segment_number,
            "start_time": request.start_time,
            "end_time": request.end_time,
            "duration_seconds": request.duration_seconds,
            "transcript_text": request.transcript_text,
            "transcript_sanitized": request.transcript_sanitized
            or request.transcript_text,
        }

        # Append 到 recordings 陣列
        existing_recordings.append(new_recording)

        # 必須重新賦值整個陣列才能觸發 SQLAlchemy 更新追蹤
        session.recordings = existing_recordings

        # 重新聚合 transcript_text
        full_transcript = aggregate_transcript_from_recordings(existing_recordings)
        session.transcript_text = full_transcript
        session.transcript_sanitized = full_transcript

        # 保存變更
        db.commit()
        db.refresh(session)

        return AppendRecordingResponse(
            session_id=session.id,
            recording_added=RecordingSegment(**new_recording),
            total_recordings=len(existing_recordings),
            transcript_text=session.transcript_text,
            updated_at=session.updated_at or session.created_at,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to append recording: {str(e)}",
        )
