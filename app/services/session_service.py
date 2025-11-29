"""
Session Service - Business logic for session management
Refactored from app/api/sessions.py to follow Service Layer pattern
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from app.models.counselor import Counselor
from app.models.session import Session
from app.repositories.session_repository import SessionRepository
from app.schemas.session import (
    SessionCreateRequest,
    SessionUpdateRequest,
)


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
        """
        Create a new counseling session with automatic session numbering.

        Business logic extracted from sessions.py lines 287-493.
        """
        # Validate case exists and belongs to tenant
        case = self.session_repo.get_case_by_id(request.case_id, tenant_id)
        if not case:
            raise ValueError("Case not found or access denied")

        # Parse dates and times
        start_time = (
            self._parse_datetime(request.start_time) if request.start_time else None
        )
        end_time = self._parse_datetime(request.end_time) if request.end_time else None
        session_date = self._parse_date(request.session_date)

        # Calculate session number based on chronological order
        session_number, needs_renumbering = self._calculate_session_number_for_new(
            case.id, start_time if start_time else session_date
        )

        # Renumber existing sessions if inserting in the middle
        if needs_renumbering:
            self.session_repo.update_session_numbers(case.id, session_number)

        # Get client info for response (reserved for future use)
        _client = self.session_repo.get_client_by_id(case.client_id)

        # Process recordings and transcript
        full_transcript = self._process_transcript_data(request)
        recordings_data = self._process_recordings_data(request)

        # Calculate time range from recordings if provided
        if recordings_data:
            calc_start, calc_end = self._calculate_timerange_from_recordings(
                recordings_data
            )
            if calc_start:
                start_time = calc_start
            if calc_end:
                end_time = calc_end

        # Create the session
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
        """
        Get a session with authorization check.

        Business logic extracted from sessions.py lines 714-784.
        """
        session = self.session_repo.get_by_id(session_id)
        if not session:
            return None

        # Check authorization
        if not self.session_repo.check_authorization(session, current_user, tenant_id):
            raise PermissionError("Not authorized to access this session")

        return session

    def list_sessions(
        self,
        counselor: Counselor,
        tenant_id: str,
        client_id: Optional[UUID] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Tuple], int]:
        """
        List sessions with filtering and pagination.

        Business logic extracted from sessions.py lines 495-597.

        Returns: (list of (Session, Case, Client, has_report) tuples, total_count)
        """
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
    ) -> Session:
        """
        Update a session with authorization check.

        Business logic extracted from sessions.py lines 787-1009.
        """
        session = self.get_session(session_id, current_user, tenant_id)
        if not session:
            raise ValueError("Session not found")

        # Prepare update data
        update_data = {}

        if request.session_date is not None:
            update_data["session_date"] = self._parse_date(request.session_date)

        if request.start_time is not None:
            update_data["start_time"] = self._parse_datetime(request.start_time)

        if request.end_time is not None:
            update_data["end_time"] = self._parse_datetime(request.end_time)

        # Handle name field - always update if provided
        update_dict = request.model_dump(exclude_unset=True)
        if "name" in update_dict:
            update_data["name"] = update_dict["name"]

        if request.notes is not None:
            update_data["notes"] = request.notes

        if request.duration_minutes is not None:
            update_data["duration_minutes"] = request.duration_minutes

        if request.reflection is not None:
            update_data["reflection"] = request.reflection

        # Process recordings and transcript updates
        if request.recordings is not None:
            recordings_data = [
                r.model_dump() if hasattr(r, "model_dump") else r
                for r in request.recordings
            ]
            update_data["recordings"] = recordings_data

            if recordings_data:
                # Aggregate transcript from recordings
                full_transcript = self._aggregate_transcript_from_recordings(
                    recordings_data
                )
                update_data["transcript_text"] = full_transcript
                update_data["transcript_sanitized"] = full_transcript

                # Recalculate time range
                calc_start, calc_end = self._calculate_timerange_from_recordings(
                    recordings_data
                )
                if calc_start:
                    update_data["start_time"] = calc_start
                if calc_end:
                    update_data["end_time"] = calc_end

        elif request.transcript is not None:
            update_data["transcript_text"] = request.transcript
            update_data["transcript_sanitized"] = request.transcript

        # Update the session
        updated_session = self.session_repo.update(session, **update_data)
        self.db.commit()
        self.db.refresh(updated_session)

        return updated_session

    def delete_session(
        self,
        session_id: UUID,
        current_user: Counselor,
        tenant_id: str,
    ) -> None:
        """
        Soft delete a session with authorization check.

        Business logic extracted from sessions.py lines 1012-1089.
        """
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

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime with timezone"""
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string with various formats"""
        time_str = datetime_str.strip()
        if " " in time_str or "T" in time_str or len(time_str) > 10:
            dt = datetime.fromisoformat(time_str.replace(" ", "T"))
        else:
            raise ValueError("datetime must include date (format: YYYY-MM-DD HH:MM)")

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def _calculate_session_number_for_new(
        self, case_id: UUID, new_datetime: datetime
    ) -> Tuple[int, bool]:
        """
        Calculate session number for a new session.
        Returns (session_number, needs_renumbering).
        """
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
        """
        Calculate session number for a session being inserted.
        Used by tests and internal logic.
        """
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

    def _process_transcript_data(self, request: SessionCreateRequest) -> Optional[str]:
        """Process transcript from request"""
        if request.recordings:
            return self._aggregate_transcript_from_recordings(request.recordings)
        return request.transcript

    def _process_recordings_data(self, request: SessionCreateRequest) -> List[dict]:
        """Convert recordings to dict format for storage"""
        if not request.recordings:
            return []

        recordings_dicts = []
        for r in request.recordings:
            if isinstance(r, dict):
                recordings_dicts.append(r)
            else:
                recordings_dicts.append(r.model_dump())
        return recordings_dicts

    def _aggregate_transcript_from_recordings(self, recordings: List) -> str:
        """
        Aggregate transcript text from recording segments.
        Helper function extracted from sessions.py lines 31-63.
        """
        if not recordings:
            return ""

        def get_segment_number(r):
            if isinstance(r, dict):
                return r.get("segment_number", 0)
            else:
                return getattr(r, "segment_number", 0)

        sorted_recordings = sorted(recordings, key=get_segment_number)

        transcripts = []
        for r in sorted_recordings:
            if isinstance(r, dict):
                text = r.get("transcript_text", "")
            else:
                text = getattr(r, "transcript_text", "")
            if text:
                transcripts.append(text)

        return "\n\n".join(transcripts)

    def _calculate_timerange_from_recordings(
        self, recordings: List
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Calculate session time range from recordings.
        Helper function extracted from sessions.py lines 66-115.
        """
        if not recordings:
            return None, None

        start_times = []
        end_times = []

        for r in recordings:
            if isinstance(r, dict):
                start_str = r.get("start_time")
                end_str = r.get("end_time")
            else:
                start_str = getattr(r, "start_time", None)
                end_str = getattr(r, "end_time", None)

            if start_str:
                if isinstance(start_str, str):
                    start_dt = datetime.fromisoformat(start_str.replace(" ", "T"))
                    if start_dt.tzinfo is None:
                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                    start_times.append(start_dt)
                elif isinstance(start_str, datetime):
                    start_times.append(start_str)

            if end_str:
                if isinstance(end_str, str):
                    end_dt = datetime.fromisoformat(end_str.replace(" ", "T"))
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                    end_times.append(end_dt)
                elif isinstance(end_str, datetime):
                    end_times.append(end_str)

        session_start = min(start_times) if start_times else None
        session_end = max(end_times) if end_times else None

        return session_start, session_end
