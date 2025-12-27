"""
Session Usage API - Analysis Logs and Usage Tracking
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.counselor import Counselor
from app.models.session import Session as SessionModel
from app.models.session_analysis_log import SessionAnalysisLog
from app.models.session_usage import SessionUsage
from app.schemas.session_usage import (
    SessionAnalysisLogCreate,
    SessionAnalysisLogListResponse,
    SessionAnalysisLogResponse,
    SessionUsageCreate,
    SessionUsageResponse,
    SessionUsageUpdate,
)
from app.services.credit_billing import CreditBillingService

router = APIRouter(tags=["Session Usage"])


def _get_session_or_404(
    db: DBSession, session_id: UUID, tenant_id: str
) -> SessionModel:
    """Get session with tenant isolation and soft-delete check"""
    session = (
        db.query(SessionModel)
        .filter(
            SessionModel.id == session_id,
            SessionModel.tenant_id == tenant_id,
            SessionModel.deleted_at.is_(None),  # Exclude soft-deleted sessions
        )
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    return session


@router.post(
    "/api/v1/sessions/{session_id}/analysis-logs",
    response_model=SessionAnalysisLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analysis_log(
    session_id: UUID,
    request: SessionAnalysisLogCreate,
    current_user: Counselor = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> SessionAnalysisLogResponse:
    """Create session analysis log"""
    tenant_id = current_user.tenant_id

    # Verify session exists and belongs to tenant
    _get_session_or_404(db, session_id, tenant_id)

    # Create analysis log
    log = SessionAnalysisLog(
        session_id=session_id,
        counselor_id=current_user.id,
        tenant_id=tenant_id,
        analysis_type=request.analysis_type,
        transcript=request.transcript,
        analysis_result=request.analysis_result or {},
        safety_level=request.safety_level,
        risk_indicators=request.risk_indicators or [],
        rag_documents=request.rag_documents or [],
        rag_sources=request.rag_sources or [],
        token_usage=request.token_usage or {},
        analyzed_at=datetime.now(timezone.utc),
    )

    db.add(log)
    db.commit()
    db.refresh(log)

    return SessionAnalysisLogResponse.model_validate(log)


@router.get(
    "/api/v1/sessions/{session_id}/analysis-logs",
    response_model=SessionAnalysisLogListResponse,
)
def list_analysis_logs(
    session_id: UUID,
    safety_level: Optional[str] = Query(None, description="Filter by safety level"),
    current_user: Counselor = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> SessionAnalysisLogListResponse:
    """List analysis logs for a session"""
    tenant_id = current_user.tenant_id

    # Verify session exists and belongs to counselor (with ownership check)
    from sqlalchemy import select

    from app.models.case import Case
    from app.models.client import Client

    result = db.execute(
        select(SessionModel, Client, Case)
        .join(Case, SessionModel.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(
            SessionModel.id == session_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
            SessionModel.deleted_at.is_(None),
            Case.deleted_at.is_(None),
            Client.deleted_at.is_(None),
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found or access denied",
        )

    # Build query
    query = db.query(SessionAnalysisLog).filter(
        SessionAnalysisLog.session_id == session_id,
        SessionAnalysisLog.tenant_id == tenant_id,
    )

    # Apply safety level filter if provided
    if safety_level:
        query = query.filter(SessionAnalysisLog.safety_level == safety_level)

    # Order by analyzed_at DESC
    query = query.order_by(SessionAnalysisLog.analyzed_at.desc())

    # Get total count
    total = query.count()

    # Get items
    items = query.all()

    return SessionAnalysisLogListResponse(
        total=total,
        items=[SessionAnalysisLogResponse.model_validate(log) for log in items],
    )


@router.delete(
    "/api/v1/sessions/{session_id}/analysis-logs/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_analysis_log(
    session_id: UUID,
    log_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> None:
    """Delete a specific analysis log"""
    tenant_id = current_user.tenant_id

    # Verify session exists and belongs to counselor (with ownership check)
    from sqlalchemy import select

    from app.models.case import Case
    from app.models.client import Client

    result = db.execute(
        select(SessionModel, Client, Case)
        .join(Case, SessionModel.case_id == Case.id)
        .join(Client, Case.client_id == Client.id)
        .where(
            SessionModel.id == session_id,
            Client.counselor_id == current_user.id,
            Client.tenant_id == tenant_id,
            SessionModel.deleted_at.is_(None),
            Case.deleted_at.is_(None),
            Client.deleted_at.is_(None),
        )
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found or access denied",
        )

    # Find the log
    log = (
        db.query(SessionAnalysisLog)
        .filter(
            SessionAnalysisLog.id == log_id,
            SessionAnalysisLog.session_id == session_id,
            SessionAnalysisLog.tenant_id == tenant_id,
        )
        .first()
    )

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis log {log_id} not found",
        )

    # Delete the log
    db.delete(log)
    db.commit()

    return None


@router.get(
    "/api/v1/sessions/{session_id}/usage",
    response_model=SessionUsageResponse,
)
def get_session_usage(
    session_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> SessionUsageResponse:
    """Get session usage record"""
    tenant_id = current_user.tenant_id

    # Verify session exists and belongs to tenant
    _get_session_or_404(db, session_id, tenant_id)

    # Get usage record
    usage = (
        db.query(SessionUsage)
        .filter(
            SessionUsage.session_id == session_id,
            SessionUsage.tenant_id == tenant_id,
        )
        .first()
    )

    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usage record for session {session_id} not found",
        )

    return SessionUsageResponse.model_validate(usage)


@router.post(
    "/api/v1/sessions/{session_id}/usage",
    response_model=SessionUsageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session_usage(
    session_id: UUID,
    request: SessionUsageCreate,
    current_user: Counselor = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> SessionUsageResponse:
    """Create session usage record"""
    tenant_id = current_user.tenant_id

    # Verify session exists and belongs to tenant
    _get_session_or_404(db, session_id, tenant_id)

    # Calculate duration if start_time and end_time provided
    duration_seconds = request.duration_seconds
    if request.start_time and request.end_time:
        # Ensure both datetimes are timezone-aware for arithmetic
        start = request.start_time
        end = request.end_time

        # Convert naive datetimes to UTC if needed
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        duration_seconds = int((end - start).total_seconds())

    # Calculate credits based on pricing rule
    credits_deducted = 0.0
    pricing_rule = request.pricing_rule

    if request.status == "completed":
        unit = pricing_rule.get("unit")
        rate = pricing_rule.get("rate", 0)

        if unit == "minute" and duration_seconds is not None:
            minutes = duration_seconds / 60.0
            credits_deducted = minutes * rate
        elif unit == "token" and request.token_usage:
            total_tokens = request.token_usage.get("total_tokens", 0)
            credits_deducted = total_tokens * rate
        elif unit == "analysis" and request.analysis_count:
            credits_deducted = request.analysis_count * rate

    # Create usage record
    try:
        usage = SessionUsage(
            session_id=session_id,
            counselor_id=current_user.id,
            tenant_id=tenant_id,
            usage_type=request.usage_type,
            status=request.status,
            start_time=request.start_time,
            end_time=request.end_time,
            duration_seconds=duration_seconds or 0,
            analysis_count=request.analysis_count or 0,
            token_usage=request.token_usage or {},
            pricing_rule=pricing_rule,
            credits_deducted=credits_deducted,
            credit_deducted=request.status == "completed" and credits_deducted > 0,
        )

        db.add(usage)

        # Deduct credits from counselor if completed
        if usage.credit_deducted:
            billing_service = CreditBillingService(db)
            billing_service.add_credits(
                counselor_id=current_user.id,
                credits_delta=-credits_deducted,  # Negative for usage
                transaction_type="usage",
                resource_type="session",
                resource_id=str(session_id),
                raw_data={
                    "pricing_rule": pricing_rule,
                    "credits_deducted": credits_deducted,
                },
            )

        db.commit()
        db.refresh(usage)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Usage record for session {session_id} already exists",
        )

    return SessionUsageResponse.model_validate(usage)


@router.patch(
    "/api/v1/sessions/{session_id}/usage/{usage_id}",
    response_model=SessionUsageResponse,
)
def update_session_usage(
    session_id: UUID,
    usage_id: UUID,
    request: SessionUsageUpdate,
    current_user: Counselor = Depends(get_current_user),
    db: DBSession = Depends(get_db),
) -> SessionUsageResponse:
    """Update session usage record"""
    tenant_id = current_user.tenant_id

    # Verify session exists and belongs to tenant
    _get_session_or_404(db, session_id, tenant_id)

    # Get usage record
    usage = (
        db.query(SessionUsage)
        .filter(
            SessionUsage.id == usage_id,
            SessionUsage.session_id == session_id,
            SessionUsage.tenant_id == tenant_id,
        )
        .first()
    )

    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usage record {usage_id} not found",
        )

    # Update fields
    if request.status is not None:
        usage.status = request.status

    if request.end_time is not None:
        usage.end_time = request.end_time

    # Calculate duration if end_time updated
    if request.end_time and usage.start_time:
        # Ensure both datetimes are timezone-aware for arithmetic
        start = usage.start_time
        end = request.end_time

        # Convert naive datetimes to UTC if needed
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        usage.duration_seconds = int((end - start).total_seconds())
    elif request.duration_seconds is not None:
        usage.duration_seconds = request.duration_seconds

    if request.analysis_count is not None:
        usage.analysis_count = request.analysis_count

    if request.total_tokens is not None:
        usage.total_tokens = request.total_tokens

    # Recalculate credits if status changed to completed
    if request.status == "completed" and not usage.credit_deducted:
        pricing_rule = usage.pricing_rule
        unit = pricing_rule.get("unit")
        rate = pricing_rule.get("rate", 0)

        credits_to_deduct = 0.0
        if unit == "minute" and usage.duration_seconds:
            minutes = usage.duration_seconds / 60.0
            credits_to_deduct = minutes * rate
        elif unit == "token" and usage.total_tokens:
            credits_to_deduct = usage.total_tokens * rate
        elif unit == "analysis" and usage.analysis_count:
            credits_to_deduct = usage.analysis_count * rate

        usage.credits_deducted = credits_to_deduct
        usage.credit_deducted = True

        # Deduct credits from counselor
        billing_service = CreditBillingService(db)
        billing_service.add_credits(
            counselor_id=current_user.id,
            credits_delta=-credits_to_deduct,  # Negative for usage
            transaction_type="usage",
            resource_type="session",
            resource_id=str(session_id),
            raw_data={
                "pricing_rule": pricing_rule,
                "credits_deducted": credits_to_deduct,
            },
        )

    if request.credits_consumed is not None:
        usage.credits_consumed = request.credits_consumed

    if request.credit_deducted is not None:
        usage.credit_deducted = request.credit_deducted

    db.commit()
    db.refresh(usage)

    return SessionUsageResponse.model_validate(usage)
