from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String(50), nullable=False)  # ingest, reembed
    target_id = Column(Integer, index=True)
    status = Column(
        String(50), default="queued", index=True
    )  # queued, running, completed, failed
    steps_json = Column(JSON, default=[])
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    error_msg = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
