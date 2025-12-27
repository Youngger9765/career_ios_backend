import enum

from sqlalchemy import Boolean, Column, DateTime, Float, String, UniqueConstraint
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
    email = Column(String, index=True, nullable=False)  # Removed unique=True
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Multi-tenant & role
    tenant_id = Column(String, nullable=False, index=True)
    role: Column[CounselorRole] = Column(
        SQLEnum(CounselorRole), default=CounselorRole.COUNSELOR, nullable=False
    )

    # Unique constraint: email + tenant_id combination must be unique
    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_counselor_email_tenant"),
    )

    # Status & metadata
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime(timezone=True))

    # Credit system fields (universal payment mechanism)
    phone = Column(String, nullable=True, comment="Contact phone number")
    available_credits = Column(
        Float,
        default=1000.0,
        nullable=False,
        comment="Available credits (current balance). Updated incrementally on each billing operation.",
    )
    subscription_expires_at = Column(
        DateTime(timezone=True), nullable=True, comment="Subscription expiry date"
    )

    # Relationships
    cases = relationship("Case", back_populates="counselor")
    reports = relationship(
        "Report", foreign_keys="[Report.created_by_id]", back_populates="created_by"
    )
    clients = relationship("Client", back_populates="counselor")
    credit_logs = relationship(
        "CreditLog", back_populates="counselor", cascade="all, delete-orphan"
    )
