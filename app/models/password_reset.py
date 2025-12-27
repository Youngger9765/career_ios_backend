"""
Password Reset Token Model
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String

from app.core.database import Base
from app.models.base import BaseModel


class PasswordResetToken(Base, BaseModel):
    """Password reset token for secure password reset flow"""

    __tablename__ = "password_reset_tokens"

    # Token (secure random string, 32+ characters)
    token = Column(String, unique=True, index=True, nullable=False)

    # User identification
    email = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)

    # Token metadata
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)

    # IP tracking (optional, for security audit)
    request_ip = Column(String, nullable=True)
    used_ip = Column(String, nullable=True)

    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)"""
        if self.used:
            return False

        from datetime import timezone as tz

        now = datetime.now(tz.utc)
        return self.expires_at > now

    def mark_as_used(self, ip: str = None):
        """Mark token as used"""
        from datetime import timezone as tz

        self.used = True
        self.used_at = datetime.now(tz.utc)
        if ip:
            self.used_ip = ip
