import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class CounselorRole(str, enum.Enum):
    COUNSELOR = "counselor"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class BillingMode(str, enum.Enum):
    """Billing mode for counselor"""
    PREPAID = "prepaid"
    SUBSCRIPTION = "subscription"


class Counselor(Base, BaseModel):
    __tablename__ = "counselors"

    # Authentication fields
    email = Column(String, index=True, nullable=False)  # Removed unique=True
    username = Column(
        String, index=True, nullable=True
    )  # Removed unique=True (allow duplicates), nullable for simplified registration
    full_name = Column(String, nullable=True)  # Nullable for simplified registration
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
    email_verified = Column(Boolean, default=False, nullable=False, comment="Email verification status")
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

    # Billing mode (prepaid vs subscription)
    billing_mode: Column[BillingMode] = Column(
        SQLEnum(BillingMode, values_callable=lambda x: [e.value for e in x]),
        server_default="subscription",
        nullable=False,
        index=True,
        comment="Billing mode: prepaid (credit-based) or subscription (time-limited)"
    )

    # Subscription-specific usage tracking fields
    monthly_usage_limit_minutes = Column(
        Integer,
        default=360,
        nullable=True,
        comment="Monthly usage limit in minutes (subscription mode only), 6 hours = 360 min"
    )
    monthly_minutes_used = Column(
        Integer,
        default=0,
        nullable=True,
        comment="Minutes used in current billing period (subscription mode only)"
    )
    usage_period_start = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Start of current 30-day usage period (subscription mode only)"
    )

    def __init__(self, **kwargs):
        """Initialize counselor with proper defaults"""
        from datetime import datetime, timezone, timedelta

        # Set Python-level defaults for fields that need them
        if 'billing_mode' not in kwargs:
            kwargs['billing_mode'] = BillingMode.SUBSCRIPTION.value  # Use .value for SQLAlchemy
        if 'monthly_usage_limit_minutes' not in kwargs:
            kwargs['monthly_usage_limit_minutes'] = 360
        if 'monthly_minutes_used' not in kwargs:
            kwargs['monthly_minutes_used'] = 0
        if 'usage_period_start' not in kwargs:
            kwargs['usage_period_start'] = datetime.now(timezone.utc)
        if 'subscription_expires_at' not in kwargs:
            # New subscription accounts get 1 year validity
            kwargs['subscription_expires_at'] = datetime.now(timezone.utc) + timedelta(days=365)

        super().__init__(**kwargs)

    # Relationships
    cases = relationship("Case", back_populates="counselor")
    reports = relationship(
        "Report", foreign_keys="[Report.created_by_id]", back_populates="created_by"
    )
    clients = relationship("Client", back_populates="counselor")
    credit_logs = relationship(
        "CreditLog", back_populates="counselor", cascade="all, delete-orphan"
    )

    # Computed properties for backward compatibility with admin API
    @property
    def total_credits(self) -> int:
        """
        Total credits purchased/added (sum of all positive deltas).
        Computed from credit_logs for backward compatibility.
        """
        if not self.credit_logs:
            return 0
        return int(
            sum(log.credits_delta for log in self.credit_logs if log.credits_delta > 0)
        )

    @property
    def credits_used(self) -> int:
        """
        Total credits consumed (absolute value of sum of all negative deltas).
        Computed from credit_logs for backward compatibility.
        """
        if not self.credit_logs:
            return 0
        return int(
            abs(
                sum(
                    log.credits_delta
                    for log in self.credit_logs
                    if log.credits_delta < 0
                )
            )
        )
