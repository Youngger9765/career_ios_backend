import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import GUID, BaseModel


class Session(Base, BaseModel):
    __tablename__ = "sessions"

    case_id: Column[uuid.UUID] = Column(GUID(), ForeignKey("cases.id"), nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    session_number = Column(Integer, nullable=False)
    session_date = Column(DateTime(timezone=True), nullable=False)
    name = Column(String(255), nullable=True)  # 會談名稱（可選）
    start_time = Column(DateTime(timezone=True))  # 開始時間
    end_time = Column(DateTime(timezone=True))  # 結束時間
    duration_minutes = Column(Integer)  # 保留向下兼容
    room_number = Column(String)

    # File paths/URLs (deprecated - use recordings table instead)
    audio_path = Column(String)  # 音訊檔路徑（模式1）- 保留向下兼容

    # Transcript content
    # NOTE: transcript_text 會自動匯聚所有 recordings 的逐字稿
    transcript_text = Column(Text)  # 完整逐字稿內容（自動從 recordings 匯聚）
    transcript_sanitized = Column(Text)  # 脫敏後逐字稿
    source_type = Column(String(10))  # 'audio' or 'text' - 輸入來源

    # Additional content
    notes = Column(Text)
    key_points = Column(Text)
    summary = Column(Text)  # 會談摘要（100字內，用於歷程展示，AI 生成）
    reflection = Column(
        JSON, default=dict
    )  # 諮商師反思（人類撰寫，格式彈性以支援不同租戶需求）

    # Recordings - 會談逐字稿片段（JSON list）
    # 支援會談中斷後繼續的場景，每個 recording 包含：
    # - segment_number: 第幾段（1, 2, 3...）
    # - start_time/end_time: 開始/結束時間
    # - transcript_text: 此段逐字稿
    # - transcript_sanitized: 脫敏後逐字稿
    recordings = Column(JSON, default=lambda: [])

    # Relationships
    case = relationship("Case", back_populates="sessions")
    jobs = relationship("Job", back_populates="session")
    reports = relationship("Report", back_populates="session")
