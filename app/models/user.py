import enum

from sqlalchemy import Boolean, Column, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


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
    reports = relationship("Report", foreign_keys="[Report.created_by_id]", back_populates="created_by")
