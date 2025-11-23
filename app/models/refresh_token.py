from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from app.models.base import GUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class RefreshToken(Base, BaseModel):
    __tablename__ = "refresh_tokens"

    token = Column(String, unique=True, index=True, nullable=False)
    counselor_id = Column(GUID(), ForeignKey("counselors.id"), nullable=False)
    tenant_id = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)

    # Relationships
    counselor = relationship("Counselor")
