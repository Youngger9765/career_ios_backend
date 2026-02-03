"""
Integration tests for Session Append Recording API (iOS-friendly)
TDD - Write tests first
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_append_recording.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh test database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Create test client with overridden DB dependency"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_counselor(db_session: DBSession):
    """Create a test counselor"""
    counselor = Counselor(
        id=uuid4(),
        email="counselor@test.com",
        username="test_counselor",
        full_name="Test Counselor",
        hashed_password=hash_password("ValidP@ssw0rd123"),
        tenant_id="test_tenant",
        role="counselor",
        is_active=True,
    )
    db_session.add(counselor)
    db_session.commit()
    db_session.refresh(counselor)
    return counselor


@pytest.fixture
def test_client_data(db_session: DBSession, test_counselor: Counselor):
    """Create a test client"""
    from datetime import date

    client = Client(
        id=uuid4(),
        name="Test Client",
        code="TC001",
        email="testclient@test.com",
        gender="其他",
        birth_date=date(1990, 1, 1),
        phone="0912345678",
        identity_option="學生",
        current_status="探索中",
        counselor_id=test_counselor.id,
        tenant_id="test_tenant",
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


@pytest.fixture
def test_case(
    db_session: DBSession, test_client_data: Client, test_counselor: Counselor
):
    """Create a test case"""
    case = Case(
        id=uuid4(),
        client_id=test_client_data.id,
        counselor_id=test_counselor.id,
        tenant_id="test_tenant",
        case_number="CASE-001",
        status="ACTIVE",
    )
    db_session.add(case)
    db_session.commit()
    db_session.refresh(case)
    return case


@pytest.fixture
def test_session(db_session: DBSession, test_case: Case):
    """Create a test session without any recordings"""
    session = Session(
        id=uuid4(),
        case_id=test_case.id,
        tenant_id="test_tenant",
        session_number=1,
        session_date=datetime.now(timezone.utc),
        transcript_text="",
        recordings=[],
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def auth_token(client, test_counselor: Counselor):
    """Get authentication token for test counselor"""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "counselor@test.com",
            "password": "ValidP@ssw0rd123",
            "tenant_id": "test_tenant",
        },
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]


class TestAppendRecordingAPI:
    """Test POST /api/v1/sessions/{session_id}/recordings/append"""

    def test_append_first_recording_success(
        self, client, test_session: Session, auth_token: str
    ):
        """Test appending the first recording to an empty session"""
        # Arrange
        request_data = {
            "start_time": "2025-01-15 10:00",
            "end_time": "2025-01-15 10:30",
            "duration_seconds": 1800,
            "transcript_text": "這是第一段錄音的逐字稿",
            "transcript_sanitized": "這是第一段錄音的逐字稿",
        }

        # Act
        response = client.post(
            f"/api/v1/sessions/{test_session.id}/recordings/append",
            json=request_data,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == str(test_session.id)
        assert data["total_recordings"] == 1
        assert data["recording_added"]["segment_number"] == 1
        assert data["recording_added"]["transcript_text"] == "這是第一段錄音的逐字稿"
        assert "這是第一段錄音的逐字稿" in data["transcript_text"]

    def test_append_multiple_recordings_increments_segment_number(
        self, client, test_session: Session, auth_token: str
    ):
        """Test appending multiple recordings auto-increments segment_number"""
        # Arrange - Append first recording
        first_request = {
            "start_time": "2025-01-15 10:00",
            "end_time": "2025-01-15 10:30",
            "duration_seconds": 1800,
            "transcript_text": "第一段",
        }
        response1 = client.post(
            f"/api/v1/sessions/{test_session.id}/recordings/append",
            json=first_request,
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response1.status_code == 200
        assert response1.json()["recording_added"]["segment_number"] == 1

        # Act - Append second recording
        second_request = {
            "start_time": "2025-01-15 10:35",
            "end_time": "2025-01-15 11:00",
            "duration_seconds": 1500,
            "transcript_text": "第二段",
        }
        response2 = client.post(
            f"/api/v1/sessions/{test_session.id}/recordings/append",
            json=second_request,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Assert
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["recording_added"]["segment_number"] == 2
        assert data2["total_recordings"] == 2

        # Act - Append third recording
        third_request = {
            "start_time": "2025-01-15 11:05",
            "end_time": "2025-01-15 11:30",
            "duration_seconds": 1500,
            "transcript_text": "第三段",
        }
        response3 = client.post(
            f"/api/v1/sessions/{test_session.id}/recordings/append",
            json=third_request,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Assert
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["recording_added"]["segment_number"] == 3
        assert data3["total_recordings"] == 3

    def test_append_aggregates_transcript_text(
        self, client, test_session: Session, auth_token: str
    ):
        """Test that transcript_text is aggregated from all recordings"""
        # Arrange & Act - Add 3 recordings
        recordings = [
            {"transcript_text": "第一段內容", "duration_seconds": 1800},
            {"transcript_text": "第二段內容", "duration_seconds": 1500},
            {"transcript_text": "第三段內容", "duration_seconds": 1200},
        ]

        for i, rec in enumerate(recordings):
            request_data = {
                "start_time": f"2025-01-15 10:{i*10:02d}",
                "end_time": f"2025-01-15 10:{(i+1)*10:02d}",
                "duration_seconds": rec["duration_seconds"],
                "transcript_text": rec["transcript_text"],
            }
            client.post(
                f"/api/v1/sessions/{test_session.id}/recordings/append",
                json=request_data,
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        # Assert - Get final session and check aggregated transcript
        response = client.get(
            f"/api/v1/sessions/{test_session.id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        transcript = data["transcript_text"]

        # Should contain all segments separated by double newlines
        assert "第一段內容" in transcript
        assert "第二段內容" in transcript
        assert "第三段內容" in transcript

    def test_append_with_sanitized_text(
        self, client, test_session: Session, auth_token: str
    ):
        """Test appending recording with sanitized text"""
        # Arrange
        request_data = {
            "start_time": "2025-01-15 10:00",
            "end_time": "2025-01-15 10:30",
            "duration_seconds": 1800,
            "transcript_text": "我的名字是張三，住在台北市。",
            "transcript_sanitized": "我的名字是XXX，住在XXX。",
        }

        # Act
        response = client.post(
            f"/api/v1/sessions/{test_session.id}/recordings/append",
            json=request_data,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert (
            data["recording_added"]["transcript_text"] == "我的名字是張三，住在台北市。"
        )
        assert (
            data["recording_added"]["transcript_sanitized"]
            == "我的名字是XXX，住在XXX。"
        )

    def test_append_without_sanitized_defaults_to_original(
        self, client, test_session: Session, auth_token: str
    ):
        """Test that transcript_sanitized defaults to transcript_text if not provided"""
        # Arrange
        request_data = {
            "start_time": "2025-01-15 10:00",
            "end_time": "2025-01-15 10:30",
            "duration_seconds": 1800,
            "transcript_text": "測試內容",
        }

        # Act
        response = client.post(
            f"/api/v1/sessions/{test_session.id}/recordings/append",
            json=request_data,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["recording_added"]["transcript_sanitized"] == "測試內容"

    def test_append_to_nonexistent_session_returns_404(self, client, auth_token: str):
        """Test appending to non-existent session returns 404"""
        # Arrange
        fake_session_id = uuid4()
        request_data = {
            "start_time": "2025-01-15 10:00",
            "end_time": "2025-01-15 10:30",
            "duration_seconds": 1800,
            "transcript_text": "測試",
        }

        # Act
        response = client.post(
            f"/api/v1/sessions/{fake_session_id}/recordings/append",
            json=request_data,
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_append_without_auth_returns_401(self, client, test_session: Session):
        """Test appending without authentication returns 401/403"""
        # Arrange
        request_data = {
            "start_time": "2025-01-15 10:00",
            "end_time": "2025-01-15 10:30",
            "duration_seconds": 1800,
            "transcript_text": "測試",
        }

        # Act
        response = client.post(
            f"/api/v1/sessions/{test_session.id}/recordings/append",
            json=request_data,
        )

        # Assert - both 401 and 403 are acceptable for missing auth
        assert response.status_code in [401, 403]
