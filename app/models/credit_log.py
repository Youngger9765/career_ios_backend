"""
Credit Log Model - Transaction history for credit system
"""
from sqlalchemy import JSON, Column, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import GUID, BaseModel


class CreditLog(Base, BaseModel):
    """
    Audit trail for all credit transactions.
    Stores raw data (e.g., seconds) and rate snapshots for flexibility and auditability.
    """

    __tablename__ = "credit_logs"

    counselor_id = Column(
        GUID(),
        ForeignKey("counselors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Counselor who owns this transaction",
    )
    session_id = Column(
        GUID(),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Related session (if applicable)",
    )
    credits_delta = Column(
        Integer,
        nullable=False,
        comment="Credit change (positive = added, negative = used)",
    )
    transaction_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Type: purchase, usage, admin_adjustment, refund",
    )
    raw_data = Column(
        JSON,
        nullable=True,
        comment="Raw data (e.g., duration_seconds for usage)",
    )
    rate_snapshot = Column(
        JSON,
        nullable=True,
        comment="Rate configuration used for this transaction",
    )
    calculation_details = Column(
        JSON,
        nullable=True,
        comment="Detailed calculation breakdown",
    )

    # Relationships
    counselor = relationship("Counselor", back_populates="credit_logs")
    session = relationship("Session", back_populates="credit_logs")

    __table_args__ = (
        Index("ix_credit_logs_counselor_type", "counselor_id", "transaction_type"),
        Index("ix_credit_logs_created_at", "created_at"),
    )
