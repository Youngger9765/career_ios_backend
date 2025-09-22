from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import BaseModel
import enum


class CaseStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    REFERRED = "referred"


class Case(Base, BaseModel):
    __tablename__ = "cases"
    
    case_number = Column(String, unique=True, index=True, nullable=False)
    counselor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    visitor_id = Column(UUID(as_uuid=True), ForeignKey("visitors.id"), nullable=False)
    status = Column(SQLEnum(CaseStatus), default=CaseStatus.ACTIVE, nullable=False)
    summary = Column(Text)
    goals = Column(Text)
    
    # Relationships
    counselor = relationship("User", back_populates="cases")
    visitor = relationship("Visitor", back_populates="cases")
    sessions = relationship("Session", back_populates="case")
    reminders = relationship("Reminder", back_populates="case")