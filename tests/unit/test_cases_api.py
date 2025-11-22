"""
Unit tests for Case API endpoints
Tests the API logic without requiring a real database
"""
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.cases import (
    _generate_case_number,
    create_case,
    delete_case,
    get_case,
    list_cases,
    update_case,
)
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor
from app.schemas.case import CaseCreate, CaseUpdate


def create_mock_case(**kwargs):
    """Helper to create a mock Case with all required fields"""
    defaults = {
        "id": uuid4(),
        "case_number": "CASE0001",
        "counselor_id": uuid4(),
        "client_id": uuid4(),
        "tenant_id": "career",
        "status": CaseStatus.ACTIVE,
        "summary": None,
        "goals": None,
        "problem_description": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    defaults.update(kwargs)

    mock_case = MagicMock(spec=Case)
    for key, value in defaults.items():
        setattr(mock_case, key, value)

    return mock_case


class TestCaseNumberGeneration:
    """Test case number auto-generation logic"""

    def test_generate_first_case_number(self):
        """Test generating the first case number"""
        db = MagicMock(spec=Session)

        # Mock no existing cases
        db.execute().scalars().all.return_value = []

        result = _generate_case_number(db, "career")

        assert result == "CASE0001"

    def test_generate_sequential_case_numbers(self):
        """Test generating sequential case numbers"""
        db = MagicMock(spec=Session)

        # Mock existing cases
        db.execute().scalars().all.return_value = ["CASE0001", "CASE0002", "CASE0005"]

        result = _generate_case_number(db, "career")

        assert result == "CASE0006"  # Should be max + 1

    def test_generate_case_number_handles_gaps(self):
        """Test generating case number with gaps in sequence"""
        db = MagicMock(spec=Session)

        # Mock cases with gaps
        db.execute().scalars().all.return_value = ["CASE0001", "CASE0010", "CASE0003"]

        result = _generate_case_number(db, "career")

        assert result == "CASE0011"  # Should use max (CASE0010) + 1

    def test_generate_case_number_ignores_invalid_formats(self):
        """Test that invalid case numbers are ignored"""
        db = MagicMock(spec=Session)

        # Mock mix of valid and invalid case numbers
        db.execute().scalars().all.return_value = [
            "CASE0001",
            "INVALID",
            "CASE0002",
            "CASEXXX",  # Not digits
        ]

        result = _generate_case_number(db, "career")

        assert result == "CASE0003"


class TestListCases:
    """Test listing cases with filters"""

    @patch("app.api.cases.get_tenant_id")
    @patch("app.api.cases.get_current_user")
    def test_list_cases_returns_paginated_results(
        self, mock_get_current_user, mock_get_tenant_id
    ):
        """Test list_cases returns items and count"""
        db = MagicMock(spec=Session)

        # Mock tenant and user
        mock_get_tenant_id.return_value = "career"
        mock_counselor = MagicMock(spec=Counselor)
        mock_get_current_user.return_value = mock_counselor

        # Mock cases
        case1 = create_mock_case(case_number="CASE0001", status=CaseStatus.NOT_STARTED)
        case2 = create_mock_case(case_number="CASE0002", status=CaseStatus.COMPLETED)

        # Mock count query
        db.execute().scalar.return_value = 2

        # Mock select query
        db.execute().scalars().all.return_value = [case1, case2]

        result = list_cases(
            client_id=None,
            skip=0,
            limit=100,
            current_user=mock_counselor,
            tenant_id="career",
            db=db,
        )

        assert result["total"] == 2
        assert result["skip"] == 0
        assert result["limit"] == 100
        assert len(result["items"]) == 2

    @patch("app.api.cases.get_tenant_id")
    @patch("app.api.cases.get_current_user")
    def test_list_cases_filters_by_client_id(
        self, mock_get_current_user, mock_get_tenant_id
    ):
        """Test filtering cases by client_id"""
        db = MagicMock(spec=Session)

        mock_get_tenant_id.return_value = "career"
        mock_counselor = MagicMock(spec=Counselor)
        mock_get_current_user.return_value = mock_counselor

        client_id = uuid4()
        case1 = create_mock_case(case_number="CASE0001", client_id=client_id)

        db.execute().scalar.return_value = 1
        db.execute().scalars().all.return_value = [case1]

        result = list_cases(
            client_id=client_id,
            skip=0,
            limit=100,
            current_user=mock_counselor,
            tenant_id="career",
            db=db,
        )

        assert result["total"] == 1
        assert result["items"][0].client_id == client_id


class TestCreateCase:
    """Test case creation"""

    def test_create_case_success(self):
        """Test creating a case successfully"""
        db = MagicMock(spec=Session)
        mock_counselor = MagicMock(spec=Counselor)
        mock_counselor.id = uuid4()

        client_id = uuid4()

        # Mock no duplicate case number
        db.execute().scalar_one_or_none.return_value = None

        # Mock client exists
        mock_client = MagicMock(spec=Client)
        mock_client.id = client_id
        db.execute().scalar_one_or_none.side_effect = [None, mock_client]

        # Mock case number generation
        db.execute().scalars().all.return_value = []

        # Mock db.refresh to populate id and timestamps
        def refresh_case(case):
            case.id = uuid4()
            case.created_at = datetime.utcnow()
            case.updated_at = datetime.utcnow()

        db.refresh.side_effect = refresh_case

        case_data = CaseCreate(
            client_id=client_id,
            status=CaseStatus.NOT_STARTED,
            problem_description="職涯探索",
            goals="找到方向",
        )

        result = create_case(
            case_data=case_data,
            current_user=mock_counselor,
            tenant_id="career",
            db=db,
        )

        # Verify case was added to session
        assert db.add.called
        assert db.commit.called
        assert db.refresh.called

    def test_create_case_duplicate_number_fails(self):
        """Test creating case with duplicate number raises error"""
        db = MagicMock(spec=Session)
        mock_counselor = MagicMock(spec=Counselor)
        mock_counselor.id = uuid4()

        # Mock duplicate case number exists
        existing_case = MagicMock(spec=Case)
        db.execute().scalar_one_or_none.return_value = existing_case

        case_data = CaseCreate(
            client_id=uuid4(),
            case_number="CASE0001",
            status=CaseStatus.NOT_STARTED,
        )

        with pytest.raises(HTTPException) as exc_info:
            create_case(
                case_data=case_data,
                current_user=mock_counselor,
                tenant_id="career",
                db=db,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in str(exc_info.value.detail)

    def test_create_case_client_not_found(self):
        """Test creating case with non-existent client fails"""
        db = MagicMock(spec=Session)
        mock_counselor = MagicMock(spec=Counselor)
        mock_counselor.id = uuid4()

        client_id = uuid4()

        # Mock no duplicate case number
        # Mock client does not exist
        db.execute().scalar_one_or_none.side_effect = [None, None]

        # Mock case number generation
        db.execute().scalars().all.return_value = []

        case_data = CaseCreate(
            client_id=client_id,
            status=CaseStatus.NOT_STARTED,
        )

        with pytest.raises(HTTPException) as exc_info:
            create_case(
                case_data=case_data,
                current_user=mock_counselor,
                tenant_id="career",
                db=db,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc_info.value.detail)


class TestGetCase:
    """Test getting a specific case"""

    def test_get_case_success(self):
        """Test getting an existing case"""
        db = MagicMock(spec=Session)
        mock_counselor = MagicMock(spec=Counselor)

        case_id = uuid4()
        mock_case = create_mock_case(id=case_id, case_number="CASE0001")

        db.execute().scalar_one_or_none.return_value = mock_case

        result = get_case(
            case_id=case_id,
            current_user=mock_counselor,
            tenant_id="career",
            db=db,
        )

        assert result.id == case_id
        assert result.case_number == "CASE0001"

    def test_get_case_not_found(self):
        """Test getting non-existent case raises 404"""
        db = MagicMock(spec=Session)
        mock_counselor = MagicMock(spec=Counselor)

        db.execute().scalar_one_or_none.return_value = None

        case_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            get_case(
                case_id=case_id,
                current_user=mock_counselor,
                tenant_id="career",
                db=db,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateCase:
    """Test updating a case"""

    def test_update_case_success(self):
        """Test updating case fields"""
        db = MagicMock(spec=Session)
        mock_counselor = MagicMock(spec=Counselor)

        case_id = uuid4()
        mock_case = create_mock_case(
            id=case_id, case_number="CASE0001", summary="原始摘要"
        )

        db.execute().scalar_one_or_none.return_value = mock_case

        update_data = CaseUpdate(
            status=CaseStatus.COMPLETED,
            summary="更新的摘要",
        )

        result = update_case(
            case_id=case_id,
            case_data=update_data,
            current_user=mock_counselor,
            tenant_id="career",
            db=db,
        )

        assert db.commit.called
        assert mock_case.status == CaseStatus.COMPLETED
        assert mock_case.summary == "更新的摘要"

    def test_update_case_not_found(self):
        """Test updating non-existent case raises 404"""
        db = MagicMock(spec=Session)
        mock_counselor = MagicMock(spec=Counselor)

        db.execute().scalar_one_or_none.return_value = None

        case_id = uuid4()
        update_data = CaseUpdate(status=CaseStatus.COMPLETED)

        with pytest.raises(HTTPException) as exc_info:
            update_case(
                case_id=case_id,
                case_data=update_data,
                current_user=mock_counselor,
                tenant_id="career",
                db=db,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteCase:
    """Test deleting a case"""

    def test_delete_case_success(self):
        """Test deleting an existing case"""
        db = MagicMock(spec=Session)
        mock_counselor = MagicMock(spec=Counselor)

        case_id = uuid4()
        mock_case = create_mock_case(id=case_id, case_number="CASE0001")

        db.execute().scalar_one_or_none.return_value = mock_case

        delete_case(
            case_id=case_id,
            current_user=mock_counselor,
            tenant_id="career",
            db=db,
        )

        assert db.delete.called_with(mock_case)
        assert db.commit.called

    def test_delete_case_not_found(self):
        """Test deleting non-existent case raises 404"""
        db = MagicMock(spec=Session)
        mock_counselor = MagicMock(spec=Counselor)

        db.execute().scalar_one_or_none.return_value = None

        case_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            delete_case(
                case_id=case_id,
                current_user=mock_counselor,
                tenant_id="career",
                db=db,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
