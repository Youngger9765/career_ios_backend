"""
Session Transcript Processing Helpers
Extracted from session_service.py to reduce file size
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from app.schemas.session import SessionCreateRequest


def process_transcript_data(request: SessionCreateRequest) -> Optional[str]:
    """Process transcript from request"""
    if request.recordings:
        return aggregate_transcript_from_recordings(request.recordings)
    return request.transcript


def process_recordings_data(request: SessionCreateRequest) -> List[dict]:
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


def aggregate_transcript_from_recordings(recordings: List) -> str:
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


def calculate_timerange_from_recordings(
    recordings: List,
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
                end_times.append(end_dt)

    session_start = min(start_times) if start_times else None
    session_end = max(end_times) if end_times else None

    return session_start, session_end
