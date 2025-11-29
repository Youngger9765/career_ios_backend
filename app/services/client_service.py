"""Service layer for client CRUD operations and business logic"""

from datetime import date, datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor, CounselorRole
from app.models.report import Report, ReportStatus
from app.models.session import Session as SessionModel


class ClientService:
    """Service for client operations and business logic"""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def calculate_age_from_birth_date(birth_date: date) -> int:
        """Calculate age from birth date

        Args:
            birth_date: Date of birth

        Returns:
            Age in years
        """
        today = date.today()
        age = today.year - birth_date.year
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age

    def generate_client_code(self, tenant_id: str) -> str:
        """Generate unique client code in format C0001, C0002, etc.

        Args:
            tenant_id: Tenant ID

        Returns:
            Generated client code
        """
        result = self.db.execute(
            select(Client.code)
            .where(Client.tenant_id == tenant_id)
            .where(Client.code.like("C%"))
            .order_by(Client.code.desc())
        )
        codes = result.scalars().all()

        # Extract numbers from codes and find max
        max_num = 0
        for code in codes:
            if code.startswith("C") and code[1:].isdigit():
                num = int(code[1:])
                if num > max_num:
                    max_num = num

        # Generate next code
        next_num = max_num + 1
        return f"C{next_num:04d}"

    def create_client(
        self,
        client_data: dict,
        counselor: Counselor,
        tenant_id: str,
    ) -> Client:
        """Create a new client

        Args:
            client_data: Client information dictionary
            counselor: Current counselor
            tenant_id: Tenant ID

        Returns:
            Created client

        Raises:
            HTTPException: If client code already exists
        """
        # Auto-generate code if not provided
        client_code = client_data.get("code")
        if not client_code:
            client_code = self.generate_client_code(tenant_id)

        # Check if code already exists (exclude soft-deleted)
        result = self.db.execute(
            select(Client).where(
                Client.code == client_code,
                Client.tenant_id == tenant_id,
                Client.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Client code '{client_code}' already exists",
            )

        # Auto-calculate age from birth_date if provided
        if client_data.get("birth_date") and not client_data.get("age"):
            client_data["age"] = self.calculate_age_from_birth_date(
                client_data["birth_date"]
            )

        # Create client
        client = Client(
            **{k: v for k, v in client_data.items() if k != "code"},
            code=client_code,
            counselor_id=counselor.id,
            tenant_id=tenant_id,
        )
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)

        return client

    def list_clients(
        self,
        counselor: Counselor,
        tenant_id: str,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
    ) -> Tuple[List[Client], int]:
        """List all clients for counselor

        Args:
            counselor: Current counselor
            tenant_id: Tenant ID
            skip: Pagination offset
            limit: Number of items per page
            search: Optional search query

        Returns:
            Tuple of (clients list, total count)
        """
        # Base query
        query = select(Client).where(
            Client.counselor_id == counselor.id,
            Client.tenant_id == tenant_id,
            Client.deleted_at.is_(None),
        )

        # Add search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Client.name.ilike(search_pattern),
                    Client.nickname.ilike(search_pattern),
                    Client.code.ilike(search_pattern),
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(Client.created_at.desc())
        result = self.db.execute(query)
        clients = result.scalars().all()

        return list(clients), total

    def get_client_by_id(
        self,
        client_id: UUID,
        counselor: Counselor,
        tenant_id: str,
    ) -> Optional[Client]:
        """Get client by ID with permission check

        Args:
            client_id: Client UUID
            counselor: Current counselor
            tenant_id: Tenant ID

        Returns:
            Client or None if not found
        """
        result = self.db.execute(
            select(Client).where(
                Client.id == client_id,
                Client.counselor_id == counselor.id,
                Client.tenant_id == tenant_id,
                Client.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def update_client(
        self,
        client_id: UUID,
        update_data: dict,
        counselor: Counselor,
        tenant_id: str,
    ) -> Client:
        """Update a client

        Args:
            client_id: Client UUID
            update_data: Updated client information
            counselor: Current counselor
            tenant_id: Tenant ID

        Returns:
            Updated client

        Raises:
            HTTPException: If client not found or code conflict
        """
        client = self.get_client_by_id(client_id, counselor, tenant_id)

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

        # Auto-calculate age from birth_date if updated
        if "birth_date" in update_data and update_data["birth_date"]:
            update_data["age"] = self.calculate_age_from_birth_date(
                update_data["birth_date"]
            )

        # Check if code is being updated and if it conflicts
        if "code" in update_data and update_data["code"] != client.code:
            existing = self.db.execute(
                select(Client).where(
                    Client.code == update_data["code"],
                    Client.tenant_id == tenant_id,
                    Client.id != client_id,
                    Client.deleted_at.is_(None),
                )
            ).scalar_one_or_none()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Client code '{update_data['code']}' already exists",
                )

        # Update fields
        for field, value in update_data.items():
            setattr(client, field, value)

        self.db.commit()
        self.db.refresh(client)

        return client

    def delete_client(
        self,
        client_id: UUID,
        counselor: Counselor,
        tenant_id: str,
    ) -> None:
        """Soft delete a client (sets deleted_at timestamp)

        Args:
            client_id: Client UUID
            counselor: Current counselor
            tenant_id: Tenant ID

        Raises:
            HTTPException: If client not found
        """
        # Build query conditions
        conditions = [
            Client.id == client_id,
            Client.tenant_id == tenant_id,
            Client.deleted_at.is_(None),
        ]

        # Non-admin users can only delete their own clients
        if counselor.role != CounselorRole.ADMIN:
            conditions.append(Client.counselor_id == counselor.id)

        result = self.db.execute(select(Client).where(*conditions))
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

        # Soft delete
        client.deleted_at = datetime.now(timezone.utc)
        self.db.commit()

    def get_client_timeline(
        self,
        client_id: UUID,
        counselor: Counselor,
        tenant_id: str,
    ) -> Tuple[Client, List[dict]]:
        """Get client timeline with all sessions

        Args:
            client_id: Client UUID
            counselor: Current counselor
            tenant_id: Tenant ID

        Returns:
            Tuple of (client, timeline_items)

        Raises:
            HTTPException: If client not found
        """
        # Verify client exists and belongs to counselor
        client = self.get_client_by_id(client_id, counselor, tenant_id)

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found",
            )

        # Query all sessions with reports
        query = (
            select(SessionModel, Report.id.label("report_id"))
            .join(Case, SessionModel.case_id == Case.id)
            .outerjoin(
                Report,
                (Report.session_id == SessionModel.id)
                & (Report.status == ReportStatus.DRAFT),
            )
            .where(Case.client_id == client_id, SessionModel.tenant_id == tenant_id)
            .order_by(SessionModel.session_date.asc())
        )

        result = self.db.execute(query)
        rows = result.all()

        # Build timeline data
        timeline_items = []
        for session, report_id in rows:
            # Format time range
            time_range = None
            if session.start_time and session.end_time:
                start = session.start_time.strftime("%H:%M")
                end = session.end_time.strftime("%H:%M")
                time_range = f"{start}-{end}"

            timeline_items.append(
                {
                    "session_id": session.id,
                    "session_number": session.session_number,
                    "date": session.session_date.strftime("%Y-%m-%d"),
                    "time_range": time_range,
                    "summary": session.summary,
                    "has_report": report_id is not None,
                    "report_id": report_id,
                }
            )

        return client, timeline_items
