from datetime import date

from sqlalchemy import JSON, Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class Client(Base, BaseModel):
    __tablename__ = "clients"

    # Core identification
    code = Column(String, unique=True, index=True, nullable=False)  # Anonymous code
    name = Column(String, nullable=False)  # Real name
    nickname = Column(String)  # Optional nickname

    # Required fields
    email = Column(String, nullable=False, index=True)  # Email address for consultation or records
    gender = Column(String, nullable=False)  # Gender: 男／女／其他／不透露
    birth_date = Column(Date, nullable=False)  # Birth date (Western calendar, 1900-2025)
    identity_option = Column(String, nullable=False)  # Identity: 學生／社會新鮮人／轉職者／在職者／其他
    current_status = Column(String, nullable=False)  # Current situation for quick case classification
    phone = Column(String, nullable=False)  # Mobile phone number

    # Optional fields
    age = Column(Integer)  # Auto-calculated from birth_date, updated on each save
    education = Column(String)  # Education: 高中／大學／研究所等
    current_job = Column(String)  # Current job (occupation/years of experience)
    career_status = Column(String)  # Career status: 探索中／轉職準備／面試中／已在職等
    occupation = Column(String)
    location = Column(String)

    # Consultation and medical history
    has_consultation_history = Column(String)  # Yes/No + supplementary text
    has_mental_health_history = Column(String)  # Yes/No + supplementary text (sensitive)

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
