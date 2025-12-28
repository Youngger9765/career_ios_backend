"""Service layer for report CRUD operations and business logic"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, attributes

from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.report import Report, ReportStatus
from app.models.session import Session as SessionModel
from app.utils.report_formatters import create_formatter, unwrap_report


class ReportOperationsService:
    """Service for report CRUD operations and business logic"""

    def __init__(self, db: Session):
        self.db = db

    def list_reports(
        self,
        counselor: Counselor,
        tenant_id: str,
        skip: int = 0,
        limit: int = 20,
        client_id: Optional[UUID] = None,
    ) -> Tuple[List[Tuple[Report, str, int]], int]:
        """List all reports for counselor with pagination

        Args:
            counselor: Current counselor
            tenant_id: Tenant ID
            skip: Pagination offset
            limit: Items per page
            client_id: Optional filter by client ID

        Returns:
            Tuple of (list of (report, client_name, session_number), total_count)
        """
        # Base query - JOIN with session and client
        query = (
            select(Report, Client.name, SessionModel.session_number)
            .join(SessionModel, Report.session_id == SessionModel.id)
            .join(Client, Report.client_id == Client.id)
            .where(
                Report.created_by_id == counselor.id,
                Report.tenant_id == tenant_id,
            )
        )

        # Filter by client if provided
        if client_id:
            query = query.where(Report.client_id == client_id)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Order and paginate
        if client_id:
            query = query.order_by(SessionModel.session_number.asc())
        else:
            query = query.order_by(Report.created_at.desc())

        query = query.offset(skip).limit(limit)
        result = self.db.execute(query)
        rows = result.all()

        return rows, total

    def get_report_by_id(
        self,
        report_id: UUID,
        counselor: Counselor,
        tenant_id: str,
    ) -> Optional[Tuple[Report, str, int]]:
        """Get report by ID with permission check

        Args:
            report_id: Report UUID
            counselor: Current counselor
            tenant_id: Tenant ID

        Returns:
            Tuple of (report, client_name, session_number) or None if not found
        """
        result = self.db.execute(
            select(Report, Client.name, SessionModel.session_number)
            .join(SessionModel, Report.session_id == SessionModel.id)
            .join(Client, Report.client_id == Client.id)
            .where(
                Report.id == report_id,
                Report.created_by_id == counselor.id,
                Report.tenant_id == tenant_id,
            )
        )
        row = result.first()
        return row

    def format_report_content(
        self,
        report: Report,
        format_type: str,
        use_edited: bool = True,
    ) -> Dict[str, Any]:
        """Format report content in specified format

        Args:
            report: Report model instance
            format_type: Output format (json, markdown, html)
            use_edited: Use edited version if available

        Returns:
            Formatted content dictionary
        """
        formatter = create_formatter(format_type)

        # Use edited version if available and requested
        if use_edited and report.edited_content_json:
            report_data = report.edited_content_json
        else:
            report_data = report.content_json

        # Extract actual report content from wrapper
        formatted_content = formatter.format(unwrap_report(report_data))

        return {
            "report_id": str(report.id),
            "format": format_type,
            "formatted_content": formatted_content,
            "is_edited": use_edited and report.edited_content_json is not None,
            "edited_at": report.edited_at if report.edited_content_json else None,
        }

    def update_report(
        self,
        report_id: UUID,
        edited_content_markdown: str,
        counselor: Counselor,
        tenant_id: str,
    ) -> Report:
        """Update report with edited content

        Args:
            report_id: Report UUID
            edited_content_markdown: Edited markdown content
            counselor: Current counselor
            tenant_id: Tenant ID

        Returns:
            Updated report

        Raises:
            HTTPException: If report not found or validation fails
        """
        result = self.db.execute(
            select(Report).where(
                Report.id == report_id,
                Report.created_by_id == counselor.id,
                Report.tenant_id == tenant_id,
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found",
            )

        # Validate markdown content
        if not edited_content_markdown or edited_content_markdown.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide edited_content_markdown",
            )

        try:
            # Update edited_content_markdown
            report.edited_content_markdown = edited_content_markdown
            attributes.flag_modified(report, "edited_content_markdown")

            # Update metadata
            report.edited_at = datetime.now(timezone.utc).isoformat()
            report.edit_count = (report.edit_count or 0) + 1

            # Flush and commit
            self.db.flush()
            self.db.commit()

            # Verify the data was saved
            verification_result = self.db.execute(
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
            print(
                f"  - edited_content_json present: {bool(verified_report.edited_content_json)}"
            )
            print(
                f"  - edited_content_markdown length: {len(verified_report.edited_content_markdown) if verified_report.edited_content_markdown else 0}"
            )
            print(f"  - edited_at: {verified_report.edited_at}")
            print(f"  - edit_count: {verified_report.edit_count}")

            return verified_report

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            print(f"[ERROR] Failed to update report {report_id}: {str(e)}")
            import traceback

            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update report: {str(e)}",
            )

    def validate_session_and_get_data(
        self,
        session_id: UUID,
        counselor: Counselor,
        tenant_id: str,
    ) -> Optional[Tuple[SessionModel, Client, Case]]:
        """Validate session exists and belongs to counselor

        Args:
            session_id: Session UUID
            counselor: Current counselor
            tenant_id: Tenant ID

        Returns:
            Tuple of (session, client, case) or None if not found
        """
        result = self.db.execute(
            select(SessionModel, Client, Case)
            .join(Case, SessionModel.case_id == Case.id)
            .join(Client, Case.client_id == Client.id)
            .where(
                SessionModel.id == session_id,
                Client.counselor_id == counselor.id,
                Client.tenant_id == tenant_id,
            )
        )
        row = result.first()
        return row

    def check_existing_report(self, session_id: UUID) -> Optional[Tuple[Report, bool]]:
        """Check if report already exists for session

        Args:
            session_id: Session UUID

        Returns:
            Tuple of (existing_report, should_skip) or None if no existing report
            should_skip is True if report is already processing/draft
        """
        existing_report_result = self.db.execute(
            select(Report)
            .where(Report.session_id == session_id)
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        existing_report = existing_report_result.scalar_one_or_none()

        if not existing_report:
            return None

        # If PROCESSING or DRAFT, skip new generation
        if existing_report.status in [ReportStatus.PROCESSING, ReportStatus.DRAFT]:
            return existing_report, True

        # If FAILED, delete old report and allow retry
        if existing_report.status == ReportStatus.FAILED:
            self.db.delete(existing_report)
            self.db.commit()
            return None

        return existing_report, False

    def create_report_record(
        self,
        session_id: UUID,
        client_id: UUID,
        counselor: Counselor,
        tenant_id: str,
        report_type: str,
        rag_system: str,
    ) -> Report:
        """Create new report record with processing status

        Args:
            session_id: Session UUID
            client_id: Client UUID
            counselor: Current counselor
            tenant_id: Tenant ID
            report_type: Report type (enhanced/legacy)
            rag_system: RAG system (openai/gemini)

        Returns:
            Created report record
        """
        report = Report(
            session_id=session_id,
            client_id=client_id,
            created_by_id=counselor.id,
            tenant_id=tenant_id,
            version=1,
            status=ReportStatus.PROCESSING,
            mode=report_type,
            ai_model="gpt-4.1-mini"
            if rag_system == "openai"
            else "gemini-3-flash-preview",
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report
