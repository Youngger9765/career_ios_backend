from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class Client(Base, BaseModel):
    __tablename__ = "clients"

    # Core identification
    code = Column(String, unique=True, index=True, nullable=False)  # Anonymous code
    name = Column(String, nullable=False)  # Real name
    nickname = Column(String)  # Optional nickname

    # Basic demographics
    age = Column(Integer)
    gender = Column(String)
    occupation = Column(String)
    education = Column(String)
    location = Column(String)

    # Additional information
    economic_status = Column(String)
    family_relations = Column(Text)
    other_info = Column(JSON, default=dict)  # Flexible JSONB for extra fields

    # Categorization
    tags = Column(JSON, default=list)  # Tags for categorization

    # Private notes
    notes = Column(Text)

    # Multi-tenant & relationships
    tenant_id = Column(String, nullable=False, index=True)
    counselor_id = Column(UUID(as_uuid=True), ForeignKey("counselors.id"), nullable=False)

    # Relationships
    counselor = relationship("Counselor", back_populates="clients")
    cases = relationship("Case", back_populates="client")
    reports = relationship("Report", back_populates="client")
