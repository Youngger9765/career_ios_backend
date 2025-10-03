from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.schemas.report import ReportResponse, ReportCreate, ReportUpdate
from app.utils.mock_data import mock_generator
from app.models.report import ReportStatus
import asyncio
from app.core.config import settings

router = APIRouter()


@router.get("/", response_model=List[ReportResponse])
async def list_reports(
    session_id: Optional[str] = Query(None),
    status: Optional[ReportStatus] = Query(None)
):
    """List reports with optional filters"""
    reports = [mock_generator.generate_report(session_id) for _ in range(5)]
    
    if status:
        for report in reports:
            report["status"] = status
    
    return [ReportResponse(**report) for report in reports]


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """Get specific report"""
    report = mock_generator.generate_report()
    report["id"] = report_id
    return ReportResponse(**report)


@router.post("/generate", response_model=ReportResponse, status_code=201)
async def generate_report(
    session_id: str,
    agent_id: Optional[int] = Query(None),
    num_participants: int = Query(2)
):
    """
    Generate AI report for session

    Flow:
    1. Get session transcript
    2. Call report_service.generate_report_from_transcript()
    3. Create report record with content_json and citations_json
    4. Return report
    """

    if settings.MOCK_MODE:
        await asyncio.sleep(settings.MOCK_DELAY * 3)
        report = mock_generator.generate_report(session_id)
        return ReportResponse(**report)

    # TODO: Real implementation
    # from app.services.report_service import report_service
    # from app.models.report import Report
    # from app.database import get_db
    #
    # async with get_db() as db:
    #     # 1. Get session transcript
    #     session = await db.get(Session, session_id)
    #     if not session.transcript_text:
    #         raise HTTPException(400, "Session has no transcript")
    #
    #     # 2. Generate report
    #     result = await report_service.generate_report_from_transcript(
    #         transcript=session.transcript_text,
    #         agent_id=agent_id,
    #         num_participants=num_participants
    #     )
    #
    #     # 3. Create report record
    #     report = Report(
    #         session_id=session_id,
    #         created_by_id=current_user.id,  # from auth dependency
    #         content_json=result["content_json"],
    #         citations_json=result["citations_json"],
    #         agent_id=result["agent_id"],
    #         status=ReportStatus.DRAFT
    #     )
    #     db.add(report)
    #     await db.commit()
    #
    #     return report

    raise HTTPException(status_code=501, detail="Real implementation pending - use MOCK_MODE=true")


@router.patch("/{report_id}/review")
async def review_report(
    report_id: str,
    action: str = Query(..., regex="^(approve|reject)$"),
    review_notes: Optional[str] = Query(None)
):
    """
    Review report - approve or reject

    Flow:
    1. Get report
    2. Update status based on action
    3. Save review info
    """

    if settings.MOCK_MODE:
        await asyncio.sleep(settings.MOCK_DELAY)
        new_status = ReportStatus.APPROVED if action == "approve" else ReportStatus.REJECTED
        return {
            "report_id": report_id,
            "status": new_status,
            "reviewed_at": "2025-10-03T14:30:00Z",
            "message": f"Report {action}d successfully"
        }

    # TODO: Real implementation
    # from app.database import get_db
    #
    # async with get_db() as db:
    #     report = await db.get(Report, report_id)
    #     if not report:
    #         raise HTTPException(404, "Report not found")
    #
    #     if action == "approve":
    #         report.status = ReportStatus.APPROVED
    #     else:
    #         report.status = ReportStatus.REJECTED
    #
    #     report.reviewed_by_id = current_user.id
    #     report.review_notes = review_notes
    #     await db.commit()
    #
    #     return {"report_id": report_id, "status": report.status}

    raise HTTPException(status_code=501, detail="Real implementation pending - use MOCK_MODE=true")


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(report_id: str, report: ReportUpdate):
    """Update report (for review/approval)"""
    report_data = mock_generator.generate_report()
    report_data["id"] = report_id
    report_data.update(report.dict(exclude_unset=True))
    return ReportResponse(**report_data)


@router.get("/{report_id}/download")
async def download_report(report_id: str):
    """Download report in various formats"""
    return {
        "report_id": report_id,
        "formats": {
            "pdf": f"/api/v1/reports/{report_id}/download/pdf",
            "docx": f"/api/v1/reports/{report_id}/download/docx",
            "json": f"/api/v1/reports/{report_id}/download/json"
        }
    }