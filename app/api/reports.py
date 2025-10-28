"""
Reports query API
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.counselor import Counselor
from app.models.report import Report
from app.schemas.report import ReportListResponse, ReportResponse
from app.utils.report_formatters import create_formatter

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("", response_model=ReportListResponse)
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """
    List all reports for current counselor

    Args:
        skip: Pagination offset
        limit: Number of items per page
        client_id: Optional filter by client ID
        current_user: Current authenticated counselor
        tenant_id: Tenant ID
        db: Database session

    Returns:
        Paginated list of reports
    """
    # Base query - counselor's reports
    query = select(Report).where(
        Report.created_by_id == current_user.id,
        Report.tenant_id == tenant_id,
    )

    # Filter by client if provided
    if client_id:
        query = query.where(Report.client_id == client_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.offset(skip).limit(limit).order_by(Report.created_at.desc())
    result = db.execute(query)
    reports = result.scalars().all()

    return ReportListResponse(
        total=total,
        items=[ReportResponse.model_validate(r) for r in reports],
    )


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ReportResponse:
    """
    Get specific report by ID

    Args:
        report_id: Report UUID
        current_user: Current authenticated counselor
        tenant_id: Tenant ID
        db: Database session

    Returns:
        Report information
    """
    result = db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.created_by_id == current_user.id,
            Report.tenant_id == tenant_id,
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    return ReportResponse.model_validate(report)


@router.get("/{report_id}/formatted")
def get_formatted_report(
    report_id: UUID,
    format: str = Query("markdown", regex="^(markdown|html)$"),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get formatted report (markdown or HTML)

    Args:
        report_id: Report UUID
        format: Output format ("markdown" or "html")
        current_user: Current authenticated counselor
        tenant_id: Tenant ID
        db: Database session

    Returns:
        Formatted report content
    """
    result = db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.created_by_id == current_user.id,
            Report.tenant_id == tenant_id,
        )
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Format report using existing formatter
    formatter = create_formatter(format)
    formatted_content = formatter.format(report.content_json)

    return {
        "report_id": str(report_id),
        "format": format,
        "content": formatted_content,
    }
