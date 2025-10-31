import enum

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class CounselorRole(str, enum.Enum):
    COUNSELOR = "counselor"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class Counselor(Base, BaseModel):
    __tablename__ = "counselors"

    # Authentication fields
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Multi-tenant & role
    tenant_id = Column(String, nullable=False, index=True)
    role = Column(SQLEnum(CounselorRole), default=CounselorRole.COUNSELOR, nullable=False)

    # Status & metadata
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))

    # Relationships
    cases = relationship("Case", back_populates="counselor")
    reports = relationship(
        "Report", foreign_keys="[Report.created_by_id]", back_populates="created_by"
    )
    clients = relationship("Client", back_populates="counselor")
