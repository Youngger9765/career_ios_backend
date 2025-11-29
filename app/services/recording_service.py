"""
Recording Service - Business logic for recording management
Extracted from app/api/sessions.py
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from app.models.session import Session
from app.repositories.session_repository import SessionRepository
from app.schemas.session import AppendRecordingRequest, RecordingSegment


class RecordingService:
    """Service for managing session recordings"""

    def __init__(self, db: DBSession):
        self.db = db
        self.session_repo = SessionRepository(db)

    def append_recording(
        self,
        session_id: UUID,
        request: AppendRecordingRequest,
        counselor_id: UUID,
        tenant_id: str,
    ) -> tuple[Session, RecordingSegment, int]:
        """
        Append a new recording segment to a session.

        Returns: (updated_session, new_recording, total_recordings)
        """
        # Get and verify session
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError("Session not found")

        # Verify authorization
        case = self.session_repo.get_case_by_id(session.case_id, tenant_id)
        if not case:
            raise ValueError("Case not found")

        client = self.session_repo.get_client_by_id(case.client_id)
        if not client or client.counselor_id != counselor_id:
            raise PermissionError("Not authorized")

        # Refresh to get latest data
        self.db.refresh(session)

        # Get existing recordings
        existing_recordings = list(session.recordings) if session.recordings else []

        # Calculate new segment number
        if existing_recordings:
            max_segment = max(r.get("segment_number", 0) for r in existing_recordings)
            new_segment_number = max_segment + 1
        else:
            new_segment_number = 1

        # Create new recording segment
        new_recording = {
            "segment_number": new_segment_number,
            "start_time": request.start_time,
            "end_time": request.end_time,
            "duration_seconds": request.duration_seconds,
            "transcript_text": request.transcript_text,
            "transcript_sanitized": request.transcript_sanitized
            or request.transcript_text,
        }

        # Append to recordings
        existing_recordings.append(new_recording)
        session.recordings = existing_recordings

        # Re-aggregate transcript
        full_transcript = self._aggregate_transcript_from_recordings(
            existing_recordings
        )
        session.transcript_text = full_transcript
        session.transcript_sanitized = full_transcript

        # Update session time range
        session_start, session_end = self._calculate_timerange_from_recordings(
            existing_recordings
        )
        if session_start:
            session.start_time = session_start
        if session_end:
            session.end_time = session_end

        self.db.commit()
        self.db.refresh(session)

        return session, RecordingSegment(**new_recording), len(existing_recordings)

    def _aggregate_transcript_from_recordings(self, recordings: List[dict]) -> str:
        """Aggregate transcript text from recording segments"""
        if not recordings:
            return ""

        sorted_recordings = sorted(recordings, key=lambda r: r.get("segment_number", 0))

        transcripts = []
        for r in sorted_recordings:
            text = r.get("transcript_text", "")
            if text:
                transcripts.append(text)

        return "\n\n".join(transcripts)

    def _calculate_timerange_from_recordings(
        self, recordings: List[dict]
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """Calculate session time range from recordings"""
        if not recordings:
            return None, None

        start_times = []
        end_times = []

        for r in recordings:
            start_str = r.get("start_time")
            end_str = r.get("end_time")

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
