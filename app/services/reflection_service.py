"""
Reflection Service - Business logic for counselor reflections
Extracted from app/api/sessions.py
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from app.models.session import Session
from app.repositories.session_repository import SessionRepository


class ReflectionService:
    """Service for managing session reflections"""

    def __init__(self, db: DBSession):
        self.db = db
        self.session_repo = SessionRepository(db)

    def get_reflection(
        self,
        session_id: UUID,
        counselor_id: UUID,
        tenant_id: str,
    ) -> Optional[dict]:
        """Get reflection for a session"""
        session = self._get_authorized_session(session_id, counselor_id, tenant_id)
        return session.reflection

    def update_reflection(
        self,
        session_id: UUID,
        reflection: dict,
        counselor_id: UUID,
        tenant_id: str,
    ) -> dict:
        """Update or create reflection for a session"""
        session = self._get_authorized_session(session_id, counselor_id, tenant_id)

        # Update reflection
        session.reflection = reflection
        self.db.commit()
        self.db.refresh(session)

        return session.reflection

    def _get_authorized_session(
        self,
        session_id: UUID,
        counselor_id: UUID,
        tenant_id: str,
    ) -> Session:
        """Get session with authorization check"""
        session = self.session_repo.get_by_id(session_id)
        if not session:
            raise ValueError("Session not found")

        # Verify authorization
        case = self.session_repo.get_case_by_id(session.case_id, tenant_id)
        if not case:
            raise ValueError("Case not found")

        client = self.session_repo.get_client_by_id(case.client_id)
        if not client or client.counselor_id != counselor_id:
            raise PermissionError("Not authorized")

        return session
