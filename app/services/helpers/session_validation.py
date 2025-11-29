"""
Session Validation Helpers
Extracted from session_service.py to reduce file size
"""
from datetime import datetime, timezone


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime with timezone"""
    dt = datetime.fromisoformat(date_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_datetime(datetime_str: str) -> datetime:
    """Parse datetime string with various formats"""
    time_str = datetime_str.strip()
    if " " in time_str or "T" in time_str or len(time_str) > 10:
        dt = datetime.fromisoformat(time_str.replace(" ", "T"))
    else:
        raise ValueError("datetime must include date (format: YYYY-MM-DD HH:MM)")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
