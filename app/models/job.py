import enum

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class JobType(str, enum.Enum):
    AUDIO_UPLOAD = "audio_upload"
    TRANSCRIPTION = "transcription"
    ANONYMIZATION = "anonymization"
    REPORT_GENERATION = "report_generation"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base, BaseModel):
    __tablename__ = "jobs"

    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    job_type: Column[JobType] = Column(SQLEnum(JobType), nullable=False)
    status: Column[JobStatus] = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)

    # Processing info
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(String)
    retry_count = Column(Integer, default=0)

    # Input/Output
    input_data = Column(JSON)
    output_data = Column(JSON)
    job_metadata = Column(JSON)

    # Relationships
    session = relationship("Session", back_populates="jobs")
