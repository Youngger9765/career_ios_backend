from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.sql import func

from app.core.database import Base


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), index=True)
    version_id = Column(Integer, ForeignKey("agent_versions.id", ondelete="SET NULL"))
    question = Column(Text, nullable=False)
    answer = Column(Text)
    citations_json = Column(JSON, default=[])
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
