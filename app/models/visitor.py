from sqlalchemy import Column, String, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import BaseModel


class Visitor(Base, BaseModel):
    __tablename__ = "visitors"
    
    code = Column(String, unique=True, index=True, nullable=False)  # Anonymous code
    nickname = Column(String)  # Optional nickname
    age_range = Column(String)  # e.g., "20-25", "25-30"
    gender = Column(String)  # Optional
    tags = Column(JSON, default=list)  # Tags for categorization
    notes = Column(Text)  # Private notes
    
    # Relationships
    cases = relationship("Case", back_populates="visitor")