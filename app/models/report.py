import enum

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class ReportStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Report(Base, BaseModel):
    __tablename__ = "reports"

    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("counselors.id"), nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    version = Column(Integer, default=1)
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.DRAFT, nullable=False)
    mode = Column(String)  # 報告生成模式

    # Report content - 結構化報告內容
    content_json = Column(
        JSON
    )  # 包含：主訴問題、成因分析、晤談目標、介入策略、成效評估、關鍵對話

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

    # Quality metrics
    quality_score = Column(Integer)  # 0-100
    quality_grade = Column(String)  # A, B, C, D, E
    quality_strengths = Column(JSON)  # List of strengths
    quality_weaknesses = Column(JSON)  # List of weaknesses

    # Review
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("counselors.id"))
    review_notes = Column(Text)

    # Relationships
    session = relationship("Session", back_populates="reports")
    client = relationship("Client", back_populates="reports")
    created_by = relationship(
        "Counselor", foreign_keys=[created_by_id], back_populates="reports"
    )
    reviewed_by = relationship("Counselor", foreign_keys=[reviewed_by_id])
