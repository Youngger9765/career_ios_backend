"""
Analysis Log Service - Handles analysis logs CRUD logic.

Extracted from sessions.py to reduce endpoint complexity.
"""
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session


class AnalysisLogService:
    """Service for managing session analysis logs"""

    def __init__(self, db: DBSession):
        self.db = db

    def get_session_analysis_logs(
        self, session_id: UUID, current_user: Counselor, tenant_id: str
    ) -> Optional[List[Dict]]:
        """
        Get all analysis logs for a session with authorization check.

        Args:
            session_id: Session UUID
            current_user: Authenticated counselor
            tenant_id: Tenant ID

        Returns:
            List of log entries with log_index added, or None if session not found
        """
        # Fetch session with authorization check
        result = self.db.execute(
            select(Session, Client, Case)
            .join(Case, Session.case_id == Case.id)
            .join(Client, Case.client_id == Client.id)
            .where(
                Session.id == session_id,
                Client.counselor_id == current_user.id,
                Client.tenant_id == tenant_id,
                Session.deleted_at.is_(None),
                Case.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
        )
        row = result.first()

        if not row:
            return None

        session = row[0]

        # Get analysis_logs (defaults to empty list if None)
        logs_data = session.analysis_logs or []

        # Convert to dict format with log indices
        log_entries = [
            {
                "log_index": idx,
                "analyzed_at": log.get("analyzed_at", ""),
                "transcript_segment": log.get("transcript_segment", ""),
                "keywords": log.get("keywords", []),
                "categories": log.get("categories", []),
                "confidence": log.get("confidence", 0.0),
                "counselor_insights": log.get("counselor_insights", ""),
                "counselor_id": log.get("counselor_id", ""),
                "fallback": log.get("fallback", False),
            }
            for idx, log in enumerate(logs_data)
        ]

        return log_entries

    def delete_analysis_log(
        self, session_id: UUID, log_index: int, current_user: Counselor, tenant_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Delete a specific analysis log entry.

        Args:
            session_id: Session UUID
            log_index: Index of log to delete (0-based)
            current_user: Authenticated counselor
            tenant_id: Tenant ID

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
            - (True, None) if deleted successfully
            - (False, "not_found") if session not found or unauthorized
            - (False, "invalid_index: <details>") if invalid index
        """
        # Fetch session with authorization check
        result = self.db.execute(
            select(Session, Client, Case)
            .join(Case, Session.case_id == Case.id)
            .join(Client, Case.client_id == Client.id)
            .where(
                Session.id == session_id,
                Client.counselor_id == current_user.id,
                Client.tenant_id == tenant_id,
                Session.deleted_at.is_(None),
                Case.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
        )
        row = result.first()

        if not row:
            return False, "not_found"

        session = row[0]

        # Get analysis_logs
        logs_data = session.analysis_logs or []

        # Validate index
        if log_index < 0 or log_index >= len(logs_data):
            error_msg = (
                f"Invalid log index: {log_index}. Valid range: 0-{len(logs_data)-1}"
            )
            return False, f"invalid_index: {error_msg}"

        # Remove the log entry
        logs_data.pop(log_index)

        # Update session
        session.analysis_logs = logs_data

        # Mark as modified for SQLAlchemy to detect changes
        flag_modified(session, "analysis_logs")

        self.db.commit()

        return True, None
