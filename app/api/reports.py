"""Reports query API"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.counselor import Counselor
from app.models.report import ReportStatus
from app.schemas.report import (
    ReportListResponse,
    ReportResponse,
    ReportUpdateRequest,
    ReportUpdateResponse,
)
from app.services.report_operations_service import ReportOperationsService

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


# Background task logic
async def _generate_report_background(
    report_id: UUID,
    session_id: UUID,
    transcript: str,
    report_type: str,
    rag_system: str,
):
    """Background task: Generate report content + session summary

    Args:
        report_id: Report UUID
        session_id: Session UUID (for updating summary)
        transcript: Transcript text
        report_type: Report type (enhanced/legacy)
        rag_system: RAG system (openai/gemini)
    """
    from sqlalchemy import select

    from app.api.rag_report import ReportRequest
    from app.api.rag_report import generate_report as rag_generate
    from app.core.database import SessionLocal
    from app.models.report import Report
    from app.models.session import Session as SessionModel
    from app.services.session_summary_service import session_summary_service
    from app.utils.report_formatters import create_formatter, unwrap_report

    db = SessionLocal()
    try:
        # Get report
        result = db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()

        if not report:
            return

        # Generate report via RAG
        rag_request = ReportRequest(
            transcript=transcript,
            num_participants=2,
            rag_system=rag_system,
            top_k=7,
            similarity_threshold=0.25,
            output_format="json",
            mode=report_type,
        )

        report_data = await rag_generate(rag_request, db)

        # Generate Markdown format
        markdown_formatter = create_formatter("markdown")
        content_markdown = markdown_formatter.format(unwrap_report(report_data))

        # Update report
        report.content_json = report_data
        report.content_markdown = content_markdown
        report.citations_json = report_data.get("theories_cited", [])
        report.prompt_tokens = report_data.get("token_usage", {}).get(
            "prompt_tokens", 0
        )
        report.completion_tokens = report_data.get("token_usage", {}).get(
            "completion_tokens", 0
        )
        report.quality_score = report_data.get("quality_summary", {}).get(
            "overall_score"
        )
        report.quality_grade = report_data.get("quality_summary", {}).get("grade")
        report.quality_strengths = report_data.get("quality_summary", {}).get(
            "strengths"
        )
        report.quality_weaknesses = report_data.get("quality_summary", {}).get(
            "improvements_needed"
        )
        report.status = ReportStatus.DRAFT

        db.commit()

        # Generate session summary asynchronously
        try:
            summary = await session_summary_service.generate_summary(
                transcript, max_length=100
            )
            if summary:
                session_result = db.execute(
                    select(SessionModel).where(SessionModel.id == session_id)
                )
                session_obj = session_result.scalar_one_or_none()
                if session_obj:
                    session_obj.summary = summary
                    db.commit()
        except Exception as summary_error:
            print(f"Warning: Failed to generate session summary: {summary_error}")

    except Exception as e:
        # Mark as failed
        if report:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            db.commit()
    finally:
        db.close()


# Request/Response Models
class GenerateReportRequest(BaseModel):
    """Request schema for generating report"""

    session_id: UUID
    report_type: str = "enhanced"  # enhanced | legacy
    rag_system: str = "openai"  # openai | gemini


class ProcessingStatus(BaseModel):
    """Report processing status"""

    status: str  # "processing"
    message: str


class GenerateReportResponse(BaseModel):
    """Async report generation response (HTTP 202)"""

    session_id: UUID
    report_id: UUID
    report: ProcessingStatus
    quality_summary: None = None


@router.get("", response_model=ReportListResponse)
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    client_id: Optional[UUID] = Query(None, description="Filter by client ID"),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    """List all reports for current counselor"""
    service = ReportOperationsService(db)
    rows, total = service.list_reports(
        counselor=current_user,
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        client_id=client_id,
    )

    # Build response items
    items = []
    for report, client_name, session_number in rows:
        report_dict = ReportResponse.model_validate(report).model_dump()
        report_dict["client_name"] = client_name
        report_dict["session_number"] = session_number
        items.append(ReportResponse(**report_dict))

    return ReportListResponse(total=total, items=items)


@router.get("/{report_id}")
def get_report(
    report_id: UUID,
    format: Optional[str] = Query(None, pattern="^(json|markdown|html)$"),
    use_edited: bool = Query(True, description="Use edited version if available"),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    """Get report by ID with optional formatting"""
    service = ReportOperationsService(db)
    row = service.get_report_by_id(
        report_id=report_id,
        counselor=current_user,
        tenant_id=tenant_id,
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    report, client_name, session_number = row

    # If no format or format is 'json', return full metadata
    if not format or format == "json":
        report_dict = ReportResponse.model_validate(report).model_dump()
        report_dict["client_name"] = client_name
        report_dict["session_number"] = session_number
        return ReportResponse(**report_dict)

    # Otherwise, return formatted content
    return service.format_report_content(report, format, use_edited)


@router.patch("/{report_id}", response_model=ReportUpdateResponse)
def update_report(
    report_id: UUID,
    update_request: ReportUpdateRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ReportUpdateResponse:
    """Update report content (counselor edits)"""
    service = ReportOperationsService(db)

    verified_report = service.update_report(
        report_id=report_id,
        edited_content_markdown=update_request.edited_content_markdown,
        counselor=current_user,
        tenant_id=tenant_id,
    )

    return ReportUpdateResponse(
        id=verified_report.id,
        edited_content_json=verified_report.edited_content_json,
        edited_content_markdown=verified_report.edited_content_markdown,
        edited_at=verified_report.edited_at,
        edit_count=verified_report.edit_count,
    )


@router.post(
    "/generate",
    response_model=GenerateReportResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_report(
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> GenerateReportResponse:
    """Generate counseling report from existing session (Async API)"""
    try:
        service = ReportOperationsService(db)

        # Validate session exists and belongs to counselor
        row = service.validate_session_and_get_data(
            session_id=request.session_id,
            counselor=current_user,
            tenant_id=tenant_id,
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied",
            )

        session, client, case = row
        transcript = session.transcript_text

        # Check for existing report
        existing_check = service.check_existing_report(session.id)
        if existing_check:
            existing_report, should_skip = existing_check
            if should_skip:
                return GenerateReportResponse(
                    session_id=session.id,
                    report_id=existing_report.id,
                    report=ProcessingStatus(
                        status=existing_report.status.value.lower(),
                        message=f"報告已存在（狀態：{existing_report.status.value}），返回現有報告",
                    ),
                    quality_summary=None,
                )

        # Create report record with processing status
        report = service.create_report_record(
            session_id=session.id,
            client_id=client.id,
            counselor=current_user,
            tenant_id=tenant_id,
            report_type=request.report_type,
            rag_system=request.rag_system,
        )

        # Add background task for report generation
        background_tasks.add_task(
            _generate_report_background,
            report_id=report.id,
            session_id=session.id,
            transcript=transcript,
            report_type=request.report_type,
            rag_system=request.rag_system,
        )

        # Return immediately
        return GenerateReportResponse(
            session_id=session.id,
            report_id=report.id,
            report=ProcessingStatus(
                status="processing", message="報告生成中，請稍後查詢結果"
            ),
            quality_summary=None,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )
