import enum

from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class CaseStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    REFERRED = "referred"


class Case(Base, BaseModel):
    __tablename__ = "cases"

    case_number = Column(String, unique=True, index=True, nullable=False)
    counselor_id = Column(UUID(as_uuid=True), ForeignKey("counselors.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    status = Column(SQLEnum(CaseStatus), default=CaseStatus.ACTIVE, nullable=False)
    summary = Column(Text)
    goals = Column(Text)

    # Relationships
    counselor = relationship("Counselor", back_populates="cases")
    client = relationship("Client", back_populates="cases")
    sessions = relationship("Session", back_populates="case")
    reminders = relationship("Reminder", back_populates="case")
