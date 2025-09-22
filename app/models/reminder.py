from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import BaseModel
import enum


class ReminderType(str, enum.Enum):
    FOLLOW_UP = "follow_up"
    APPOINTMENT = "appointment"
    TASK = "task"
    REVIEW = "review"


class ReminderStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SNOOZED = "snoozed"


class Reminder(Base, BaseModel):
    __tablename__ = "reminders"
    
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    reminder_type = Column(SQLEnum(ReminderType), nullable=False)
    status = Column(SQLEnum(ReminderStatus), default=ReminderStatus.ACTIVE, nullable=False)
    
    title = Column(String, nullable=False)
    description = Column(Text)
    due_date = Column(DateTime(timezone=True), nullable=False)
    
    # Notification
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True))
    
    # Relationships
    case = relationship("Case", back_populates="reminders")