"""Service layer for case CRUD operations"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor, CounselorRole


class CaseService:
    """Service for case operations"""

    def __init__(self, db: Session):
        self.db = db

    def generate_case_number(self, tenant_id: str) -> str:
        """Generate unique case number in format CASE0001, CASE0002, etc.

        Args:
            tenant_id: Tenant ID

        Returns:
            Generated case number
        """
        result = self.db.execute(
            select(Case.case_number)
            .where(Case.tenant_id == tenant_id)
            .where(Case.case_number.like("CASE%"))
            .where(Case.deleted_at.is_(None))
            .order_by(Case.case_number.desc())
        )
        numbers = result.scalars().all()

        # Extract numbers and find max
        max_num = 0
        for num_str in numbers:
            if num_str.startswith("CASE") and num_str[4:].isdigit():
                num = int(num_str[4:])
                if num > max_num:
                    max_num = num

        # Generate next number
        next_num = max_num + 1
        return f"CASE{next_num:04d}"

    def list_cases(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        client_id: Optional[UUID] = None,
    ) -> Tuple[List[Case], int]:
        """List cases with optional filtering

        Args:
            tenant_id: Tenant ID
            skip: Pagination offset
            limit: Number of items per page
            client_id: Optional client ID filter

        Returns:
            Tuple of (cases list, total count)
        """
        query = select(Case).where(
            Case.tenant_id == tenant_id,
            Case.deleted_at.is_(None),
        )

        if client_id:
            query = query.where(Case.client_id == client_id)

        query = query.order_by(Case.created_at.desc())

        # Get total count
        count_query = (
            select(func.count()).select_from(Case).where(Case.tenant_id == tenant_id)
        )
        if client_id:
            count_query = count_query.where(Case.client_id == client_id)
        total_count = self.db.execute(count_query).scalar() or 0

        # Get paginated results
        result = self.db.execute(query.offset(skip).limit(limit))
        cases = result.scalars().all()

        return list(cases), total_count

    def create_case(
        self,
        case_data: dict,
        counselor: Counselor,
        tenant_id: str,
    ) -> Case:
        """Create a new case

        Args:
            case_data: Case information dictionary
            counselor: Current counselor
            tenant_id: Tenant ID

        Returns:
            Created case

        Raises:
            HTTPException: If case number exists or client not found
        """
        # Auto-generate case_number if not provided
        case_number = case_data.get("case_number")
        if not case_number:
            case_number = self.generate_case_number(tenant_id)

        # Check if case number already exists
        result = self.db.execute(
            select(Case).where(
                Case.case_number == case_number,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Case number '{case_number}' already exists",
            )

        # Verify client exists and belongs to same tenant
        client_result = self.db.execute(
            select(Client).where(
                Client.id == case_data["client_id"],
                Client.tenant_id == tenant_id,
            )
        )
        client = client_result.scalar_one_or_none()
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {case_data['client_id']} not found or doesn't belong to this tenant",
            )

        # Create case
        new_case = Case(
            case_number=case_number,
            counselor_id=counselor.id,
            client_id=case_data["client_id"],
            tenant_id=tenant_id,
            status=case_data.get("status"),
            summary=case_data.get("summary"),
            goals=case_data.get("goals"),
            problem_description=case_data.get("problem_description"),
        )

        self.db.add(new_case)
        self.db.commit()
        self.db.refresh(new_case)

        return new_case

    def get_case_by_id(
        self,
        case_id: UUID,
        tenant_id: str,
    ) -> Optional[Case]:
        """Get case by ID

        Args:
            case_id: Case UUID
            tenant_id: Tenant ID

        Returns:
            Case or None if not found
        """
        result = self.db.execute(
            select(Case).where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def update_case(
        self,
        case_id: UUID,
        update_data: dict,
        tenant_id: str,
    ) -> Case:
        """Update a case

        Args:
            case_id: Case UUID
            update_data: Updated case information
            tenant_id: Tenant ID

        Returns:
            Updated case

        Raises:
            HTTPException: If case not found or case number conflict
        """
        case = self.get_case_by_id(case_id, tenant_id)

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found",
            )

        # Check if case_number is being updated and if it conflicts
        if (
            "case_number" in update_data
            and update_data["case_number"] != case.case_number
        ):
            existing = self.db.execute(
                select(Case).where(
                    Case.case_number == update_data["case_number"],
                    Case.tenant_id == tenant_id,
                    Case.id != case_id,
                    Case.deleted_at.is_(None),
                )
            ).scalar_one_or_none()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Case number '{update_data['case_number']}' already exists",
                )

        # Update fields
        for field, value in update_data.items():
            if hasattr(case, field):
                setattr(case, field, value)

        self.db.commit()
        self.db.refresh(case)

        return case

    def delete_case(
        self,
        case_id: UUID,
        counselor: Counselor,
        tenant_id: str,
    ) -> None:
        """Soft delete a case

        Args:
            case_id: Case UUID
            counselor: Current counselor
            tenant_id: Tenant ID

        Raises:
            HTTPException: If case not found or permission denied
        """
        conditions = [
            Case.id == case_id,
            Case.tenant_id == tenant_id,
            Case.deleted_at.is_(None),
        ]

        # Non-admin users can only delete their own cases
        if counselor.role != CounselorRole.ADMIN:
            conditions.append(Case.counselor_id == counselor.id)

        result = self.db.execute(select(Case).where(*conditions))
        case = result.scalar_one_or_none()

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found",
            )

        # Soft delete
        case.deleted_at = datetime.now(timezone.utc)
        self.db.commit()
