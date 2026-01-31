"""
Integration tests for usage limit enforcement in session creation.

TDD - Write tests FIRST, then integrate check_usage_limit into session creation.

Test Scenarios:
1. Subscription user at limit (360/360) → HTTP 429
2. Subscription user below limit (200/360) → HTTP 201 (success)
3. Prepaid user with credits → HTTP 201 (success)
4. Prepaid user without credits → HTTP 402
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import BillingMode, Counselor


class TestSessionCreationUsageLimit:
    """Test usage limit enforcement at session creation endpoint."""

    # Remove the shared auth_headers fixture since we need different counselor states per test

    def test_session_creation_blocked_at_limit(self, db_session: Session):
        """
        Test: Subscription user at limit (360/360) → HTTP 429

        Expected error response:
        {
            "code": "MONTHLY_USAGE_LIMIT_EXCEEDED",
            "message": "...",
            "monthly_limit": 360,
            "monthly_used": 360,
            "period_start": "..."
        }
        """
        from datetime import date

        # Create counselor at limit FROM THE START
        counselor = Counselor(
            id=uuid4(),
            email="at-limit@test.com",
            username="at_limit_user",
            full_name="At Limit User",
            hashed_password=hash_password("password123"),
            tenant_id="test_tenant",
            role="counselor",
            is_active=True,
            email_verified=True,
            billing_mode=BillingMode.SUBSCRIPTION,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            monthly_usage_limit_minutes=360,
            monthly_minutes_used=360,  # AT LIMIT
            usage_period_start=datetime.now(timezone.utc),
        )
        db_session.add(counselor)
        db_session.commit()

        # Create client and case
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="test_tenant",
            name="測試案主",
            code="CLI001",
            email="cli001@example.com",
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
            case_number="CASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="test_tenant",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)
        db_session.commit()

        # Login
        with TestClient(app) as test_client:
            login_response = test_client.post(
                "/api/auth/login",
                json={
                    "email": "at-limit@test.com",
                    "password": "password123",
                    "tenant_id": "test_tenant",
                },
            )
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Attempt to create session
            response = test_client.post(
                "/api/v1/sessions",
                headers=headers,
                json={
                    "case_id": str(case.id),
                    "session_date": datetime.now(timezone.utc).isoformat(),
                    "session_number": 1,
                },
            )

            # Verify blocked with 429
            assert response.status_code == 429, f"Expected 429, got {response.status_code}: {response.json()}"

            error_detail = response.json()
            assert error_detail["code"] == "MONTHLY_USAGE_LIMIT_EXCEEDED"
            assert error_detail["monthly_limit"] == 360
            assert error_detail["monthly_used"] == 360
            assert "period_start" in error_detail

    def test_session_creation_allowed_below_limit(self, db_session: Session):
        """
        Test: Subscription user below limit (200/360) → HTTP 201 (success)
        """
        from datetime import date

        # Create counselor below limit FROM THE START
        counselor = Counselor(
            id=uuid4(),
            email="below-limit@test.com",
            username="below_limit_user",
            full_name="Below Limit User",
            hashed_password=hash_password("password123"),
            tenant_id="test_tenant",
            role="counselor",
            is_active=True,
            email_verified=True,
            billing_mode=BillingMode.SUBSCRIPTION,
            subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            monthly_usage_limit_minutes=360,
            monthly_minutes_used=200,  # BELOW LIMIT
            usage_period_start=datetime.now(timezone.utc),
        )
        db_session.add(counselor)
        db_session.commit()

        # Create client and case
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="test_tenant",
            name="測試案主2",
            code="CLI002",
            email="cli002@example.com",
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
            case_number="CASE002",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="test_tenant",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)
        db_session.commit()

        # Login
        with TestClient(app) as test_client:
            login_response = test_client.post(
                "/api/auth/login",
                json={
                    "email": "below-limit@test.com",
                    "password": "password123",
                    "tenant_id": "test_tenant",
                },
            )
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create session
            response = test_client.post(
                "/api/v1/sessions",
                headers=headers,
                json={
                    "case_id": str(case.id),
                    "session_date": datetime.now(timezone.utc).isoformat(),
                    "session_number": 1,
                },
            )

            # Verify success
            assert response.status_code == 201
            data = response.json()
            assert data["case_id"] == str(case.id)
            assert data["session_number"] == 1

    def test_session_creation_prepaid_with_credits(self, db_session: Session):
        """
        Test: Prepaid user with credits → HTTP 201 (success)
        """
        from datetime import date

        # Create prepaid counselor with credits FROM THE START
        counselor = Counselor(
            id=uuid4(),
            email="prepaid-with@test.com",
            username="prepaid_with_user",
            full_name="Prepaid With User",
            hashed_password=hash_password("password123"),
            tenant_id="test_tenant",
            role="counselor",
            is_active=True,
            email_verified=True,
            billing_mode=BillingMode.PREPAID,
            available_credits=100.0,
        )
        db_session.add(counselor)
        db_session.commit()

        # Create client and case
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="test_tenant",
            name="測試案主3",
            code="CLI003",
            email="cli003@example.com",
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
            case_number="CASE003",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="test_tenant",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)
        db_session.commit()

        # Login
        with TestClient(app) as test_client:
            login_response = test_client.post(
                "/api/auth/login",
                json={
                    "email": "prepaid-with@test.com",
                    "password": "password123",
                    "tenant_id": "test_tenant",
                },
            )
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create session
            response = test_client.post(
                "/api/v1/sessions",
                headers=headers,
                json={
                    "case_id": str(case.id),
                    "session_date": datetime.now(timezone.utc).isoformat(),
                    "session_number": 1,
                },
            )

            # Verify success
            assert response.status_code == 201
            data = response.json()
            assert data["case_id"] == str(case.id)

    def test_session_creation_prepaid_no_credits(self, db_session: Session):
        """
        Test: Prepaid user without credits → HTTP 402
        """
        from datetime import date

        # Create prepaid counselor with NO credits FROM THE START
        counselor = Counselor(
            id=uuid4(),
            email="prepaid-no@test.com",
            username="prepaid_no_user",
            full_name="Prepaid No User",
            hashed_password=hash_password("password123"),
            tenant_id="test_tenant",
            role="counselor",
            is_active=True,
            email_verified=True,
            billing_mode=BillingMode.PREPAID,
            available_credits=0.0,
        )
        db_session.add(counselor)
        db_session.commit()

        # Create client and case
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="test_tenant",
            name="測試案主4",
            code="CLI004",
            email="cli004@example.com",
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
            case_number="CASE004",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="test_tenant",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)
        db_session.commit()

        # Login
        with TestClient(app) as test_client:
            login_response = test_client.post(
                "/api/auth/login",
                json={
                    "email": "prepaid-no@test.com",
                    "password": "password123",
                    "tenant_id": "test_tenant",
                },
            )
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Attempt to create session
            response = test_client.post(
                "/api/v1/sessions",
                headers=headers,
                json={
                    "case_id": str(case.id),
                    "session_date": datetime.now(timezone.utc).isoformat(),
                    "session_number": 1,
                },
            )

            # Verify blocked with 402
            assert response.status_code == 402, f"Got {response.status_code}: {response.json()}"

            error_detail = response.json()
            assert error_detail["code"] == "INSUFFICIENT_CREDITS"
            assert error_detail["available_credits"] == 0.0
