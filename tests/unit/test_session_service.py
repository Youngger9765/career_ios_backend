"""
Unit tests for SessionService - TDD Phase 2
"""
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.models.case import Case
from app.models.client import Client
from app.models.session import Session
from app.repositories.session_repository import SessionRepository
from app.schemas.session import (
    SessionCreateRequest,
    SessionUpdateRequest,
)
from app.services.session_service import SessionService


class TestSessionService:
    """Test SessionService business logic"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = Mock()
        db.commit = Mock()
        db.rollback = Mock()
        db.refresh = Mock()
        db.flush = Mock()
        return db

    @pytest.fixture
    def mock_session_repo(self):
        """Mock SessionRepository"""
        return Mock(spec=SessionRepository)

    @pytest.fixture
    def session_service(self, mock_db, mock_session_repo):
        """Create SessionService with mocked dependencies"""
        service = SessionService(mock_db)
        service.session_repo = mock_session_repo
        return service

    @pytest.fixture
    def sample_counselor(self):
        """Sample counselor for testing"""
        counselor = Mock()
        counselor.id = uuid4()
        counselor.tenant_id = "career"
        counselor.role = "counselor"
        return counselor

    @pytest.fixture
    def sample_case(self):
        """Sample case for testing"""
        case = Mock(spec=Case)
        case.id = uuid4()
        case.client_id = uuid4()
        case.tenant_id = "career"
        case.deleted_at = None
        return case

    @pytest.fixture
    def sample_client(self):
        """Sample client for testing"""
        client = Mock(spec=Client)
        client.id = uuid4()
        client.name = "Test Client"
        client.code = "CLI001"
        return client

    def test_create_session_success(
        self,
        session_service,
        mock_session_repo,
        sample_counselor,
        sample_case,
        sample_client,
    ):
        """Test successful session creation"""
        # Arrange
        request = SessionCreateRequest(
            case_id=sample_case.id,
            session_date="2025-01-15",
            name="Initial Session",
            notes="First meeting",
        )

        mock_session_repo.get_case_by_id.return_value = sample_case
        mock_session_repo.get_client_by_id.return_value = sample_client
        mock_session_repo.get_sessions_by_case.return_value = []  # No existing sessions

        created_session = Mock(spec=Session)
        created_session.id = uuid4()
        created_session.session_number = 1
        mock_session_repo.create.return_value = created_session

        # Act
        result = session_service.create_session(request, sample_counselor, "career")

        # Assert
        assert result is not None
        mock_session_repo.get_case_by_id.assert_called_once_with(
            sample_case.id, "career"
        )
        mock_session_repo.create.assert_called_once()
        assert mock_session_repo.create.call_args[1]["session_number"] == 1

    def test_create_session_with_existing_sessions(
        self,
        session_service,
        mock_session_repo,
        sample_counselor,
        sample_case,
        sample_client,
    ):
        """Test session number calculation with existing sessions"""
        # Arrange
        request = SessionCreateRequest(
            case_id=sample_case.id,
            session_date="2025-01-20",
            start_time="2025-01-20 14:00",
        )

        # Existing sessions
        existing_session1 = Mock()
        existing_session1.id = uuid4()
        existing_session1.session_date = datetime(2025, 1, 10, tzinfo=timezone.utc)
        existing_session1.start_time = datetime(2025, 1, 10, 10, 0, tzinfo=timezone.utc)
        existing_session1.session_number = 1

        existing_session2 = Mock()
        existing_session2.id = uuid4()
        existing_session2.session_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        existing_session2.start_time = datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc)
        existing_session2.session_number = 2

        mock_session_repo.get_case_by_id.return_value = sample_case
        mock_session_repo.get_client_by_id.return_value = sample_client
        mock_session_repo.get_sessions_by_case.return_value = [
            existing_session1,
            existing_session2,
        ]

        created_session = Mock(spec=Session)
        created_session.id = uuid4()
        created_session.session_number = 3  # Should be 3rd session
        mock_session_repo.create.return_value = created_session

        # Act
        result = session_service.create_session(request, sample_counselor, "career")

        # Assert
        assert result is not None
        assert mock_session_repo.create.call_args[1]["session_number"] == 3

    def test_create_session_case_not_found(
        self, session_service, mock_session_repo, sample_counselor
    ):
        """Test session creation when case doesn't exist"""
        # Arrange
        request = SessionCreateRequest(
            case_id=uuid4(),
            session_date="2025-01-15",
        )

        mock_session_repo.get_case_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Case not found"):
            session_service.create_session(request, sample_counselor, "career")

    def test_get_session_success(
        self, session_service, mock_session_repo, sample_counselor
    ):
        """Test successful session retrieval"""
        # Arrange
        session_id = uuid4()
        session = Mock(spec=Session)
        session.id = session_id
        session.case_id = uuid4()

        case = Mock(spec=Case)
        case.client_id = uuid4()

        client = Mock(spec=Client)
        client.counselor_id = sample_counselor.id
        client.tenant_id = "career"

        mock_session_repo.get_by_id.return_value = session
        mock_session_repo.get_case_by_id.return_value = case
        mock_session_repo.get_client_by_id.return_value = client

        # Act
        result = session_service.get_session(session_id, sample_counselor, "career")

        # Assert
        assert result == session
        mock_session_repo.get_by_id.assert_called_once_with(session_id)

    def test_get_session_unauthorized(
        self, session_service, mock_session_repo, sample_counselor
    ):
        """Test session retrieval by unauthorized counselor"""
        # Arrange
        session_id = uuid4()
        session = Mock(spec=Session)
        session.id = session_id
        session.case_id = uuid4()

        case = Mock(spec=Case)
        case.client_id = uuid4()

        client = Mock(spec=Client)
        client.counselor_id = uuid4()  # Different counselor
        client.tenant_id = "career"

        mock_session_repo.get_by_id.return_value = session
        mock_session_repo.get_case_by_id.return_value = case
        mock_session_repo.get_client_by_id.return_value = client

        # Act & Assert
        with pytest.raises(PermissionError, match="Not authorized"):
            session_service.get_session(session_id, sample_counselor, "career")

    def test_list_sessions_with_filters(
        self, session_service, mock_session_repo, sample_counselor
    ):
        """Test listing sessions with filters"""
        # Arrange
        client_id = uuid4()
        sessions = [Mock(spec=Session) for _ in range(3)]

        mock_session_repo.list_sessions.return_value = (sessions, 3)

        # Act
        result, total = session_service.list_sessions(
            counselor=sample_counselor,
            tenant_id="career",
            client_id=client_id,
            skip=0,
            limit=20,
        )

        # Assert
        assert len(result) == 3
        assert total == 3
        mock_session_repo.list_sessions.assert_called_once_with(
            counselor_id=sample_counselor.id,
            tenant_id="career",
            client_id=client_id,
            search=None,
            skip=0,
            limit=20,
        )

    def test_update_session_success(
        self, session_service, mock_session_repo, sample_counselor
    ):
        """Test successful session update"""
        # Arrange
        session_id = uuid4()
        request = SessionUpdateRequest(
            name="Updated Session",
            notes="Updated notes",
        )

        session = Mock(spec=Session)
        session.id = session_id
        session.case_id = uuid4()

        case = Mock(spec=Case)
        case.client_id = uuid4()

        client = Mock(spec=Client)
        client.counselor_id = sample_counselor.id
        client.tenant_id = "career"

        mock_session_repo.get_by_id.return_value = session
        mock_session_repo.get_case_by_id.return_value = case
        mock_session_repo.get_client_by_id.return_value = client
        mock_session_repo.update.return_value = session

        # Act
        result = session_service.update_session(
            session_id, request, sample_counselor, "career"
        )

        # Assert
        assert result == session
        mock_session_repo.update.assert_called_once()

    def test_delete_session_success(
        self, session_service, mock_session_repo, sample_counselor
    ):
        """Test successful session deletion"""
        # Arrange
        session_id = uuid4()
        session = Mock(spec=Session)
        session.id = session_id
        session.case_id = uuid4()

        case = Mock(spec=Case)
        case.client_id = uuid4()

        client = Mock(spec=Client)
        client.counselor_id = sample_counselor.id
        client.tenant_id = "career"

        mock_session_repo.get_by_id.return_value = session
        mock_session_repo.get_case_by_id.return_value = case
        mock_session_repo.get_client_by_id.return_value = client
        mock_session_repo.has_reports.return_value = False

        # Act
        session_service.delete_session(session_id, sample_counselor, "career")

        # Assert
        mock_session_repo.soft_delete.assert_called_once_with(session)

    def test_delete_session_with_reports_fails(
        self, session_service, mock_session_repo, sample_counselor
    ):
        """Test deletion fails when session has reports"""
        # Arrange
        session_id = uuid4()
        session = Mock(spec=Session)
        session.id = session_id
        session.case_id = uuid4()

        case = Mock(spec=Case)
        case.client_id = uuid4()

        client = Mock(spec=Client)
        client.counselor_id = sample_counselor.id
        client.tenant_id = "career"

        mock_session_repo.get_by_id.return_value = session
        mock_session_repo.get_case_by_id.return_value = case
        mock_session_repo.get_client_by_id.return_value = client
        mock_session_repo.has_reports.return_value = True  # Has reports

        # Act & Assert
        with pytest.raises(ValueError, match="Cannot delete session with reports"):
            session_service.delete_session(session_id, sample_counselor, "career")

    def test_calculate_session_number_for_inserted_session(
        self, session_service, mock_session_repo
    ):
        """Test session number calculation when inserting between existing sessions"""
        # Arrange
        new_date = datetime(2025, 1, 12, 14, 0, tzinfo=timezone.utc)

        existing_sessions = [
            Mock(
                session_date=datetime(2025, 1, 10, tzinfo=timezone.utc),
                start_time=datetime(2025, 1, 10, 10, 0, tzinfo=timezone.utc),
                session_number=1,
            ),
            Mock(
                session_date=datetime(2025, 1, 15, tzinfo=timezone.utc),
                start_time=datetime(2025, 1, 15, 14, 0, tzinfo=timezone.utc),
                session_number=2,
            ),
            Mock(
                session_date=datetime(2025, 1, 20, tzinfo=timezone.utc),
                start_time=datetime(2025, 1, 20, 10, 0, tzinfo=timezone.utc),
                session_number=3,
            ),
        ]

        # Act
        session_number, needs_renumbering = session_service._calculate_session_number(
            new_date, existing_sessions
        )

        # Assert
        assert session_number == 2  # Should be inserted as session 2
        assert needs_renumbering is True  # Following sessions need renumbering
