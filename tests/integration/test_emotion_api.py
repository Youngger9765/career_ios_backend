"""
Integration tests for Emotion Analysis API
TDD - Write tests first, then implement

Tests cover:
1. Green light scenario (良好溝通)
2. Yellow light scenario (警告)
3. Red light scenario (危險)
4. Invalid format errors
5. Session not found
6. Performance requirements (<3 seconds)
"""
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password

# Tests enabled - emotion API bugs fixed
# pytestmark = pytest.mark.skip(
#     reason="Skipped in CI due to Gemini API usage (expensive)"
# )
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session as SessionModel


class TestEmotionAnalysisAPI:
    """Test Emotion Analysis API"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="emotion-test@island-parents.com",
            username="emotiontest",
            full_name="Emotion Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "emotion-test@island-parents.com",
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_session_obj(self, db_session: Session, auth_headers):
        """Create a test session for emotion analysis tests"""
        from datetime import date

        counselor = (
            db_session.query(Counselor)
            .filter_by(email="emotion-test@island-parents.com")
            .first()
        )

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="island_parents",
            name="情緒測試家長",
            code="EMOCLI001",
            email="emocli001@example.com",
            gender="不透露",
            birth_date=date(1980, 1, 1),
            phone="0912345678",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(client)
        db_session.commit()

        case = Case(
            id=uuid4(),
            case_number="EMOCASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="island_parents",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)
        db_session.commit()

        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            name="情緒分析測試會談",
        )
        db_session.add(session)
        db_session.commit()

        return session

    def test_green_light_scenario(
        self, db_session: Session, auth_headers, test_session_obj
    ):
        """
        Scenario 1: 綠燈（良好溝通）
        Parent shows empathy and constructive communication
        Expected: level=1, hint length <=17 chars
        """
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{test_session_obj.id}/emotion-feedback",
                headers=auth_headers,
                json={
                    "context": "小明：我今天很開心\n媽媽：發生什麼好事了？",
                    "target": "媽媽願意聽你分享，真好",
                },
            )

            assert response.status_code == 200, f"Failed: {response.json()}"
            data = response.json()

            # Verify structure
            assert "level" in data
            assert "hint" in data

            # Verify green light
            assert data["level"] == 1, f"Expected level 1, got {data['level']}"

            # Verify hint constraints
            assert len(data["hint"]) <= 17, f"Hint too long: {len(data['hint'])} chars"
            assert isinstance(data["hint"], str)

    def test_yellow_light_scenario(
        self, db_session: Session, auth_headers, test_session_obj
    ):
        """
        Scenario 2: 黃燈（警告）
        Parent shows slight impatience but not out of control
        Expected: level=2, hint length <=17 chars
        """
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{test_session_obj.id}/emotion-feedback",
                headers=auth_headers,
                json={
                    "context": "小明：作業我不會寫\n媽媽：你上課有認真聽嗎？",
                    "target": "你怎麼又不會？",
                },
            )

            assert response.status_code == 200, f"Failed: {response.json()}"
            data = response.json()

            # Verify yellow light
            assert data["level"] == 2, f"Expected level 2, got {data['level']}"

            # Verify hint constraints
            assert len(data["hint"]) <= 17, f"Hint too long: {len(data['hint'])} chars"

    def test_red_light_scenario(
        self, db_session: Session, auth_headers, test_session_obj
    ):
        """
        Scenario 3: 紅燈（危險）
        Parent shows strong negative emotion and potential harm
        Expected: level=3, hint length <=17 chars
        """
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{test_session_obj.id}/emotion-feedback",
                headers=auth_headers,
                json={
                    "context": "小明：我考試不及格\n媽媽：你有認真準備嗎？",
                    "target": "你就是不用功！笨死了！",
                },
            )

            assert response.status_code == 200, f"Failed: {response.json()}"
            data = response.json()

            # Verify red light
            assert data["level"] == 3, f"Expected level 3, got {data['level']}"

            # Verify hint constraints
            assert len(data["hint"]) <= 17, f"Hint too long: {len(data['hint'])} chars"

    def test_invalid_format_empty_context(
        self, db_session: Session, auth_headers, test_session_obj
    ):
        """
        Scenario 4: Invalid format - empty context
        Expected: 422 Unprocessable Entity (Pydantic validation)
        """
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{test_session_obj.id}/emotion-feedback",
                headers=auth_headers,
                json={
                    "context": "",  # Empty context
                    "target": "測試",
                },
            )

            assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    def test_invalid_format_empty_target(
        self, db_session: Session, auth_headers, test_session_obj
    ):
        """
        Scenario 4: Invalid format - empty target
        Expected: 422 Unprocessable Entity (Pydantic validation)
        """
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{test_session_obj.id}/emotion-feedback",
                headers=auth_headers,
                json={
                    "context": "測試",
                    "target": "",  # Empty target
                },
            )

            assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    def test_session_not_found(self, db_session: Session, auth_headers):
        """
        Scenario 5: Session not found
        Expected: 404 Not Found
        """
        non_existent_id = uuid4()

        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{non_existent_id}/emotion-feedback",
                headers=auth_headers,
                json={
                    "context": "測試上下文",
                    "target": "測試目標",
                },
            )

            assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    def test_response_time_performance(
        self, db_session: Session, auth_headers, test_session_obj
    ):
        """
        Scenario 6: Performance test
        Expected: Response time < 3 seconds
        """
        with TestClient(app) as client:
            start_time = time.time()

            response = client.post(
                f"/api/v1/sessions/{test_session_obj.id}/emotion-feedback",
                headers=auth_headers,
                json={
                    "context": "小明：今天好累\n媽媽：早點休息吧",
                    "target": "你辛苦了，早點睡",
                },
            )

            elapsed = time.time() - start_time

            # Verify response succeeded
            assert response.status_code == 200, f"Failed: {response.json()}"

            # Verify performance requirement
            assert (
                elapsed < 3.0
            ), f"Response took {elapsed:.2f}s (max 3s)"

            print(f"✓ Response time: {elapsed:.2f}s")

    def test_unauthorized_access(self, db_session: Session, test_session_obj):
        """
        Security test: Verify endpoint requires authentication
        Expected: 401 Unauthorized or 403 Forbidden
        """
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{test_session_obj.id}/emotion-feedback",
                # No auth headers
                json={
                    "context": "測試",
                    "target": "測試",
                },
            )

            assert response.status_code in [401, 403], \
                f"Expected 401 or 403, got {response.status_code}"
