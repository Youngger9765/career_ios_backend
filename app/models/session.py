from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class Session(Base, BaseModel):
    __tablename__ = "sessions"

    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    session_number = Column(Integer, nullable=False)
    session_date = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer)
    room_number = Column(String)

    # File paths/URLs
    audio_path = Column(String)  # 音訊檔路徑（模式1）

    # Transcript content
    transcript_text = Column(Text)  # 逐字稿內容
    transcript_sanitized = Column(Text)  # 脫敏後逐字稿
    source_type = Column(String(10))  # 'audio' or 'text' - 輸入來源

    # Additional content
    notes = Column(Text)
    key_points = Column(Text)

    # Relationships
    case = relationship("Case", back_populates="sessions")
    jobs = relationship("Job", back_populates="session")
    reports = relationship("Report", back_populates="session")
