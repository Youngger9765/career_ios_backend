from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="draft", index=True)
    active_version_id = Column(Integer, ForeignKey("agent_versions.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    versions = relationship(
        "AgentVersion", back_populates="agent", foreign_keys="AgentVersion.agent_id"
    )
    active_version = relationship(
        "AgentVersion", foreign_keys=[active_version_id], post_update=True
    )


class AgentVersion(Base):
    __tablename__ = "agent_versions"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(
        Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False)
    state = Column(String(50), default="draft")  # draft, published
    config_json = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String(255))

    # Relationships
    agent = relationship("Agent", back_populates="versions", foreign_keys=[agent_id])
