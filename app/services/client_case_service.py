"""
Client-Case Service - Business logic for unified client-case operations
Refactored from app/api/ui_client_case_list.py (962 lines → service layer)
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session as SessionModel


class ClientCaseService:
    """Service layer for client-case operations"""

    def __init__(self, db: DBSession):
        self.db = db

    # ============================================================================
    # Helper Methods
    # ============================================================================

    def _generate_client_code(self, tenant_id: str) -> str:
        """Generate unique client code in format C0001, C0002, etc."""
        result = self.db.execute(
            select(Client.code)
            .where(Client.tenant_id == tenant_id)
            .where(Client.code.like("C%"))
            .order_by(Client.code.desc())
        )
        codes = result.scalars().all()

        max_num = 0
        for code in codes:
            if code.startswith("C") and code[1:].isdigit():
                num = int(code[1:])
                if num > max_num:
                    max_num = num

        next_num = max_num + 1
        return f"C{next_num:04d}"

    def _generate_case_number(self, tenant_id: str) -> str:
        """Generate unique case number in format CASE0001, CASE0002, etc."""
        result = self.db.execute(
            select(Case.case_number)
            .where(Case.tenant_id == tenant_id)
            .where(Case.case_number.like("CASE%"))
            .order_by(Case.case_number.desc())
        )
        numbers = result.scalars().all()

        max_num = 0
        for num_str in numbers:
            if num_str.startswith("CASE") and num_str[4:].isdigit():
                num = int(num_str[4:])
                if num > max_num:
                    max_num = num

        next_num = max_num + 1
        return f"CASE{next_num:04d}"

    def _map_case_status_to_label(self, status: CaseStatus) -> str:
        """Map case status to Chinese label"""
        status_map = {
            CaseStatus.NOT_STARTED: "未開始",
            CaseStatus.IN_PROGRESS: "進行中",
            CaseStatus.COMPLETED: "已完成",
        }
        return status_map.get(status, "未知")

    def _format_session_date(self, dt: Optional[datetime]) -> Optional[str]:
        """Format session date for display: 2026/01/22 19:30"""
        if not dt:
            return None
        return dt.strftime("%Y/%m/%d %H:%M")

    def _normalize_case_status(self, status: Any) -> Tuple[int, CaseStatus]:
        """Normalize case status to (int_value, enum)"""
        if isinstance(status, int):
            return status, CaseStatus(status)
        elif isinstance(status, CaseStatus):
            return status.value, status
        else:
            # Legacy string data
            status_map = {
                "ACTIVE": CaseStatus.NOT_STARTED,
                "IN_PROGRESS": CaseStatus.IN_PROGRESS,
                "COMPLETED": CaseStatus.COMPLETED,
                "SUSPENDED": CaseStatus.IN_PROGRESS,
                "REFERRED": CaseStatus.COMPLETED,
                "NOT_STARTED": CaseStatus.NOT_STARTED,
            }
            status_enum = status_map.get(str(status).upper(), CaseStatus.NOT_STARTED)
            return status_enum.value, status_enum

    # ============================================================================
    # Core Business Methods
    # ============================================================================

    def create_client_and_case(
        self,
        tenant_id: str,
        counselor: Counselor,
        client_data: Dict[str, Any],
        case_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Client, Case]:
        """
        Create client and associated case atomically.

        Args:
            tenant_id: Tenant ID
            counselor: Current counselor
            client_data: Client fields (name, email, etc.)
            case_data: Optional case fields (summary, goals, etc.)

        Returns:
            Tuple of (created_client, created_case)

        Raises:
            ValueError: If email already exists
        """
        # Generate client code
        client_code = self._generate_client_code(tenant_id)

        # Check email uniqueness
        existing_client = self.db.execute(
            select(Client).where(
                Client.email == client_data["email"],
                Client.tenant_id == tenant_id,
                Client.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if existing_client:
            raise ValueError(
                f"Email {client_data['email']} already exists for this tenant"
            )

        # Create client
        new_client = Client(
            code=client_code,
            counselor_id=counselor.id,
            tenant_id=tenant_id,
            **client_data,
        )
        self.db.add(new_client)
        self.db.flush()

        # Generate case number
        case_number = self._generate_case_number(tenant_id)

        # Create case
        case_fields = case_data or {}
        new_case = Case(
            case_number=case_number,
            client_id=new_client.id,
            counselor_id=counselor.id,
            tenant_id=tenant_id,
            status=CaseStatus.NOT_STARTED,
            summary=case_fields.get("summary"),
            goals=case_fields.get("goals"),
            problem_description=case_fields.get("problem_description"),
        )
        self.db.add(new_case)

        self.db.commit()
        self.db.refresh(new_client)
        self.db.refresh(new_case)

        return new_client, new_case

    def list_client_cases(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List all client-cases with session statistics.

        Returns:
            Tuple of (items, total_count)
        """
        # Subquery: first case per client
        case_subquery = (
            select(
                Case.client_id,
                func.min(Case.created_at).label("first_case_created_at"),
            )
            .where(
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
            .group_by(Case.client_id)
            .subquery()
        )

        # Subquery: session stats per case
        session_stats_subquery = (
            select(
                SessionModel.case_id,
                func.count(SessionModel.id).label("total_sessions"),
                func.max(SessionModel.session_date).label("last_session_date"),
            )
            .where(SessionModel.deleted_at.is_(None))
            .group_by(SessionModel.case_id)
            .subquery()
        )

        # Main query: join clients with first case and session stats
        query = (
            select(
                Client,
                Case,
                session_stats_subquery.c.total_sessions,
                session_stats_subquery.c.last_session_date,
            )
            .join(case_subquery, Client.id == case_subquery.c.client_id)
            .join(
                Case,
                (Case.client_id == Client.id)
                & (Case.created_at == case_subquery.c.first_case_created_at)
                & (Case.deleted_at.is_(None)),
            )
            .outerjoin(
                session_stats_subquery, Case.id == session_stats_subquery.c.case_id
            )
            .where(
                Client.tenant_id == tenant_id,
                Client.deleted_at.is_(None),
            )
        )

        # Count total
        count_query = select(func.count()).select_from(
            select(Client.id)
            .join(case_subquery, Client.id == case_subquery.c.client_id)
            .where(
                Client.tenant_id == tenant_id,
                Client.deleted_at.is_(None),
            )
            .subquery()
        )
        total = self.db.execute(count_query).scalar() or 0

        # Execute with pagination
        result = self.db.execute(query.offset(skip).limit(limit))
        rows = result.all()

        # Build items
        items = []
        for client, case, total_sessions, last_session_date in rows:
            status_value, status_enum = self._normalize_case_status(case.status)

            item = {
                "client_id": client.id,
                "case_id": case.id,
                "counselor_id": client.counselor_id,
                "client_name": client.name,
                "client_code": client.code,
                "client_email": client.email,
                "identity_option": client.identity_option,
                "current_status": client.current_status,
                "case_number": case.case_number,
                "case_status": status_value,
                "case_status_label": self._map_case_status_to_label(status_enum),
                "last_session_date": last_session_date,
                "last_session_date_display": self._format_session_date(
                    last_session_date
                ),
                "total_sessions": total_sessions or 0,
                "case_created_at": case.created_at,
                "case_updated_at": case.updated_at,
            }
            items.append(item)

        # Sort by last_session_date (newest first)
        min_datetime = datetime.min.replace(tzinfo=timezone.utc)

        def sort_key(item):
            dt = item["last_session_date"]
            if dt is None:
                return min_datetime
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt

        items.sort(key=sort_key, reverse=True)

        return items, total

    def get_client_case_detail(self, case_id: UUID, tenant_id: str) -> Dict[str, Any]:
        """
        Get detailed client-case information.

        Args:
            case_id: Case UUID
            tenant_id: Tenant ID

        Returns:
            Dict with client and case details

        Raises:
            ValueError: If case or client not found
        """
        from sqlalchemy.orm import joinedload

        case = self.db.execute(
            select(Case)
            .options(joinedload(Case.client))
            .where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not case:
            raise ValueError(f"Case {case_id} not found")

        client = case.client
        if not client or client.deleted_at is not None:
            raise ValueError(f"Client for case {case_id} not found")

        status_value, _ = self._normalize_case_status(case.status)
        status_labels = {
            0: "未開始",
            1: "進行中",
            2: "已完成",
        }

        return {
            # Client fields
            "client_id": client.id,
            "client_name": client.name,
            "client_code": client.code,
            "client_email": client.email,
            "gender": client.gender,
            "birth_date": client.birth_date,
            "phone": client.phone,
            "identity_option": client.identity_option,
            "current_status": client.current_status,
            "nickname": client.nickname,
            "education": client.education,
            "occupation": client.occupation,
            "current_job": client.current_job,
            "career_status": client.career_status,
            "has_consultation_history": client.has_consultation_history,
            "has_mental_health_history": client.has_mental_health_history,
            "location": client.location,
            "notes": client.notes,
            # Case fields
            "case_id": case.id,
            "case_number": case.case_number,
            "case_status": status_value,
            "case_status_label": status_labels.get(status_value, "未知"),
            "case_summary": case.summary,
            "case_goals": case.goals,
            "problem_description": case.problem_description,
            # Metadata
            "counselor_id": case.counselor_id,
            "created_at": case.created_at,
            "updated_at": case.updated_at,
        }

    def update_client_and_case(
        self,
        case_id: UUID,
        tenant_id: str,
        client_updates: Optional[Dict[str, Any]] = None,
        case_updates: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Client, Case]:
        """
        Update client and case data.

        Args:
            case_id: Case UUID
            tenant_id: Tenant ID
            client_updates: Optional dict of client fields to update
            case_updates: Optional dict of case fields to update

        Returns:
            Tuple of (updated_client, updated_case)

        Raises:
            ValueError: If case/client not found or email conflict
        """
        # Find case
        case = self.db.execute(
            select(Case).where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not case:
            raise ValueError(f"Case {case_id} not found")

        # Find client
        client = self.db.execute(
            select(Client).where(
                Client.id == case.client_id,
                Client.tenant_id == tenant_id,
                Client.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not client:
            raise ValueError(f"Client {case.client_id} not found")

        # Update client fields
        if client_updates:
            # Check email uniqueness if being updated
            if "email" in client_updates:
                existing = self.db.execute(
                    select(Client).where(
                        Client.email == client_updates["email"],
                        Client.tenant_id == tenant_id,
                        Client.id != client.id,
                        Client.deleted_at.is_(None),
                    )
                ).scalar_one_or_none()
                if existing:
                    raise ValueError(
                        f"Email {client_updates['email']} already exists for another client"
                    )

            for key, value in client_updates.items():
                if hasattr(client, key):
                    setattr(client, key, value)

        # Update case fields
        if case_updates:
            for key, value in case_updates.items():
                if key == "status":
                    # Handle status conversion
                    try:
                        if isinstance(value, int):
                            case.status = CaseStatus(value)
                        else:
                            case.status = CaseStatus(int(value))
                    except (ValueError, TypeError) as e:
                        raise ValueError(
                            f"Invalid case_status: {value}. Must be 0 (未開始), 1 (進行中), or 2 (已完成)"
                        ) from e
                elif hasattr(case, key):
                    setattr(case, key, value)

        self.db.commit()
        self.db.refresh(client)
        self.db.refresh(case)

        return client, case

    def delete_case(
        self,
        case_id: UUID,
        tenant_id: str,
        counselor: Counselor,
    ) -> Dict[str, Any]:
        """
        Soft-delete a case (client remains).

        Args:
            case_id: Case UUID
            tenant_id: Tenant ID
            counselor: Current counselor (for ownership check)

        Returns:
            Dict with deletion info

        Raises:
            ValueError: If case not found
            PermissionError: If counselor doesn't own case (unless admin)
        """
        from app.models.counselor import CounselorRole

        case = self.db.execute(
            select(Case).where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not case:
            raise ValueError(f"Case {case_id} not found")

        # Check ownership
        if counselor.role != CounselorRole.ADMIN and case.counselor_id != counselor.id:
            raise PermissionError("You can only delete your own cases")

        # Soft delete
        case.deleted_at = datetime.now(timezone.utc)
        self.db.commit()

        return {
            "message": "Case deleted successfully",
            "case_id": str(case_id),
            "case_number": case.case_number,
            "deleted_at": case.deleted_at.isoformat(),
        }
