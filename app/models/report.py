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
    
    # Report content - 結構化報告內容
    content_json = Column(JSON)  # 包含：主訴問題、成因分析、晤談目標、介入策略、成效評估、關鍵對話

    # RAG Agent 引用
    citations_json = Column(JSON)  # RAG檢索的理論引用
    agent_id = Column(Integer)  # 使用的Agent ID

    # Legacy fields (保留向下兼容)
    summary = Column(Text)
    analysis = Column(Text)
    recommendations = Column(Text)
    action_items = Column(JSON)

    # AI metadata
    ai_model = Column(String)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    
    # Review
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    review_notes = Column(Text)
    
    # Relationships
    session = relationship("Session", back_populates="reports")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="reports")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])