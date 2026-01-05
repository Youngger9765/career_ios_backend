"""
Sessions (逐字稿) API
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.core.exceptions import (
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
)
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.report import Report
from app.models.session import Session
from app.repositories.session_repository import SessionRepository
from app.schemas.report import ReportResponse
from app.schemas.session import (
    AppendRecordingRequest,
    AppendRecordingResponse,
    ReflectionRequest,
    ReflectionResponse,
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
    SessionTimelineResponse,
    SessionUpdateRequest,
)
from app.services.recording_service import RecordingService
from app.services.reflection_service import ReflectionService
from app.services.session_service import SessionService
from app.services.timeline_service import TimelineService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])


def _build_session_response(
    session: Session, client: Client, case: Case, has_report: bool
) -> SessionResponse:
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
        # Island Parents - 練習情境
        scenario=session.scenario,
        scenario_description=session.scenario_description,
        session_mode=session.session_mode,
        has_report=has_report,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _handle_value_error(e: ValueError, instance: str):
    raise NotFoundError(detail=str(e), instance=instance)


def _handle_permission_error(e: PermissionError, instance: str):
    raise ForbiddenError(detail=str(e), instance=instance)


def _handle_generic_error(e: Exception, operation: str, instance: str):
    raise InternalServerError(
        detail=f"Failed to {operation}: {str(e)}",
        instance=instance,
    )


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_data: SessionCreateRequest,
    request: Request,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionResponse:
    """創建逐字稿記錄（不生成報告）"""
    service = SessionService(db)
    repo = SessionRepository(db)
    instance = str(request.url.path)
    try:
        session = service.create_session(session_data, current_user, tenant_id)
        case = repo.get_case_by_id(session.case_id, tenant_id)
        client = repo.get_client_by_id(case.client_id)
        return _build_session_response(session, client, case, has_report=False)
    except ValueError as e:
        _handle_value_error(e, instance)
    except Exception as e:
        db.rollback()
        _handle_generic_error(e, "create session", instance)


@router.get("", response_model=SessionListResponse)
def list_sessions(
    client_id: Optional[UUID] = Query(None, description="Filter by client"),
    case_id: Optional[UUID] = Query(None, description="Filter by case"),
    session_mode: Optional[str] = Query(
        None, description="Filter by session_mode: practice / emergency"
    ),
    search: Optional[str] = Query(None, description="Search by client name or code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionListResponse:
    """列出會談記錄

    支援篩選條件：
    - client_id: 依孩子（Client）篩選
    - case_id: 依案例（Case）篩選
    - session_mode: 依模式篩選 (practice=對話練習, emergency=親子溝通)
    - search: 依孩子名稱或代碼搜尋
    """
    service = SessionService(db)
    session_data, total = service.list_sessions(
        counselor=current_user,
        tenant_id=tenant_id,
        client_id=client_id,
        case_id=case_id,
        mode=session_mode,
        search=search,
        skip=skip,
        limit=limit,
    )
    items = [
        _build_session_response(session, client, case, has_report)
        for session, case, client, has_report in session_data
    ]
    return SessionListResponse(total=total, items=items)


@router.get("/timeline", response_model=SessionTimelineResponse)
def get_session_timeline(
    client_id: UUID = Query(..., description="個案 UUID"),
    request: Request = None,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionTimelineResponse:
    """取得個案的會談歷程時間線"""
    service = TimelineService(db)
    instance = str(request.url.path) if request else "/api/v1/sessions/timeline"
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
        _handle_value_error(e, instance)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: UUID,
    request: Request,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionResponse:
    """取得單一逐字稿"""
    service = SessionService(db)
    result = service.get_session_with_details(session_id, current_user, tenant_id)
    if not result:
        raise NotFoundError(
            detail="Session not found",
            instance=str(request.url.path),
        )
    session, client, case, has_report = result
    return _build_session_response(session, client, case, has_report)


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: UUID,
    update_data: SessionUpdateRequest,
    request: Request,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionResponse:
    """更新逐字稿"""
    service = SessionService(db)
    instance = str(request.url.path)
    try:
        session, client, case, has_report = service.update_session(
            session_id, update_data, current_user, tenant_id
        )
        return _build_session_response(session, client, case, has_report)
    except ValueError as e:
        _handle_value_error(e, instance)
    except Exception as e:
        db.rollback()
        _handle_generic_error(e, "update session", instance)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    request: Request,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
):
    """軟刪除逐字稿 (如果有關聯報告會失敗)"""
    service = SessionService(db)
    instance = str(request.url.path)
    try:
        service.delete_session(session_id, current_user, tenant_id)
    except ValueError as e:
        error_msg = str(e)
        if "with associated reports" in error_msg:
            raise BadRequestError(
                detail=error_msg,
                instance=instance,
            )
        raise NotFoundError(
            detail=error_msg,
            instance=instance,
        )
    except Exception as e:
        db.rollback()
        raise InternalServerError(
            detail=f"Failed to delete session: {str(e)}",
            instance=instance,
        )


@router.get("/{session_id}/reflection", response_model=ReflectionResponse)
def get_reflection(
    session_id: UUID,
    request: Request,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> ReflectionResponse:
    """取得會談的諮詢師反思"""
    service = ReflectionService(db)
    instance = str(request.url.path)
    try:
        reflection, session = service.get_reflection(
            session_id, current_user.id, tenant_id
        )
        return ReflectionResponse(
            session_id=session_id,
            reflection=reflection,
            updated_at=session.updated_at or session.created_at,
        )
    except ValueError as e:
        _handle_value_error(e, instance)
    except PermissionError as e:
        _handle_permission_error(e, instance)


@router.put("/{session_id}/reflection", response_model=ReflectionResponse)
def update_reflection(
    session_id: UUID,
    reflection_data: ReflectionRequest,
    request: Request,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> ReflectionResponse:
    """更新或建立會談的諮詢師反思"""
    service = ReflectionService(db)
    instance = str(request.url.path)
    try:
        reflection, session = service.update_reflection(
            session_id, reflection_data.reflection, current_user.id, tenant_id
        )
        return ReflectionResponse(
            session_id=session_id,
            reflection=reflection,
            updated_at=session.updated_at,
        )
    except ValueError as e:
        _handle_value_error(e, instance)
    except PermissionError as e:
        _handle_permission_error(e, instance)
    except Exception as e:
        _handle_generic_error(e, "update reflection", instance)


@router.post("/{session_id}/recordings/append", response_model=AppendRecordingResponse)
def append_recording(
    session_id: UUID,
    recording_data: AppendRecordingRequest,
    request: Request,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> AppendRecordingResponse:
    """Append新錄音片段（自動計算segment_number，重新聚合transcript）"""
    service = RecordingService(db)
    instance = str(request.url.path)
    try:
        session, new_recording, total_recordings = service.append_recording(
            session_id, recording_data, current_user.id, tenant_id
        )

        return AppendRecordingResponse(
            session_id=session.id,
            recording_added=new_recording,
            total_recordings=total_recordings,
            transcript_text=session.transcript_text,
            updated_at=session.updated_at or session.created_at,
        )
    except ValueError as e:
        _handle_value_error(e, instance)
    except PermissionError as e:
        _handle_permission_error(e, instance)
    except Exception as e:
        _handle_generic_error(e, "append recording", instance)


@router.get("/{session_id}/report", response_model=ReportResponse)
def get_session_report(
    session_id: UUID,
    request: Request,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> ReportResponse:
    """取得會談的報告 (by session_id) - 用於 History Page"""
    instance = str(request.url.path)

    # First verify the session exists and user has access
    service = SessionService(db)
    result = service.get_session_with_details(session_id, current_user, tenant_id)
    if not result:
        raise NotFoundError(
            detail="Session not found",
            instance=instance,
        )

    session, client, case, has_report = result

    if not has_report:
        raise NotFoundError(
            detail="No report found for this session",
            instance=instance,
        )

    # Get the report for this session
    from sqlalchemy import select

    report = db.execute(
        select(Report).where(
            Report.session_id == session_id,
            Report.deleted_at.is_(None),
        )
    ).scalar_one_or_none()

    if not report:
        raise NotFoundError(
            detail="Report not found",
            instance=instance,
        )

    # Build response
    report_dict = {
        "id": report.id,
        "session_id": report.session_id,
        "client_id": case.client_id,
        "created_by_id": report.created_by_id,
        "tenant_id": report.tenant_id,
        "version": report.version,
        "status": report.status,
        "mode": report.mode,
        "client_name": client.name,
        "session_number": session.session_number,
        "content_json": report.content_json,
        "content_markdown": report.content_markdown,
        "edited_content_json": report.edited_content_json,
        "edited_content_markdown": report.edited_content_markdown,
        "edited_at": str(report.edited_at) if report.edited_at else None,
        "edit_count": report.edit_count,
        "citations_json": report.citations_json,
        "quality_score": report.quality_score,
        "quality_grade": report.quality_grade,
        "quality_strengths": report.quality_strengths,
        "quality_weaknesses": report.quality_weaknesses,
        "error_message": report.error_message,
        "ai_model": report.ai_model,
        "prompt_tokens": report.prompt_tokens,
        "completion_tokens": report.completion_tokens,
        "summary": report.summary,
        "analysis": report.analysis,
        "recommendations": report.recommendations,
        "action_items": report.action_items,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }

    return ReportResponse(**report_dict)
