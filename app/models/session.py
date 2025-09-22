from sqlalchemy import Column, String, ForeignKey, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import BaseModel


class Session(Base, BaseModel):
    __tablename__ = "sessions"
    
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.id"), nullable=False)
    session_number = Column(Integer, nullable=False)
    session_date = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer)
    room_number = Column(String)
    
    # File paths/URLs
    audio_file_path = Column(String)
    transcript_file_path = Column(String)
    
    # Content
    notes = Column(Text)
    key_points = Column(Text)
    
    # Relationships
    case = relationship("Case", back_populates="sessions")
    jobs = relationship("Job", back_populates="session")
    reports = relationship("Report", back_populates="session")