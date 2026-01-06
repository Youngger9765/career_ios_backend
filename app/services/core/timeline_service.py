"""
Timeline Service - Business logic for session timeline
Extracted from app/api/sessions.py
"""
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models.case import Case
from app.models.client import Client
from app.models.report import Report, ReportStatus
from app.models.session import Session
from app.schemas.session import TimelineSessionItem


class TimelineService:
    """Service for managing session timeline"""

    def __init__(self, db: DBSession):
        self.db = db

    def get_session_timeline(
        self,
        client_id: UUID,
        counselor_id: UUID,
        tenant_id: str,
    ) -> tuple[Client, List[TimelineSessionItem]]:
        """
        Get session timeline for a client.

        Returns: (client, timeline_items)
        """
        # Verify client exists and belongs to counselor
        client_result = self.db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.counselor_id == counselor_id,
                Client.tenant_id == tenant_id,
            )
        )
        client = client_result.scalar_one_or_none()

        if not client:
            raise ValueError("Client not found")

        # Query all sessions with reports
        query = (
            select(Session, Report.id.label("report_id"))
            .join(Case, Session.case_id == Case.id)
            .outerjoin(
                Report,
                (Report.session_id == Session.id)
                & (Report.status == ReportStatus.DRAFT),
            )
            .where(Case.client_id == client_id, Session.tenant_id == tenant_id)
            .order_by(Session.session_date.asc())
        )

        result = self.db.execute(query)
        rows = result.all()

        # Build timeline items
        timeline_items = []
        for session, report_id in rows:
            # Format time range
            time_range = None
            if session.start_time and session.end_time:
                start = session.start_time.strftime("%H:%M")
                end = session.end_time.strftime("%H:%M")
                time_range = f"{start}-{end}"

            timeline_items.append(
                TimelineSessionItem(
                    session_id=session.id,
                    session_number=session.session_number,
                    date=session.session_date.strftime("%Y-%m-%d"),
                    time_range=time_range,
                    summary=session.summary,
                    has_report=report_id is not None,
                    report_id=report_id,
                )
            )

        return client, timeline_items
