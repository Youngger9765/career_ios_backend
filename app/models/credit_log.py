"""
Credit Log Model - Transaction history for credit system
"""
from sqlalchemy import JSON, Column, Float, ForeignKey, Index, String
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

    # Polymorphic association - can link to sessions, translations, OCR, reports, etc.
    resource_type = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Resource type: 'session', 'translation', 'ocr', 'report', etc. NULL for purchases/refunds.",
    )
    resource_id = Column(
        String,
        nullable=True,
        index=True,
        comment="Resource ID (UUID as string, polymorphic). NULL for purchases/refunds.",
    )

    credits_delta = Column(
        Float,
        nullable=False,
        comment="Credit change (positive = added/refund, negative = usage)",
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

    __table_args__ = (
        Index("ix_credit_logs_counselor_type", "counselor_id", "transaction_type"),
        Index("ix_credit_logs_created_at", "created_at"),
        Index("ix_credit_logs_resource", "resource_type", "resource_id"),
    )
