"""
Sessions (逐字稿) API
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.report import Report, ReportStatus
from app.models.session import Session

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


# Schemas
class SessionCreateRequest(BaseModel):
    """創建會談記錄請求"""
    client_id: UUID
    session_date: str  # YYYY-MM-DD
    start_time: Optional[str] = None  # YYYY-MM-DD HH:MM
    end_time: Optional[str] = None  # YYYY-MM-DD HH:MM
    transcript: str
    duration_minutes: Optional[int] = None  # 保留向下兼容
    notes: Optional[str] = None
    reflection: Optional[dict] = None  # 諮商師反思（JSON 格式，彈性支援不同租戶需求）


class SessionUpdateRequest(BaseModel):
    """更新會談記錄請求"""
    session_date: Optional[str] = None  # YYYY-MM-DD
    start_time: Optional[str] = None  # YYYY-MM-DD HH:MM
    end_time: Optional[str] = None  # YYYY-MM-DD HH:MM
    transcript: Optional[str] = None
    notes: Optional[str] = None
    duration_minutes: Optional[int] = None  # 保留向下兼容
    reflection: Optional[dict] = None  # 諮商師反思


class SessionResponse(BaseModel):
    """會談記錄響應"""
    id: UUID
    client_id: UUID
    client_name: Optional[str] = None  # 個案姓名
    client_code: Optional[str] = None  # 個案代碼
    case_id: UUID
    session_number: int
    session_date: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    transcript_text: str
    summary: Optional[str] = None  # 會談摘要（AI 生成）
    duration_minutes: Optional[int]
    notes: Optional[str]
    reflection: Optional[dict] = None  # 諮商師反思（人類撰寫）
    has_report: bool  # 是否已生成報告
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """逐字稿列表響應"""
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
    # 驗證個案存在且屬於當前諮商師
    result = db.execute(
        select(Client).where(
            Client.id == request.client_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found or access denied",
        )

    try:
        # 查找或創建 Case
        result = db.execute(
            select(Case).where(
                Case.client_id == client.id,
                Case.tenant_id == tenant_id,
            )
        )
        case = result.scalar_one_or_none()

        if not case:
            # Generate case_number
            result = db.execute(
                select(func.count(Case.id)).where(Case.tenant_id == tenant_id)
            )
            case_count = result.scalar() or 0
            case_number = f"CASE-{tenant_id.upper()}-{case_count + 1:04d}"

            case = Case(
                client_id=client.id,
                counselor_id=current_user.id,
                tenant_id=tenant_id,
                case_number=case_number,
            )
            db.add(case)
            db.flush()

        # Parse start_time and end_time if provided
        start_time = None
        end_time = None
        if request.start_time:
            # Handle both "YYYY-MM-DD HH:MM" and "HH:MM" formats
            time_str = request.start_time.strip()
            if ' ' in time_str or 'T' in time_str or len(time_str) > 10:
                # Full datetime string
                start_time = datetime.fromisoformat(time_str.replace(' ', 'T'))
            else:
                # Only time provided, combine with session_date
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_time must include date (format: YYYY-MM-DD HH:MM)"
                )
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)

        if request.end_time:
            # Handle both "YYYY-MM-DD HH:MM" and "HH:MM" formats
            time_str = request.end_time.strip()
            if ' ' in time_str or 'T' in time_str or len(time_str) > 10:
                # Full datetime string
                end_time = datetime.fromisoformat(time_str.replace(' ', 'T'))
            else:
                # Only time provided, combine with session_date
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="end_time must include date (format: YYYY-MM-DD HH:MM)"
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
                Session.created_at.asc()  # 同一時間則按創建時間排序
            )
        )
        existing_sessions = [(row[0], row[1] if row[1] else row[2]) for row in result.all()]

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
                Session.__table__.update()
                .where(Session.case_id == case.id)
                .where(Session.session_number >= session_number)
                .values(session_number=Session.session_number + 1)
            )
            db.flush()

        # 創建 Session
        session = Session(
            case_id=case.id,
            tenant_id=tenant_id,
            session_number=session_number,
            session_date=new_session_date,
            start_time=start_time,
            end_time=end_time,
            transcript_text=request.transcript,
            transcript_sanitized=request.transcript,  # TODO: 實作脫敏
            source_type="transcript",
            duration_minutes=request.duration_minutes,
            notes=request.notes,
            reflection=request.reflection or {},
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # 檢查是否有報告
        result = db.execute(
            select(func.count()).where(
                select(1).where(
                    Session.id == session.id,
                ).exists()
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
    列出逐字稿記錄

    Args:
        client_id: 篩選特定個案
        search: 搜尋個案姓名或代碼
        skip: 分頁偏移
        limit: 每頁筆數
        current_user: 當前諮商師
        tenant_id: 租戶 ID
        db: 數據庫 session

    Returns:
        逐字稿列表
    """
    # 基礎查詢: 只查詢當前諮商師的 sessions
    query = (
        select(Session, Client, Case)
        .join(Case, Session.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
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
    query = query.offset(skip).limit(limit).order_by(
        Case.id.asc(),
        func.coalesce(Session.start_time, Session.session_date).asc(),
        Session.created_at.asc()  # 同一時間則按創建時間排序
    )
    results = db.execute(query).all()

    items = []
    for session, client, case in results:
        # 檢查是否有報告
        has_report_result = db.execute(
            select(func.count()).select_from(
                select(1)
                .where(Session.id == session.id)
                .where(Session.reports.any())
                .subquery()
            )
        )
        has_report = has_report_result.scalar() > 0

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
            select(1).where(Session.id == session.id).where(Session.reports.any()).subquery()
        )
    )
    has_report = has_report_result.scalar() > 0

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
            if ' ' in time_str or 'T' in time_str or len(time_str) > 10:
                new_start_time = datetime.fromisoformat(time_str.replace(' ', 'T'))
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="start_time must include date (format: YYYY-MM-DD HH:MM)"
                )
            if new_start_time.tzinfo is None:
                new_start_time = new_start_time.replace(tzinfo=timezone.utc)
            if new_start_time != session.start_time:
                time_changed = True
            session.start_time = new_start_time

        if request.end_time is not None:
            time_str = request.end_time.strip()
            if ' ' in time_str or 'T' in time_str or len(time_str) > 10:
                new_end_time = datetime.fromisoformat(time_str.replace(' ', 'T'))
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="end_time must include date (format: YYYY-MM-DD HH:MM)"
                )
            if new_end_time.tzinfo is None:
                new_end_time = new_end_time.replace(tzinfo=timezone.utc)
            session.end_time = new_end_time

        if request.transcript is not None:
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
        new_sort_time = session.start_time if session.start_time else session.session_date

        if time_changed:
            # 1. 先將當前 session 的 session_number 設為 0（臨時值）
            session.session_number = 0
            db.flush()

            # 2. 將原本 > old_session_number 的所有 sessions 編號 -1
            db.execute(
                Session.__table__.update()
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
                .order_by(
                    func.coalesce(Session.start_time, Session.session_date).asc()
                )
            )
            existing_times = [
                (row[0] if row[0] else row[1]) for row in result.all()
            ]

            # 4. 找出新 session_number
            new_session_number = 1
            for existing_time in existing_times:
                if new_sort_time > existing_time:
                    new_session_number += 1
                else:
                    break

            # 5. 更新 >= new_session_number 的所有 sessions（不包括當前 session）編號 +1
            db.execute(
                Session.__table__.update()
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
                select(1).where(Session.id == session.id).where(Session.reports.any()).subquery()
            )
        )
        has_report = has_report_result.scalar() > 0

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
    刪除逐字稿 (如果有關聯報告會失敗)

    Args:
        session_id: Session UUID
        current_user: 當前諮商師
        tenant_id: 租戶 ID
        db: 數據庫 session

    Raises:
        HTTPException: 404 if not found, 400 if has reports, 500 if deletion fails
    """
    result = db.execute(
        select(Session, Client, Case)
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

    session, _, case = row

    # 檢查是否有報告
    has_report_result = db.execute(
        select(func.count()).select_from(
            select(1).where(Session.id == session.id).where(Session.reports.any()).subquery()
        )
    )
    has_report = has_report_result.scalar() > 0

    if has_report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete session with associated reports",
        )

    try:
        deleted_session_number = session.session_number
        case_id = session.case_id

        db.delete(session)
        db.flush()

        # 重新編號：將所有 session_number > deleted_session_number 的 sessions 編號 -1
        db.execute(
            Session.__table__.update()
            .where(Session.case_id == case_id)
            .where(Session.session_number > deleted_session_number)
            .values(session_number=Session.session_number - 1)
        )

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


