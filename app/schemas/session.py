from typing import Optional
from datetime import datetime
from uuid import UUID
from app.schemas.base import BaseSchema, BaseResponse


class SessionBase(BaseSchema):
    session_date: datetime
    duration_minutes: Optional[int] = None
    room_number: Optional[str] = None
    notes: Optional[str] = None
    key_points: Optional[str] = None


class SessionCreate(SessionBase):
    case_id: UUID
    session_number: int


class SessionResponse(BaseResponse, SessionBase):
    case_id: UUID
    session_number: int
    audio_file_path: Optional[str] = None
    transcript_file_path: Optional[str] = None


class AudioUpload(BaseSchema):
    session_id: UUID
    file_name: str
    file_size: int
    duration_seconds: Optional[int] = None