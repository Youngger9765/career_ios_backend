"""
Session Service - Business logic for session management
Refactored from app/api/sessions.py to follow Service Layer pattern
"""
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.report import Report
from app.models.session import Session
from app.repositories.session_repository import SessionRepository
from app.schemas.session import (
    SessionCreateRequest,
    SessionUpdateRequest,
)
from app.services.helpers.session_transcript import (
    aggregate_transcript_from_recordings,
    calculate_timerange_from_recordings,
    process_recordings_data,
    process_transcript_data,
)
from app.services.helpers.session_validation import parse_date, parse_datetime


class SessionService:
    """Service layer for session business logic"""

    def __init__(self, db: DBSession):
        self.db = db
        self.session_repo = SessionRepository(db)

    def create_session(
        self,
        request: SessionCreateRequest,
        current_user: Counselor,
        tenant_id: str,
    ) -> Session:
        """Create a new counseling session with automatic session numbering."""
        case = self.session_repo.get_case_by_id(request.case_id, tenant_id)
        if not case:
            raise ValueError("Case not found or access denied")
        start_time = parse_datetime(request.start_time) if request.start_time else None
        end_time = parse_datetime(request.end_time) if request.end_time else None
        session_date = parse_date(request.session_date)
        session_number, needs_renumbering = self._calculate_session_number_for_new(
            case.id, start_time if start_time else session_date
        )
        if needs_renumbering:
            self.session_repo.update_session_numbers(case.id, session_number)
        _client = self.session_repo.get_client_by_id(case.client_id)
        full_transcript = process_transcript_data(request)
        recordings_data = process_recordings_data(request)
        if recordings_data:
            calc_start, calc_end = calculate_timerange_from_recordings(recordings_data)
            if calc_start:
                start_time = calc_start
            if calc_end:
                end_time = calc_end
        session = self.session_repo.create(
            case_id=case.id,
            tenant_id=tenant_id,
            session_number=session_number,
            session_date=session_date,
            name=request.name,
            start_time=start_time,
            end_time=end_time,
            transcript_text=full_transcript,
            transcript_sanitized=full_transcript,  # TODO: Integrate sanitizer service
            source_type="transcript",
            duration_minutes=request.duration_minutes,
            notes=request.notes,
            reflection=request.reflection or {},
            recordings=recordings_data,
        )

        self.db.commit()
        self.db.refresh(session)
        return session

    def get_session(
        self,
        session_id: UUID,
        current_user: Counselor,
        tenant_id: str,
    ) -> Optional[Session]:
        """Get a session with authorization check."""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            return None
        if not self.session_repo.check_authorization(session, current_user, tenant_id):
            raise PermissionError("Not authorized to access this session")
        return session

    def get_session_with_details(
        self,
        session_id: UUID,
        current_user: Counselor,
        tenant_id: str,
    ) -> Optional[Tuple[Session, Client, Case, bool]]:
        """Get session with joined Client, Case, and has_report flag."""
        result = self.db.execute(
            select(Session, Client, Case, Report.id.label("report_id"))
            .join(Case, Session.case_id == Case.id)
            .join(Client, Case.client_id == Client.id)
            .outerjoin(Report, Report.session_id == Session.id)
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
        session, client, case, report_id = row
        has_report = report_id is not None
        return (session, client, case, has_report)

    def get_session_with_context(
        self,
        session_id: UUID,
        current_user: Counselor,
        tenant_id: str,
    ) -> Optional[Tuple[Session, Client, Case]]:
        """Get session with joined Client and Case for keyword analysis."""
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
        return row if row else None

    def list_sessions(
        self,
        counselor: Counselor,
        tenant_id: str,
        client_id: Optional[UUID] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Tuple], int]:
        """List sessions with filtering and pagination."""
        return self.session_repo.list_sessions(
            counselor_id=counselor.id,
            tenant_id=tenant_id,
            client_id=client_id,
            search=search,
            skip=skip,
            limit=limit,
        )

    def update_session(
        self,
        session_id: UUID,
        request: SessionUpdateRequest,
        current_user: Counselor,
        tenant_id: str,
    ) -> Tuple[Session, Client, Case, bool]:
        """Update a session with authorization check and return full details."""
        result = self.get_session_with_details(session_id, current_user, tenant_id)
        if not result:
            raise ValueError("Session not found")

        session, client, case, _ = result

        # Track if time changed (for session number recalculation)
        time_changed = False
        old_session_number = session.session_number

        # Update session_date
        if request.session_date is not None:
            new_session_date = parse_date(request.session_date)
            if new_session_date != session.session_date:
                time_changed = True
                session.session_date = new_session_date

        # Update start_time
        if request.start_time is not None:
            new_start_time = parse_datetime(request.start_time)
            if new_start_time != session.start_time:
                time_changed = True
            session.start_time = new_start_time

        # Update end_time
        if request.end_time is not None:
            new_end_time = parse_datetime(request.end_time)
            session.end_time = new_end_time

        # Process recordings and transcript
        if request.recordings is not None:
            session.recordings = request.recordings
            if request.recordings:
                # Aggregate transcript from recordings
                full_transcript = aggregate_transcript_from_recordings(
                    request.recordings
                )
                session.transcript_text = full_transcript
                session.transcript_sanitized = full_transcript

                # Recalculate time range from recordings
                calc_start, calc_end = calculate_timerange_from_recordings(
                    request.recordings
                )
                if calc_start:
                    session.start_time = calc_start
                    time_changed = False  # Recordings-calculated time doesn't count
                if calc_end:
                    session.end_time = calc_end
                    time_changed = False  # Recordings-calculated time doesn't count

        elif request.transcript is not None:
            session.transcript_text = request.transcript
            session.transcript_sanitized = request.transcript

        # Handle name field
        update_dict = request.model_dump(exclude_unset=True)
        if "name" in update_dict:
            session.name = update_dict["name"]

        if request.notes is not None:
            session.notes = request.notes

        if request.duration_minutes is not None:
            session.duration_minutes = request.duration_minutes

        if request.reflection is not None:
            session.reflection = request.reflection

        # Recalculate session_number if time changed
        if time_changed:
            self._renumber_session_on_time_change(session, old_session_number, case.id)

        self.db.commit()
        self.db.refresh(session)

        # Check for reports
        has_report = self.session_repo.has_reports(session.id)

        return (session, client, case, has_report)

    def delete_session(
        self,
        session_id: UUID,
        current_user: Counselor,
        tenant_id: str,
    ) -> None:
        """Soft delete a session with authorization check."""
        session = self.get_session(session_id, current_user, tenant_id)
        if not session:
            raise ValueError("Session not found")

        # Check if session has reports
        if self.session_repo.has_reports(session.id):
            raise ValueError("Cannot delete session with associated reports")

        # Soft delete
        self.session_repo.soft_delete(session)
        self.db.commit()

    # Helper methods (extracted from sessions.py lines 29-116)

    def _calculate_session_number_for_new(
        self, case_id: UUID, new_datetime: datetime
    ) -> Tuple[int, bool]:
        """Calculate session number for a new session."""
        existing_sessions = self.session_repo.get_sessions_by_case(case_id)

        if not existing_sessions:
            return 1, False

        session_number = 1
        needs_renumbering = False

        for existing in existing_sessions:
            existing_time = (
                existing.start_time if existing.start_time else existing.session_date
            )
            if new_datetime > existing_time:
                session_number += 1
            else:
                # Inserting in the middle, need to renumber
                needs_renumbering = True
                break

        return session_number, needs_renumbering

    def _calculate_session_number(
        self, new_datetime: datetime, existing_sessions: List[Session]
    ) -> Tuple[int, bool]:
        """Calculate session number for a session being inserted."""
        if not existing_sessions:
            return 1, False

        session_number = 1
        needs_renumbering = False

        for existing in existing_sessions:
            existing_time = (
                existing.start_time if existing.start_time else existing.session_date
            )
            if new_datetime > existing_time:
                session_number += 1
            else:
                needs_renumbering = True
                break

        return session_number, needs_renumbering

    def _renumber_session_on_time_change(
        self, session: Session, old_session_number: int, case_id: UUID
    ) -> None:
        """Renumber sessions when session time changes."""
        from sqlalchemy import func

        # Determine new sort time (start_time takes precedence)
        new_sort_time = (
            session.start_time if session.start_time else session.session_date
        )

        # 1. Temporarily set current session number to 0
        session.session_number = 0
        self.db.flush()

        # 2. Decrement session numbers > old_session_number
        self.db.execute(
            Session.__table__.update()  # type: ignore[attr-defined]
            .where(Session.case_id == case_id)
            .where(Session.session_number > old_session_number)
            .values(session_number=Session.session_number - 1)
        )
        self.db.flush()

        # 3. Query all other sessions in this case, ordered by time
        result = self.db.execute(
            select(Session.start_time, Session.session_date)
            .where(Session.case_id == case_id)
            .where(Session.id != session.id)
            .order_by(func.coalesce(Session.start_time, Session.session_date).asc())
        )
        existing_times = [(row[0] if row[0] else row[1]) for row in result.all()]

        # 4. Calculate new session number based on chronological position
        new_session_number = 1
        for existing_time in existing_times:
            if new_sort_time > existing_time:
                new_session_number += 1
            else:
                break

        # 5. Increment session numbers >= new_session_number (exclude current)
        self.db.execute(
            Session.__table__.update()  # type: ignore[attr-defined]
            .where(Session.case_id == case_id)
            .where(Session.session_number >= new_session_number)
            .where(Session.id != session.id)
            .values(session_number=Session.session_number + 1)
        )
        self.db.flush()

        # 6. Assign new session number to current session
        session.session_number = new_session_number
