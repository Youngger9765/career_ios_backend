"""
Sessions Analysis Logs API
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.counselor import Counselor
from app.schemas.session import AnalysisLogEntry, AnalysisLogsResponse
from app.services.analysis_log_service import AnalysisLogService

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions - Analysis"])


@router.get("/{session_id}/analysis-logs", response_model=AnalysisLogsResponse)
def get_analysis_logs(
    session_id: UUID,
    db: DBSession = Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
) -> AnalysisLogsResponse:
    """Get all analysis logs for a session in chronological order."""
    service = AnalysisLogService(db)
    logs = service.get_session_analysis_logs(session_id, current_user, tenant_id)

    if logs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied",
        )

    return AnalysisLogsResponse(
        session_id=session_id,
        total_logs=len(logs),
        logs=[AnalysisLogEntry(**log) for log in logs],
    )


@router.delete(
    "/{session_id}/analysis-logs/{log_index}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_analysis_log(
    session_id: UUID,
    log_index: int,
    db: DBSession = Depends(get_db),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a specific analysis log entry by index."""
    service = AnalysisLogService(db)
    success, error = service.delete_analysis_log(
        session_id, log_index, current_user, tenant_id
    )

    if not success:
        if error == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied",
            )
        elif error and error.startswith("invalid_index"):
            # Extract error message after "invalid_index: "
            detail = error.split("invalid_index: ", 1)[1]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )

    return None
