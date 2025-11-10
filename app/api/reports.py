"""
Reports query API
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, attributes

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.report import Report, ReportStatus
from app.models.session import Session as SessionModel
from app.schemas.report import (
    ReportListResponse,
    ReportResponse,
    ReportUpdateRequest,
    ReportUpdateResponse,
)
from app.utils.report_formatters import create_formatter, unwrap_report

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


async def _generate_report_background(
    report_id: UUID,
    session_id: UUID,
    transcript: str,
    report_type: str,
    rag_system: str,
):
    """
    背景任務:生成報告內容 + 會談摘要 (異步版本)

    Args:
        report_id: Report UUID
        session_id: Session UUID (用於更新摘要)
        transcript: 逐字稿
        report_type: 報告類型 (enhanced/legacy)
        rag_system: RAG 系統 (openai/gemini)
    """
    from app.api.rag_report import ReportRequest, generate_report as rag_generate
    from app.core.database import SessionLocal
    from app.services.session_summary_service import session_summary_service

    db = SessionLocal()
    try:
        # 查詢 report
        result = db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()

        if not report:
            return

        # 生成報告
        rag_request = ReportRequest(
            transcript=transcript,
            num_participants=2,
            rag_system=rag_system,
            top_k=7,
            similarity_threshold=0.25,
            output_format="json",
            mode=report_type,
        )

        # 異步調用 RAG 生成 (在背景執行)
        report_data = await rag_generate(rag_request, db)

        # 生成 Markdown 格式
        markdown_formatter = create_formatter("markdown")
        # Extract actual report from wrapper (fix for wrapped JSON bug)
        content_markdown = markdown_formatter.format(unwrap_report(report_data))

        # 更新 report
        report.content_json = report_data
        report.content_markdown = content_markdown
        report.citations_json = report_data.get("theories_cited", [])
        report.prompt_tokens = report_data.get("token_usage", {}).get("prompt_tokens", 0)
        report.completion_tokens = report_data.get("token_usage", {}).get("completion_tokens", 0)
        report.quality_score = report_data.get("quality_summary", {}).get("overall_score")
        report.quality_grade = report_data.get("quality_summary", {}).get("grade")
        report.quality_strengths = report_data.get("quality_summary", {}).get("strengths")
        report.quality_weaknesses = report_data.get("quality_summary", {}).get("improvements_needed")
        report.status = ReportStatus.DRAFT  # 生成完成,狀態改為 draft

        db.commit()

        # 【新增】異步生成會談摘要並更新 session
        try:
            summary = await session_summary_service.generate_summary(transcript, max_length=100)
            if summary:
                # 更新 session 的 summary 欄位
                session_result = db.execute(
                    select(SessionModel).where(SessionModel.id == session_id)
                )
                session_obj = session_result.scalar_one_or_none()
                if session_obj:
                    session_obj.summary = summary
                    db.commit()
        except Exception as summary_error:
            # 摘要生成失敗不影響報告生成
            print(f"Warning: Failed to generate session summary: {summary_error}")

    except Exception as e:
        # 生成失敗,標記為 failed
        if report:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            db.commit()
    finally:
        db.close()


class GenerateReportRequest(BaseModel):
    """Request schema for generating report"""

    session_id: UUID  # 必填：使用現有逐字稿生成報告
    report_type: str = "enhanced"  # enhanced | legacy
    rag_system: str = "openai"  # openai | gemini


class ProcessingStatus(BaseModel):
    """報告處理中的狀態"""
    status: str  # "processing"
    message: str


class GenerateReportResponse(BaseModel):
    """異步報告生成響應 (HTTP 202)"""

    session_id: UUID
    report_id: UUID
    report: ProcessingStatus  # 處理中狀態
    quality_summary: None = None  # 處理中時一定是 None


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
    # Base query - JOIN with session and client to get client_name and session_number
    query = (
        select(Report, Client.name, SessionModel.session_number)
        .join(SessionModel, Report.session_id == SessionModel.id)
        .join(Client, Report.client_id == Client.id)
        .where(
            Report.created_by_id == current_user.id,
            Report.tenant_id == tenant_id,
        )
    )

    # Filter by client if provided
    if client_id:
        query = query.where(Report.client_id == client_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results - order by session_number when filtering by client_id
    if client_id:
        query = query.order_by(SessionModel.session_number.asc())
    else:
        query = query.order_by(Report.created_at.desc())

    query = query.offset(skip).limit(limit)
    result = db.execute(query)
    rows = result.all()

    # Build response with client_name and session_number
    items = []
    for report, client_name, session_number in rows:
        report_dict = ReportResponse.model_validate(report).model_dump()
        report_dict['client_name'] = client_name
        report_dict['session_number'] = session_number
        items.append(ReportResponse(**report_dict))

    return ReportListResponse(
        total=total,
        items=items,
    )


@router.get("/{report_id}")
def get_report(
    report_id: UUID,
    format: Optional[str] = Query(None, pattern="^(json|markdown|html)$"),
    use_edited: bool = Query(True, description="Use edited version if available"),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
):
    """
    Get report by ID with optional formatting

    **⭐️ NEW: Markdown fields included in response**
    - content_markdown: AI-generated Markdown (always present after generation)
    - edited_content_markdown: Edited Markdown (present after editing)

    Args:
        report_id: Report UUID
        format: Output format - None/json (default, returns full metadata), markdown, or html
        use_edited: Use edited version if available when formatting (default: True)
        current_user: Current authenticated counselor
        tenant_id: Tenant ID
        db: Session: Database session

    Returns:
        - If format is None or 'json': ReportResponse (full metadata + JSON + Markdown)
        - If format is 'markdown' or 'html': Formatted content dict (for backward compatibility)

    Examples:
        GET /api/v1/reports/{id} → Full JSON metadata (includes content_markdown, edited_content_markdown)
        GET /api/v1/reports/{id}?format=json → Same as above
        GET /api/v1/reports/{id}?format=markdown → Dynamically formatted Markdown (legacy)
        GET /api/v1/reports/{id}?format=html → Dynamically formatted HTML (legacy)

    **Recommended for iOS:**
    Use default format (no query param) and access `content_markdown` or `edited_content_markdown` directly.
    """
    result = db.execute(
        select(Report, Client.name, SessionModel.session_number)
        .join(SessionModel, Report.session_id == SessionModel.id)
        .join(Client, Report.client_id == Client.id)
        .where(
            Report.id == report_id,
            Report.created_by_id == current_user.id,
            Report.tenant_id == tenant_id,
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    report, client_name, session_number = row

    # If no format specified or format is 'json', return full metadata
    if not format or format == 'json':
        report_dict = ReportResponse.model_validate(report).model_dump()
        report_dict['client_name'] = client_name
        report_dict['session_number'] = session_number
        return ReportResponse(**report_dict)

    # Otherwise, return formatted content
    formatter = create_formatter(format)

    # Use edited version if available and requested, otherwise use AI original
    if use_edited and report.edited_content_json:
        report_data = report.edited_content_json
    else:
        report_data = report.content_json

    # Extract actual report content from wrapper
    formatted_content = formatter.format(unwrap_report(report_data))

    return {
        "report_id": str(report_id),
        "format": format,
        "formatted_content": formatted_content,
        "is_edited": use_edited and report.edited_content_json is not None,
        "edited_at": report.edited_at if report.edited_content_json else None,
    }


@router.patch("/{report_id}", response_model=ReportUpdateResponse)
def update_report(
    report_id: UUID,
    update_request: ReportUpdateRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ReportUpdateResponse:
    """
    Update report content (counselor edits)

    This endpoint automatically generates and saves both JSON and Markdown versions
    of the edited report.

    Args:
        report_id: Report UUID
        update_request: Updated report content (JSON format)
        current_user: Current authenticated counselor
        tenant_id: Tenant ID
        db: Database session

    Returns:
        Updated report with:
        - edited_content_json: The edited JSON content
        - edited_content_markdown: The edited Markdown content (auto-generated)
        - edited_at: Timestamp of the edit
        - edit_count: Number of edits made

    Raises:
        HTTPException: 404 if report not found, 500 if update fails
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

    try:
        # 前端可以傳 edited_content_json 或 edited_content_markdown，或兩者都傳
        if not update_request.edited_content_json and not update_request.edited_content_markdown:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either edited_content_json or edited_content_markdown",
            )

        # Update edited_content_json if provided
        if update_request.edited_content_json:
            report.edited_content_json = update_request.edited_content_json
            attributes.flag_modified(report, "edited_content_json")

        # Update edited_content_markdown if provided (前端直接傳)
        if update_request.edited_content_markdown:
            report.edited_content_markdown = update_request.edited_content_markdown
            attributes.flag_modified(report, "edited_content_markdown")
        # 如果只傳 JSON 沒傳 Markdown，自動生成（向後相容）
        elif update_request.edited_content_json:
            formatter = create_formatter("markdown")
            report_data = update_request.edited_content_json
            edited_markdown = formatter.format(unwrap_report(report_data))
            report.edited_content_markdown = edited_markdown
            attributes.flag_modified(report, "edited_content_markdown")

        # Update metadata
        report.edited_at = datetime.now(timezone.utc).isoformat()
        report.edit_count = (report.edit_count or 0) + 1

        # Explicitly flush to detect any database errors before commit
        db.flush()
        db.commit()

        # Verify the data was actually saved by querying it again
        verification_result = db.execute(
            select(Report).where(Report.id == report_id)
        )
        verified_report = verification_result.scalar_one_or_none()

        if not verified_report:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Report update failed: verification query returned no results",
            )

        # Log for debugging
        print(f"[DEBUG] Report {verified_report.id} updated and verified:")
        print(f"  - edited_content_json present: {bool(verified_report.edited_content_json)}")
        print(f"  - edited_content_markdown length: {len(verified_report.edited_content_markdown) if verified_report.edited_content_markdown else 0}")
        print(f"  - edited_at: {verified_report.edited_at}")
        print(f"  - edit_count: {verified_report.edit_count}")

        return ReportUpdateResponse(
            id=verified_report.id,
            edited_content_json=verified_report.edited_content_json,
            edited_content_markdown=verified_report.edited_content_markdown,
            edited_at=verified_report.edited_at,
            edit_count=verified_report.edit_count,
        )

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to update report {report_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update report: {str(e)}",
        )


@router.post("/generate", response_model=GenerateReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    request: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> GenerateReportResponse:
    """
    Generate counseling report from existing session (Async API)

    Workflow:
    1. 驗證 session 存在且屬於當前諮商師
    2. 創建 Report (status: "processing")
    3. 背景任務生成報告
    4. 立即返回 report_id 和狀態

    Args:
        request: Report generation request (requires session_id)
        background_tasks: FastAPI background tasks
        current_user: Current authenticated counselor
        tenant_id: Tenant ID
        db: Database session

    Returns:
        Report ID with status "processing"

    Raises:
        HTTPException: 404 if session not found, 500 if creation fails
    """
    try:
        # 驗證 session 存在且屬於當前諮商師
        result = db.execute(
            select(SessionModel, Client, Case)
            .join(Case, SessionModel.case_id == Case.id)
            .join(Client, Case.client_id == Client.id)
            .where(
                SessionModel.id == request.session_id,
                Client.counselor_id == current_user.id,
                Client.tenant_id == tenant_id,
            )
        )
        row = result.first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or access denied",
            )

        session, client, case = row
        transcript = session.transcript_text

        # Check if there's already a report for this session (processing or draft)
        existing_report_result = db.execute(
            select(Report)
            .where(Report.session_id == session.id)
            .where(Report.status.in_([ReportStatus.PROCESSING, ReportStatus.DRAFT]))
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        existing_report = existing_report_result.scalar_one_or_none()

        if existing_report:
            # Return existing report instead of creating a new one
            return GenerateReportResponse(
                session_id=session.id,
                report_id=existing_report.id,
                report=ProcessingStatus(
                    status=existing_report.status.value.lower(),
                    message=f"報告已存在（狀態：{existing_report.status.value}），返回現有報告"
                ),
                quality_summary=None,
            )

        # Step 3: Create report record with "processing" status
        report = Report(
            session_id=session.id,
            client_id=client.id,
            created_by_id=current_user.id,
            tenant_id=tenant_id,
            version=1,
            status=ReportStatus.PROCESSING,  # 狀態:生成中
            mode=request.report_type,
            ai_model=f"gpt-4.1-mini" if request.rag_system == "openai" else "gemini-2.5-flash",
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        # Step 4: 背景任務生成報告 + 摘要 (不阻塞)
        background_tasks.add_task(
            _generate_report_background,
            report_id=report.id,
            session_id=session.id,  # 傳入 session_id 用於生成摘要
            transcript=transcript,  # 使用上面準備好的 transcript 變數
            report_type=request.report_type,
            rag_system=request.rag_system,
        )

        # Step 5: 立即返回
        return GenerateReportResponse(
            session_id=session.id,
            report_id=report.id,
            report=ProcessingStatus(
                status="processing",
                message="報告生成中，請稍後查詢結果"
            ),
            quality_summary=None,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )
