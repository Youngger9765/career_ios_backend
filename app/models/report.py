from sqlalchemy import Column, String, ForeignKey, Enum as SQLEnum, Text, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import BaseModel
import enum


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Report(Base, BaseModel):
    __tablename__ = "reports"
    
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    version = Column(Integer, default=1)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.DRAFT, nullable=False)
    
    # Report content
    summary = Column(Text)
    analysis = Column(Text)
    recommendations = Column(Text)
    action_items = Column(JSON)
    
    # AI metadata
    ai_model = Column(String)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    rag_sources = Column(JSON)  # Retrieved documents used
    
    # Review
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    review_notes = Column(Text)
    
    # Relationships
    session = relationship("Session", back_populates="reports")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="reports")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])