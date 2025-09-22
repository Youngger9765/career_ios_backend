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
async def generate_report(session_id: str):
    """Generate AI report for session"""
    # Simulate AI processing delay
    if settings.MOCK_MODE:
        await asyncio.sleep(settings.MOCK_DELAY * 3)  # Longer delay for AI
    
    report = mock_generator.generate_report(session_id)
    return ReportResponse(**report)


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