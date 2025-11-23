import enum

from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class ReportStatus(str, enum.Enum):
    PROCESSING = "PROCESSING"  # 生成中
    DRAFT = "DRAFT"  # 已生成,草稿
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"  # 生成失敗
    ARCHIVED = "ARCHIVED"


class Report(Base, BaseModel):
    __tablename__ = "reports"

    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("counselors.id"), nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    version = Column(Integer, default=1)
    status: Column[ReportStatus] = Column(SQLEnum(ReportStatus, values_callable=lambda x: [e.value for e in x]), default=ReportStatus.DRAFT, nullable=False)
    mode = Column(String)  # 報告生成模式

    # Report content - 結構化報告內容
    content_json = Column(
        JSON
    )  # AI 原始生成的報告 (不可變，用於審計和回溯)
    content_markdown = Column(Text)  # AI 原始生成的 Markdown 格式 (不可變)

    # User edited content - 諮商師編輯後的版本
    edited_content_json = Column(JSON)  # 諮商師手動編輯的報告內容
    edited_content_markdown = Column(Text)  # 諮商師編輯後的 Markdown 格式
    edited_at = Column(String)  # ISO 8601 timestamp of last edit
    edit_count = Column(Integer, default=0)  # 編輯次數

    # RAG Agent 引用
    citations_json = Column(JSON)  # RAG檢索的理論引用
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete='SET NULL'), nullable=True)  # 使用的Agent ID

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

    # Error handling
    error_message = Column(Text)  # 生成失敗時的錯誤訊息

    # Relationships
    session = relationship("Session", back_populates="reports")
    client = relationship("Client", back_populates="reports")
    created_by = relationship(
        "Counselor", foreign_keys=[created_by_id], back_populates="reports"
    )
    reviewed_by = relationship("Counselor", foreign_keys=[reviewed_by_id])
