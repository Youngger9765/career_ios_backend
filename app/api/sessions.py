"""
Sessions (逐字稿) API
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session
from app.repositories.session_repository import SessionRepository
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
        has_report=has_report,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _handle_value_error(e: ValueError):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


def _handle_permission_error(e: PermissionError):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


def _handle_generic_error(e: Exception, operation: str):
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to {operation}: {str(e)}",
    )


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    request: SessionCreateRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionResponse:
    """創建逐字稿記錄（不生成報告）"""
    service = SessionService(db)
    repo = SessionRepository(db)
    try:
        session = service.create_session(request, current_user, tenant_id)
        case = repo.get_case_by_id(session.case_id, tenant_id)
        client = repo.get_client_by_id(case.client_id)
        return _build_session_response(session, client, case, has_report=False)
    except ValueError as e:
        _handle_value_error(e)
    except Exception as e:
        db.rollback()
        _handle_generic_error(e, "create session")


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
    """列出會談記錄"""
    service = SessionService(db)
    session_data, total = service.list_sessions(
        counselor=current_user,
        tenant_id=tenant_id,
        client_id=client_id,
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
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionTimelineResponse:
    """取得個案的會談歷程時間線"""
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
        _handle_value_error(e)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionResponse:
    """取得單一逐字稿"""
    service = SessionService(db)
    result = service.get_session_with_details(session_id, current_user, tenant_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    session, client, case, has_report = result
    return _build_session_response(session, client, case, has_report)


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: UUID,
    request: SessionUpdateRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> SessionResponse:
    """更新逐字稿"""
    service = SessionService(db)
    try:
        session, client, case, has_report = service.update_session(
            session_id, request, current_user, tenant_id
        )
        return _build_session_response(session, client, case, has_report)
    except ValueError as e:
        _handle_value_error(e)
    except Exception as e:
        db.rollback()
        _handle_generic_error(e, "update session")


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
):
    """軟刪除逐字稿 (如果有關聯報告會失敗)"""
    service = SessionService(db)
    try:
        service.delete_session(session_id, current_user, tenant_id)
    except ValueError as e:
        error_msg = str(e)
        if "with associated reports" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_msg,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}",
        )


@router.get("/{session_id}/reflection", response_model=ReflectionResponse)
def get_reflection(
    session_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> ReflectionResponse:
    """取得會談的諮詢師反思"""
    service = ReflectionService(db)
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
        _handle_value_error(e)
    except PermissionError as e:
        _handle_permission_error(e)


@router.put("/{session_id}/reflection", response_model=ReflectionResponse)
def update_reflection(
    session_id: UUID,
    reflection_data: ReflectionRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> ReflectionResponse:
    """更新或建立會談的諮詢師反思"""
    service = ReflectionService(db)
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
        _handle_value_error(e)
    except PermissionError as e:
        _handle_permission_error(e)
    except Exception as e:
        _handle_generic_error(e, "update reflection")


@router.post("/{session_id}/recordings/append", response_model=AppendRecordingResponse)
def append_recording(
    session_id: UUID,
    request: AppendRecordingRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> AppendRecordingResponse:
    """Append新錄音片段（自動計算segment_number，重新聚合transcript）"""
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
        _handle_value_error(e)
    except PermissionError as e:
        _handle_permission_error(e)
    except Exception as e:
        _handle_generic_error(e, "append recording")
