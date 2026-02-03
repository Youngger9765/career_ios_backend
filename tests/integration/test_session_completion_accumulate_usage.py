"""
Integration tests for session completion accumulating usage time to monthly_minutes_used

TDD - Write tests FIRST, then implement.

Test Scenario:
When a SessionUsage record status changes to "completed", the duration_seconds
should be accumulated to counselor.monthly_minutes_used (for subscription mode only).

Goal Behavior:
1. SessionUsage status changes from "in_progress" to "completed"
2. System calculates minutes from duration_seconds (ceil rounding)
3. For subscription counselors: Add minutes to monthly_minutes_used
4. For prepaid counselors: No accumulation (they use credits instead)
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import BillingMode, Counselor
from app.models.session import Session as SessionModel


class TestSessionCompletionAccumulateUsage:
    """Test session completion accumulates usage time for subscription counselors"""

    @pytest.fixture
    def subscription_counselor(self, db_session: Session):
        """Create subscription counselor with initial usage"""
        counselor = Counselor(
            id=uuid4(),
            email="sub-counselor@test.com",
            username="sub_counselor",
            full_name="Subscription Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
            email_verified=True,
            billing_mode=BillingMode.SUBSCRIPTION,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            monthly_usage_limit_minutes=360,
            monthly_minutes_used=100,  # Already used 100 minutes
            usage_period_start=datetime.now(timezone.utc),
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "sub-counselor@test.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return counselor, {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def prepaid_counselor(self, db_session: Session):
        """Create prepaid counselor with credits"""
        counselor = Counselor(
            id=uuid4(),
            email="prepaid-counselor@test.com",
            username="prepaid_counselor",
            full_name="Prepaid Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
            email_verified=True,
            billing_mode=BillingMode.PREPAID,
            available_credits=1000.0,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "prepaid-counselor@test.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return counselor, {"Authorization": f"Bearer {token}"}

    def _create_test_session(self, db_session: Session, counselor: Counselor):
        """Helper to create client, case, and session"""
        from datetime import date

        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="測試案主",
            code=f"CLI{uuid4().hex[:6]}",
            email=f"client{uuid4().hex[:6]}@example.com",
            gender="不透露",
            birth_date=date(1995, 1, 1),
            phone="0912345678",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(client)
        db_session.commit()

        case = Case(
            id=uuid4(),
            case_number=f"CASE{uuid4().hex[:6]}",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)
        db_session.commit()

        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now(timezone.utc),
        )
        db_session.add(session)
        db_session.commit()

        return session

    def test_subscription_session_completion_accumulates_30_minutes(
        self, db_session: Session, subscription_counselor
    ):
        """
        Test: Subscription counselor completes session with 1800 seconds (30 min)
        Expected: monthly_minutes_used increases from 100 to 130
        """
        counselor, headers = subscription_counselor
        session = self._create_test_session(db_session, counselor)

        # Verify initial state
        assert counselor.monthly_minutes_used == 100

        with TestClient(app) as client:
            # Create usage record
            start_time = datetime.now(timezone.utc)
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "in_progress",
                    "start_time": start_time.isoformat(),
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )
            assert response.status_code == 201
            usage_id = response.json()["id"]

            # Complete the session (30 minutes = 1800 seconds)
            end_time = start_time + timedelta(seconds=1800)
            response = client.patch(
                f"/api/v1/sessions/{session.id}/usage/{usage_id}",
                headers=headers,
                json={
                    "status": "completed",
                    "end_time": end_time.isoformat(),
                },
            )

            assert response.status_code == 200

            # Verify counselor's monthly_minutes_used was updated
            db_session.refresh(counselor)
            assert counselor.monthly_minutes_used == 130, (
                f"Expected 130 (100 + 30), got {counselor.monthly_minutes_used}"
            )

    def test_subscription_session_completion_accumulates_with_ceiling(
        self, db_session: Session, subscription_counselor
    ):
        """
        Test: Session with 90 seconds (1.5 minutes) should accumulate as 2 minutes (ceiling)
        Expected: monthly_minutes_used increases from 100 to 102
        """
        counselor, headers = subscription_counselor
        session = self._create_test_session(db_session, counselor)

        with TestClient(app) as client:
            # Create and complete usage (90 seconds)
            start_time = datetime.now(timezone.utc)
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "completed",
                    "start_time": start_time.isoformat(),
                    "end_time": (start_time + timedelta(seconds=90)).isoformat(),
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )

            assert response.status_code == 201

            # Verify ceiling: 90s = 1.5min → ceil(1.5) = 2 minutes
            db_session.refresh(counselor)
            assert counselor.monthly_minutes_used == 102, (
                f"Expected 102 (100 + ceil(1.5)=2), got {counselor.monthly_minutes_used}"
            )

    def test_prepaid_session_completion_does_not_accumulate(
        self, db_session: Session, prepaid_counselor
    ):
        """
        Test: Prepaid counselor completes session
        Expected: monthly_minutes_used should NOT change (remain 0 or None)
        Prepaid uses credit deduction instead
        """
        counselor, headers = prepaid_counselor
        session = self._create_test_session(db_session, counselor)

        # Verify initial state (prepaid should have 0 or None)
        initial_usage = counselor.monthly_minutes_used or 0

        with TestClient(app) as client:
            # Create and complete usage
            start_time = datetime.now(timezone.utc)
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "completed",
                    "start_time": start_time.isoformat(),
                    "end_time": (start_time + timedelta(seconds=1800)).isoformat(),
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )

            assert response.status_code == 201

            # Verify monthly_minutes_used did NOT change
            db_session.refresh(counselor)
            assert counselor.monthly_minutes_used == initial_usage, (
                f"Prepaid counselor should not accumulate monthly_minutes_used, "
                f"expected {initial_usage}, got {counselor.monthly_minutes_used}"
            )

    def test_multiple_sessions_accumulate_correctly(
        self, db_session: Session, subscription_counselor
    ):
        """
        Test: Multiple sessions accumulate correctly
        Session 1: 30 min (100 → 130)
        Session 2: 45 min (130 → 175)
        Session 3: 10 min (175 → 185)
        """
        counselor, headers = subscription_counselor

        expected_usage = 100  # Starting value

        for minutes in [30, 45, 10]:
            session = self._create_test_session(db_session, counselor)

            with TestClient(app) as client:
                start_time = datetime.now(timezone.utc)
                response = client.post(
                    f"/api/v1/sessions/{session.id}/usage",
                    headers=headers,
                    json={
                        "usage_type": "voice_call",
                        "status": "completed",
                        "start_time": start_time.isoformat(),
                        "end_time": (start_time + timedelta(minutes=minutes)).isoformat(),
                        "pricing_rule": {"unit": "minute", "rate": 1.0},
                    },
                )
                assert response.status_code == 201

                expected_usage += minutes
                db_session.refresh(counselor)
                assert counselor.monthly_minutes_used == expected_usage, (
                    f"After {minutes}min session, expected {expected_usage}, "
                    f"got {counselor.monthly_minutes_used}"
                )

    def test_in_progress_session_does_not_accumulate(
        self, db_session: Session, subscription_counselor
    ):
        """
        Test: Creating session with status "in_progress" should NOT accumulate
        Only "completed" status triggers accumulation
        """
        counselor, headers = subscription_counselor
        session = self._create_test_session(db_session, counselor)

        initial_usage = counselor.monthly_minutes_used

        with TestClient(app) as client:
            # Create usage with in_progress status
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "in_progress",
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )

            assert response.status_code == 201

            # Verify no accumulation happened
            db_session.refresh(counselor)
            assert counselor.monthly_minutes_used == initial_usage, (
                f"in_progress status should not accumulate, "
                f"expected {initial_usage}, got {counselor.monthly_minutes_used}"
            )

    def test_duplicate_completion_should_not_accumulate(
        self, db_session: Session, subscription_counselor
    ):
        """
        Test: Updating a completed session to completed again should NOT accumulate twice
        CRITICAL: Prevents duplicate accumulation bug
        Expected: monthly_minutes_used only increases once
        """
        counselor, headers = subscription_counselor
        session = self._create_test_session(db_session, counselor)

        # Verify initial state
        assert counselor.monthly_minutes_used == 100

        with TestClient(app) as client:
            # Create usage record
            start_time = datetime.now(timezone.utc)
            response = client.post(
                f"/api/v1/sessions/{session.id}/usage",
                headers=headers,
                json={
                    "usage_type": "voice_call",
                    "status": "in_progress",
                    "start_time": start_time.isoformat(),
                    "pricing_rule": {"unit": "minute", "rate": 1.0},
                },
            )
            assert response.status_code == 201
            usage_id = response.json()["id"]

            # Update to completed (first time - should accumulate)
            end_time = start_time + timedelta(seconds=1800)  # 30 minutes
            response = client.patch(
                f"/api/v1/sessions/{session.id}/usage/{usage_id}",
                headers=headers,
                json={
                    "status": "completed",
                    "end_time": end_time.isoformat(),
                },
            )
            assert response.status_code == 200

            # Verify: Usage should be 130 (100 + 30)
            db_session.refresh(counselor)
            assert counselor.monthly_minutes_used == 130

            # Update to completed AGAIN (should NOT accumulate again)
            response = client.patch(
                f"/api/v1/sessions/{session.id}/usage/{usage_id}",
                headers=headers,
                json={
                    "status": "completed",
                },
            )
            assert response.status_code == 200

            # Verify: Usage should STILL be 130 (not 160)
            db_session.refresh(counselor)
            assert counselor.monthly_minutes_used == 130, (
                f"Duplicate completion should not accumulate, "
                f"expected 130, got {counselor.monthly_minutes_used}"
            )
