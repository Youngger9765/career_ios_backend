from sqlalchemy import Column, String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import BaseModel
import enum


class UserRole(str, enum.Enum):
    COUNSELOR = "counselor"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class User(Base, BaseModel):
    __tablename__ = "users"
    
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.COUNSELOR, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    cases = relationship("Case", back_populates="counselor")
    reports = relationship("Report", back_populates="created_by")