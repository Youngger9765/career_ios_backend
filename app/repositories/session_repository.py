"""
Session Repository - Data access layer for sessions
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DBSession

from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor, CounselorRole
from app.models.report import Report
from app.models.session import Session


class SessionRepository:
    """Repository for session data access"""

    def __init__(self, db: DBSession):
        self.db = db

    def create(self, **kwargs) -> Session:
        """Create a new session"""
        session = Session(**kwargs)
        self.db.add(session)
        self.db.flush()
        return session

    def get_by_id(self, session_id: UUID) -> Optional[Session]:
        """Get session by ID"""
        result = self.db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def get_case_by_id(self, case_id: UUID, tenant_id: str) -> Optional[Case]:
        """Get case by ID with tenant check"""
        result = self.db.execute(
            select(Case).where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def get_client_by_id(self, client_id: UUID) -> Optional[Client]:
        """Get client by ID"""
        result = self.db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def get_sessions_by_case(
        self, case_id: UUID, order_by_date: bool = True
    ) -> List[Session]:
        """Get all sessions for a case"""
        query = select(Session).where(
            Session.case_id == case_id,
            Session.deleted_at.is_(None),
        )

        if order_by_date:
            query = query.order_by(
                func.coalesce(Session.start_time, Session.session_date).asc(),
                Session.created_at.asc(),
            )

        result = self.db.execute(query)
        return list(result.scalars().all())

    def list_sessions(
        self,
        counselor_id: UUID,
        tenant_id: str,
        client_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        mode: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Tuple[Session, Case, Client, bool]], int]:
        """
        List sessions with filters and pagination.

        Args:
            counselor_id: 諮詢師 ID
            tenant_id: 租戶 ID
            client_id: 依孩子（Client）篩選
            case_id: 依案例（Case）篩選
            mode: 依模式篩選 (practice / emergency)
            search: 依孩子名稱或代碼搜尋
            skip: 分頁偏移
            limit: 每頁筆數

        Returns: (list of (Session, Case, Client, has_report) tuples, total_count)
        """
        # Base query - select Session, Case, Client, and has_report
        # Use LEFT JOIN with Report and check if report_id is not null
        query = (
            select(Session, Case, Client, Report.id.label("report_id"))
            .join(Case, Session.case_id == Case.id)
            .join(Client, Case.client_id == Client.id)
            .outerjoin(Report, Report.session_id == Session.id)
            .where(
                Client.counselor_id == counselor_id,
                Client.tenant_id == tenant_id,
                Session.deleted_at.is_(None),
                Case.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
        )

        # Apply filters
        if client_id:
            query = query.where(Client.id == client_id)

        if case_id:
            query = query.where(Case.id == case_id)

        if mode:
            query = query.where(Session.session_mode == mode)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Client.name.ilike(search_pattern),
                    Client.code.ilike(search_pattern),
                )
            )

        # Count total - use same WHERE clauses but count distinct sessions
        count_query = (
            select(func.count(func.distinct(Session.id)))
            .select_from(Session)
            .join(Case, Session.case_id == Case.id)
            .join(Client, Case.client_id == Client.id)
            .where(
                Client.counselor_id == counselor_id,
                Client.tenant_id == tenant_id,
                Session.deleted_at.is_(None),
                Case.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
        )
        if client_id:
            count_query = count_query.where(Client.id == client_id)
        if case_id:
            count_query = count_query.where(Case.id == case_id)
        if mode:
            count_query = count_query.where(Session.session_mode == mode)
        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.where(
                or_(
                    Client.name.ilike(search_pattern),
                    Client.code.ilike(search_pattern),
                )
            )
        total = self.db.execute(count_query).scalar()

        # Apply pagination and ordering (最新的在前面)
        query = (
            query.offset(skip)
            .limit(limit)
            .order_by(
                func.coalesce(Session.start_time, Session.session_date).desc(),
                Session.created_at.desc(),
            )
        )

        result = self.db.execute(query)
        rows = result.all()

        # Convert to (Session, Case, Client, has_report) tuples
        session_data = [
            (session, case, client, report_id is not None)
            for session, case, client, report_id in rows
        ]

        return session_data, total

    def update(self, session: Session, **kwargs) -> Session:
        """Update a session"""
        # Handle session date/time updates
        time_changed = False
        old_session_number = session.session_number

        for key, value in kwargs.items():
            if hasattr(session, key):
                # Track if time-related fields changed
                if (
                    key in ["session_date", "start_time"]
                    and getattr(session, key) != value
                ):
                    time_changed = True
                setattr(session, key, value)

        # If time changed, recalculate session numbers
        if time_changed:
            self._recalculate_session_numbers(session, old_session_number)

        self.db.flush()
        return session

    def soft_delete(self, session: Session) -> None:
        """Soft delete a session"""
        session.deleted_at = datetime.now(timezone.utc)
        self.db.flush()

    def has_reports(self, session_id: UUID) -> bool:
        """Check if session has any reports"""
        result = self.db.execute(
            select(func.count()).where(
                Report.session_id == session_id,
            )
        )
        count = result.scalar()
        return count > 0

    def update_session_numbers(
        self, case_id: UUID, start_number: int, increment: int = 1
    ) -> None:
        """Update session numbers for all sessions >= start_number"""
        self.db.execute(
            Session.__table__.update()
            .where(Session.case_id == case_id)
            .where(Session.session_number >= start_number)
            .values(session_number=Session.session_number + increment)
        )
        self.db.flush()

    def _recalculate_session_numbers(
        self, session: Session, old_session_number: int
    ) -> None:
        """Recalculate session numbers when a session's time changes"""
        # Set current session to temporary number
        session.session_number = 0
        self.db.flush()

        # Decrement sessions after the old position
        self.db.execute(
            Session.__table__.update()
            .where(Session.case_id == session.case_id)
            .where(Session.session_number > old_session_number)
            .values(session_number=Session.session_number - 1)
        )
        self.db.flush()

        # Find new position based on updated time
        existing_sessions = self.get_sessions_by_case(session.case_id)
        existing_sessions = [s for s in existing_sessions if s.id != session.id]

        new_sort_time = (
            session.start_time if session.start_time else session.session_date
        )
        new_session_number = 1

        for existing in existing_sessions:
            existing_time = (
                existing.start_time if existing.start_time else existing.session_date
            )
            if new_sort_time > existing_time:
                new_session_number += 1
            else:
                break

        # Increment sessions at or after the new position
        self.db.execute(
            Session.__table__.update()
            .where(Session.case_id == session.case_id)
            .where(Session.session_number >= new_session_number)
            .where(Session.id != session.id)
            .values(session_number=Session.session_number + 1)
        )
        self.db.flush()

        # Set the final session number
        session.session_number = new_session_number

    def check_authorization(
        self, session: Session, counselor: Counselor, tenant_id: str
    ) -> bool:
        """Check if counselor is authorized to access session"""
        # Admin can access all sessions in their tenant
        if counselor.role == CounselorRole.ADMIN:
            case = self.get_case_by_id(session.case_id, tenant_id)
            return case is not None

        # Regular counselor can only access their own clients' sessions
        case = self.get_case_by_id(session.case_id, tenant_id)
        if not case:
            return False

        client = self.get_client_by_id(case.client_id)
        if not client:
            return False

        return client.counselor_id == counselor.id
