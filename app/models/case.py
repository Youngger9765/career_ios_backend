import enum

from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class CaseStatus(enum.IntEnum):
    """
    Case status using integer values
    0 = 未開始 (Not Started)
    1 = 進行中 (In Progress)
    2 = 已完成 (Completed)
    """
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2


class Case(Base, BaseModel):
    __tablename__ = "cases"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'case_number', name='uix_tenant_case_number'),
    )

    case_number = Column(String, index=True, nullable=False)
    counselor_id = Column(UUID(as_uuid=True), ForeignKey("counselors.id"), nullable=False)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    status = Column(Integer, default=CaseStatus.NOT_STARTED.value, nullable=False)
    summary = Column(Text)
    goals = Column(Text)
    problem_description = Column(Text)  # 問題敘述（諮詢目的）

    # Relationships
    counselor = relationship("Counselor", back_populates="cases")
    client = relationship("Client", back_populates="cases")
    sessions = relationship("Session", back_populates="case")
    reminders = relationship("Reminder", back_populates="case")
