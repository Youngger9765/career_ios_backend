"""
Sessions (逐字稿) API
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from sqlalchemy.orm import Session as DBSession

from app.api.session_analysis import _log_analysis_background
from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.core.exceptions import (
    BadRequestError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
)
from app.middleware.usage_limit import check_usage_limit
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
    EmotionFeedbackRequest,
    EmotionFeedbackResponse,
    ParentsReportResponse,
    ReflectionRequest,
    ReflectionResponse,
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
    SessionTimelineResponse,
    SessionUpdateRequest,
)
from app.services.analysis.emotion_service import EmotionAnalysisService
from app.services.core.recording_service import RecordingService
from app.services.core.reflection_service import ReflectionService
from app.services.core.session_service import SessionService
from app.services.core.timeline_service import TimelineService

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
    # Check usage limits before creating session
    check_usage_limit(current_user)

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


@router.get(
    "/{session_id}/report",
    response_model=Union[ParentsReportResponse, ReportResponse],
)
def get_session_report(
    session_id: UUID,
    request: Request,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: DBSession = Depends(get_db),
) -> Union[ParentsReportResponse, ReportResponse]:
    """
    取得會談的報告 (by session_id)

    回傳格式依據報告類型：
    - island_parents: 回傳 ParentsReportResponse (flat format)
    - 其他: 回傳 ReportResponse (full format with metadata)
    """
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

    # For Island Parents tenant, return flat ParentsReportResponse
    # to match POST endpoint format (regardless of how report was generated)
    if tenant_id == "island_parents":
        content = report.content_json or {}
        return ParentsReportResponse(
            encouragement=content.get("encouragement", ""),
            issue=content.get("issue", ""),
            analyze=content.get("analyze", ""),
            suggestion=content.get("suggestion", ""),
            references=content.get("references", []),
            timestamp=report.created_at.replace(tzinfo=timezone.utc).isoformat()
            if report.created_at
            else datetime.now(timezone.utc).isoformat(),
        )

    # For other modes (legacy), return full ReportResponse
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


# =============================================================================
# Emotion Analysis (Island Parents - Real-time Feedback)
# =============================================================================


@router.post(
    "/{session_id}/emotion-feedback",
    response_model=EmotionFeedbackResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_emotion_feedback(
    session_id: UUID,
    request: EmotionFeedbackRequest,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """
    **[Island Parents] Real-time emotion analysis for parent-child communication**

    Analyze the emotion level of parent's communication and provide instant guidance.

    **Emotion Levels:**
    - **Level 1 (綠燈/Green)**: Good communication - calm, empathetic, constructive
    - **Level 2 (黃燈/Yellow)**: Warning - slightly impatient, but not out of control
    - **Level 3 (紅燈/Red)**: Danger - strong negative emotion, may harm relationship

    **Performance:**
    - Response time: <3 seconds
    - Model: Gemini Flash Lite Latest

    **Request:**
    - `context`: Conversation context (可能包含多輪對話)
    - `target`: Target sentence to analyze

    **Response:**
    - `level`: 1/2/3 (green/yellow/red)
    - `hint`: Guidance hint (≤17 chars)

    **Example:**
    ```json
    {
      "context": "小明：我考試不及格\\n媽媽：你有認真準備嗎？",
      "target": "你就是不用功！"
    }
    ```

    **Returns:**
    ```json
    {
      "level": 3,
      "hint": "試著同理孩子的挫折感"
    }
    ```
    """
    # 1. Verify session exists and user has access
    try:
        session = (
            db.query(Session)
            .filter(Session.id == session_id, Session.tenant_id == tenant_id)
            .first()
        )

        if not session:
            raise NotFoundError(
                detail="Session not found",
                instance=f"/api/v1/sessions/{session_id}/emotion-feedback",
            )

        # Verify case access (session belongs to case, case belongs to counselor)
        case = db.query(Case).filter(Case.id == session.case_id).first()
        if not case:
            raise NotFoundError(
                detail="Case not found",
                instance=f"/api/v1/sessions/{session_id}/emotion-feedback",
            )

        if case.counselor_id != current_user.id:
            raise ForbiddenError(
                detail="Access denied to this session",
                instance=f"/api/v1/sessions/{session_id}/emotion-feedback",
            )

    except NotFoundError:
        raise
    except ForbiddenError:
        raise
    except Exception as e:
        logger.error(f"Failed to verify session access: {e}")
        raise InternalServerError(
            detail="Failed to verify session access",
            instance=f"/api/v1/sessions/{session_id}/emotion-feedback",
        )

    # 2. Validate request (context can be empty on first call)
    if not request.target or not request.target.strip():
        raise BadRequestError(
            detail="Target cannot be empty",
            instance=f"/api/v1/sessions/{session_id}/emotion-feedback",
        )

    # 3. Analyze emotion
    try:
        start_time = time.time()

        emotion_service = EmotionAnalysisService()
        result = await emotion_service.analyze_emotion(
            context=request.context, target=request.target
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Log to DB and BigQuery in background (after response sent)
        background_tasks.add_task(
            _log_analysis_background,
            session_id=session_id,
            counselor_id=current_user.id,
            tenant_id=tenant_id,
            transcript_segment=request.context[:500],  # First 500 chars
            result_data={
                "analysis_type": "emotion_feedback",
                "level": result["level"],
                "hint": result["hint"],
                "context_preview": request.context[:100],
                "target": request.target,
                "_metadata": {
                    "latency_ms": latency_ms,
                },
            },
            token_usage_data=result["token_usage"],
            analysis_type="emotion_feedback",
        )

        return EmotionFeedbackResponse(level=result["level"], hint=result["hint"])

    except asyncio.TimeoutError:
        logger.error("Emotion analysis timeout (>3s)")
        raise InternalServerError(
            detail="Analysis timeout - please try again",
            instance=f"/api/v1/sessions/{session_id}/emotion-feedback",
        )
    except Exception as e:
        logger.error(f"Emotion analysis failed: {e}")
        raise InternalServerError(
            detail="Failed to analyze emotion",
            instance=f"/api/v1/sessions/{session_id}/emotion-feedback",
        )


@router.post("/{session_id}/messages", status_code=201)
async def add_session_message(
    session_id: UUID,
    message: dict,
    db: DBSession = Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
):
    """
    Add a message to session (minimal implementation for testing)

    This is a placeholder endpoint for TDD testing.
    Real implementation should use proper message model.
    """
    # Verify session exists
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise NotFoundError(
            detail=f"Session {session_id} not found",
            instance=f"/api/v1/sessions/{session_id}/messages",
        )

    # Verify ownership
    case = db.query(Case).filter(Case.id == session.case_id).first()
    if not case or case.counselor_id != current_user.id:
        raise ForbiddenError(
            detail="Access denied",
            instance=f"/api/v1/sessions/{session_id}/messages",
        )

    # Minimal implementation: just return success
    # TODO: Actually store messages when Message model is implemented
    return {"message": "Message received (not stored - placeholder)"}


# REMOVED: Old deep-analyze endpoint (TDD stub)
# The proper implementation is now in app/api/session_analysis.py
# which returns RealtimeAnalyzeResponse with full analysis pipeline
