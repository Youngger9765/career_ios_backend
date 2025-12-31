"""
Integration test to verify token_usage is included in analyze-partial API response.

This test uses REAL Gemini API calls (not mocked) to verify:
1. Token usage is calculated by Gemini service
2. Token usage is extracted from metadata
3. Token usage is returned in API response

Run with: pytest tests/integration/test_token_usage_response.py -v -s
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session as SessionModel


# Skip if no valid GCP credentials
def _check_gcp_credentials():
    """Check if valid GCP credentials are available"""
    try:
        from google.auth import default
        from google.auth.exceptions import DefaultCredentialsError, RefreshError

        try:
            credentials, project = default()
            from google.auth.transport.requests import Request

            credentials.refresh(Request())
            return True
        except (DefaultCredentialsError, RefreshError, Exception):
            return False
    except ImportError:
        return False


HAS_VALID_GCP_CREDENTIALS = _check_gcp_credentials()

pytestmark = pytest.mark.skipif(
    not HAS_VALID_GCP_CREDENTIALS,
    reason="Valid Google Cloud credentials not available (run: gcloud auth application-default login)",
)


class TestTokenUsageInResponse:
    """Test that token_usage field is present in API responses"""

    @pytest.fixture
    def career_counselor_and_session(self, db_session: Session):
        """Create counselor with session for testing"""
        from uuid import uuid4

        # Create counselor
        counselor = Counselor(
            id=uuid4(),
            email=f"token-test-{uuid4().hex[:8]}@test.com",
            username=f"tokentest{uuid4().hex[:6]}",
            full_name="Token Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
            available_credits=100.0,
        )
        db_session.add(counselor)

        # Create client
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            code=f"CLI-{uuid4().hex[:8]}",
            name="Test Client",
            email=f"client-{uuid4().hex[:8]}@test.com",
            gender="不透露",
            birth_date=datetime(1990, 1, 1).date(),
            phone="0912345678",
            identity_option="其他",
            current_status="active",
        )
        db_session.add(client)

        # Create case
        case = Case(
            id=uuid4(),
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            case_number=f"CASE-{uuid4().hex[:8]}",
            status=CaseStatus.IN_PROGRESS.value,
            goals="職涯探索",
        )
        db_session.add(case)

        # Create session
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="",
        )
        db_session.add(session)

        db_session.commit()

        return {
            "counselor": counselor,
            "session": session,
            "client": client,
            "case": case,
        }

    def test_token_usage_in_career_response(
        self, career_counselor_and_session, db_session
    ):
        """Test that token_usage appears in career tenant response"""
        counselor = career_counselor_and_session["counselor"]
        session = career_counselor_and_session["session"]

        # Login to get auth token
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": counselor.email,
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # Call analyze-partial endpoint
            response = client.post(
                f"/api/v1/sessions/{session.id}/analyze-partial",
                json={
                    "transcript_segment": "個案說：我最近對未來感到很焦慮，不知道該往哪個方向發展",
                    "mode": "practice",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()

            # Verify basic response structure
            assert "keywords" in data
            assert "categories" in data
            assert "confidence" in data
            assert "counselor_insights" in data

            # ✅ CRITICAL: Verify token_usage is present
            assert "token_usage" in data, "token_usage field is missing from response!"

            # Verify token_usage structure
            token_usage = data["token_usage"]
            assert token_usage is not None, "token_usage should not be None"
            assert isinstance(
                token_usage, dict
            ), f"token_usage should be dict, got {type(token_usage)}"

            # Verify required fields
            assert (
                "prompt_tokens" in token_usage
            ), "prompt_tokens missing from token_usage"
            assert (
                "completion_tokens" in token_usage
            ), "completion_tokens missing from token_usage"
            assert (
                "total_tokens" in token_usage
            ), "total_tokens missing from token_usage"

            # Verify values are positive integers
            assert (
                token_usage["prompt_tokens"] > 0
            ), f"prompt_tokens should be > 0, got {token_usage['prompt_tokens']}"
            assert (
                token_usage["completion_tokens"] > 0
            ), f"completion_tokens should be > 0, got {token_usage['completion_tokens']}"
            assert (
                token_usage["total_tokens"] > 0
            ), f"total_tokens should be > 0, got {token_usage['total_tokens']}"

            # Verify math: total >= prompt + completion
            # Note: Gemini's total_token_count may include additional tokens
            # (e.g., thoughts_token_count for reasoning, system instructions, etc.)
            min_expected_total = (
                token_usage["prompt_tokens"] + token_usage["completion_tokens"]
            )
            assert (
                token_usage["total_tokens"] >= min_expected_total
            ), f"total_tokens should be >= {min_expected_total}, got {token_usage['total_tokens']}"

            print("\n✅ Token usage verification PASSED:")
            print(f"   - prompt_tokens: {token_usage['prompt_tokens']}")
            print(f"   - completion_tokens: {token_usage['completion_tokens']}")
            print(f"   - total_tokens: {token_usage['total_tokens']}")

    def test_token_usage_in_island_parents_response(
        self, career_counselor_and_session, db_session
    ):
        """Test that token_usage appears in island_parents tenant response"""
        from uuid import uuid4

        # Create island_parents counselor
        counselor = Counselor(
            id=uuid4(),
            email=f"parent-token-test-{uuid4().hex[:8]}@test.com",
            username=f"parenttoken{uuid4().hex[:6]}",
            full_name="Parent Token Test",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
            available_credits=100.0,
        )
        db_session.add(counselor)

        # Create client for island_parents
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="island_parents",
            code=f"CLI-{uuid4().hex[:8]}",
            name="Parent Test",
            email=f"parent-{uuid4().hex[:8]}@test.com",
            gender="不透露",
            birth_date=datetime(1990, 1, 1).date(),
            phone="0912345678",
            identity_option="家長",
            current_status="active",
        )
        db_session.add(client)

        # Create case
        case = Case(
            id=uuid4(),
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="island_parents",
            case_number=f"CASE-{uuid4().hex[:8]}",
            status=CaseStatus.IN_PROGRESS.value,
            goals="親子溝通改善",
        )
        db_session.add(case)

        # Create session
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="island_parents",
            session_number=1,
            session_date=datetime.now(timezone.utc),
            transcript_text="",
        )
        db_session.add(session)
        db_session.commit()

        # Login and test
        with TestClient(app) as client_http:
            login_response = client_http.post(
                "/api/auth/login",
                json={
                    "email": counselor.email,
                    "password": "password123",
                    "tenant_id": "island_parents",
                },
            )
            assert login_response.status_code == 200
            token = login_response.json()["access_token"]

            # Call analyze-partial
            response = client_http.post(
                f"/api/v1/sessions/{session.id}/analyze-partial",
                json={
                    "transcript_segment": "家長：孩子最近都不想去學校，每天早上都哭",
                    "mode": "emergency",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()

            # Verify island_parents response structure
            assert "safety_level" in data
            assert "severity" in data
            assert "display_text" in data

            # ✅ CRITICAL: Verify token_usage
            assert "token_usage" in data, "token_usage missing from island_parents!"
            token_usage = data["token_usage"]
            assert token_usage is not None
            assert "prompt_tokens" in token_usage
            assert "completion_tokens" in token_usage
            assert "total_tokens" in token_usage

            print("\n✅ Island Parents token usage verification PASSED:")
            print(f"   - prompt_tokens: {token_usage['prompt_tokens']}")
            print(f"   - completion_tokens: {token_usage['completion_tokens']}")
            print(f"   - total_tokens: {token_usage['total_tokens']}")
