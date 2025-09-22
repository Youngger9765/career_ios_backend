from typing import Optional
from datetime import datetime
from uuid import UUID
from app.schemas.base import BaseSchema, BaseResponse
from app.models.reminder import ReminderType, ReminderStatus


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