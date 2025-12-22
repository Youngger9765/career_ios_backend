"""
Credit Rate Model - Configurable billing rules for credit system
"""
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from app.core.database import Base
from app.models.base import BaseModel


class CreditRate(Base, BaseModel):
    """
    Configurable billing rate rules stored in database.
    Supports versioning for rate changes with audit trail.
    """

    __tablename__ = "credit_rates"

    rule_name = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Rule identifier (e.g., 'voice_call', 'text_session')",
    )
    calculation_method = Column(
        String(20),
        default="per_second",
        nullable=False,
        comment="Calculation method: per_second, per_minute, tiered",
    )
    rate_config = Column(
        JSON, nullable=False, comment="JSON configuration for rate calculation"
    )
    version = Column(
        Integer, default=1, nullable=False, comment="Version number for this rule"
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Is this version active",
    )
    effective_from = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="When this rate becomes effective",
    )

    __table_args__ = (
        UniqueConstraint("rule_name", "version", name="uq_credit_rate_rule_version"),
        Index("ix_credit_rates_active_lookup", "rule_name", "is_active", "version"),
    )
