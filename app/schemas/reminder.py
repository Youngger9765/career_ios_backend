from datetime import datetime
from typing import Optional
from uuid import UUID

from app.models.reminder import ReminderStatus, ReminderType
from app.schemas.base import BaseResponse, BaseSchema


class ReminderBase(BaseSchema):
    title: str
    description: Optional[str] = None
    due_date: datetime
    reminder_type: ReminderType


class ReminderCreate(ReminderBase):
    case_id: UUID


class ReminderUpdate(BaseSchema):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[ReminderStatus] = None


class ReminderResponse(BaseResponse, ReminderBase):
    case_id: UUID
    status: ReminderStatus
    is_sent: bool
    sent_at: Optional[datetime] = None
