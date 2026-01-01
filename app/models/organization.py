"""
Organization (Tenant) Model
Multi-tenant organization management for Duotopia
"""
from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class Organization(Base, BaseModel):
    """
    Organization/Tenant model for multi-tenant architecture

    Each organization represents a school, institution, or practice
    that has counselors, clients, and sessions.
    """

    __tablename__ = "organizations"

    # Core identification
    tenant_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
        comment="Unique tenant identifier (e.g., 'school_abc', 'practice_xyz')",
    )
    name = Column(String, nullable=False, comment="Organization display name")

    # Optional details
    description = Column(
        Text, nullable=True, comment="Organization description or notes"
    )

    # Status
    is_active = Column(
        Boolean, default=True, nullable=False, comment="Whether organization is active"
    )

    # Statistics (computed from relationships)
    # These are stored for performance but can be recomputed
    counselor_count = Column(
        Integer, default=0, nullable=False, comment="Cached count of active counselors"
    )
    client_count = Column(
        Integer, default=0, nullable=False, comment="Cached count of active clients"
    )
    session_count = Column(
        Integer, default=0, nullable=False, comment="Cached count of total sessions"
    )

    # Relationships
    counselors = relationship(
        "Counselor",
        foreign_keys="[Counselor.tenant_id]",
        primaryjoin="Organization.tenant_id == Counselor.tenant_id",
        back_populates="organization",
        lazy="dynamic",
    )

    def update_stats(self, db_session):
        """Update cached statistics from actual data"""
        from sqlalchemy import func, select

        from app.models.client import Client
        from app.models.counselor import Counselor
        from app.models.session import Session

        # Count active counselors
        counselor_count = (
            db_session.scalar(
                select(func.count(Counselor.id)).where(
                    Counselor.tenant_id == self.tenant_id, Counselor.is_active.is_(True)
                )
            )
            or 0
        )

        # Count active clients
        client_count = (
            db_session.scalar(
                select(func.count(Client.id)).where(Client.tenant_id == self.tenant_id)
            )
            or 0
        )

        # Count sessions
        session_count = (
            db_session.scalar(
                select(func.count(Session.id)).where(
                    Session.tenant_id == self.tenant_id
                )
            )
            or 0
        )

        self.counselor_count = counselor_count
        self.client_count = client_count
        self.session_count = session_count

    def __repr__(self) -> str:
        return f"<Organization(tenant_id='{self.tenant_id}', name='{self.name}')>"
