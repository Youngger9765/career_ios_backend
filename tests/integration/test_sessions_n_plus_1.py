"""
Integration tests for N+1 query fixes in Sessions API
TDD - Write tests first to verify no N+1 queries
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.report import Report, ReportStatus
from app.models.session import Session as SessionModel


class QueryCounter:
    """Helper to count SQL queries executed"""

    def __init__(self):
        self.count = 0
        self.queries = []

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1
        self.queries.append(statement)


class TestSessionsNPlusOneQueries:
    """Test that Sessions API endpoints don't have N+1 query problems"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-n1@test.com",
            username="n1counselor",
            full_name="N+1 Test Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "counselor-n1@test.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_sessions_with_reports(self, db_session: Session, auth_headers):
        """Create multiple sessions, some with reports, some without"""
        from datetime import date

        counselor = (
            db_session.query(Counselor).filter_by(email="counselor-n1@test.com").first()
        )

        # Create client
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="N+1 測試客戶",
            code="N1CLI001",
            email="n1cli001@example.com",
            gender="不透露",
            birth_date=date(1995, 1, 1),
            phone="0912345678",
            identity_option="其他",
            current_status="探索中",
        )
        db_session.add(client)
        db_session.commit()

        # Create case
        case = Case(
            id=uuid4(),
            case_number="N1CASE001",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.NOT_STARTED,
        )
        db_session.add(case)
        db_session.commit()

        # Create 10 sessions (mix with/without reports)
        sessions = []
        for i in range(10):
            session = SessionModel(
                id=uuid4(),
                case_id=case.id,
                tenant_id="career",
                session_number=i + 1,
                session_date=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
                transcript_text=f"Test transcript {i+1}",
                source_type="transcript",
            )
            db_session.add(session)
            sessions.append(session)

        db_session.commit()

        # Add reports to half of the sessions
        for i in range(0, 10, 2):  # Sessions 0, 2, 4, 6, 8 have reports
            report = Report(
                id=uuid4(),
                session_id=sessions[i].id,
                client_id=client.id,
                created_by_id=counselor.id,
                tenant_id="career",
                version=1,
                status=ReportStatus.DRAFT,
                mode="enhanced",
                ai_model="gpt-4o-mini",
                content_json={"sections": []},
                content_markdown="# Test Report",
            )
            db_session.add(report)

        db_session.commit()

        return {"client": client, "case": case, "sessions": sessions}

    def test_list_sessions_no_n_plus_1(
        self, db_session: Session, auth_headers, test_sessions_with_reports
    ):
        """
        Test GET /api/v1/sessions - Should not have N+1 queries

        Expected: Should use JOIN to fetch report counts in single query
        Not Expected: Separate query for each session's report count
        """
        # Setup query counter
        counter = QueryCounter()
        event.listen(Engine, "before_cursor_execute", counter)

        try:
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/sessions",
                    headers=auth_headers,
                    params={"limit": 20},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 10
            assert len(data["items"]) == 10

            # Verify has_report field is correct
            for item in data["items"]:
                assert "has_report" in item
                # Sessions 1, 3, 5, 7, 9 (odd session_numbers) should have reports
                expected_has_report = (item["session_number"] % 2) == 1
                assert item["has_report"] == expected_has_report

            # Count queries - should be much less than 10 (number of sessions)
            # Expected queries:
            # 1. Main SELECT with JOINs (Session + Client + Case)
            # 2. LEFT JOIN or subquery for Report counts
            # Total should be around 2-4 queries, definitely not 10+
            print(f"\n[DEBUG] Total queries executed: {counter.count}")
            print(f"[DEBUG] Queries: {counter.queries}")

            # STRICT: Should not exceed 5 queries for 10 sessions
            # If this fails, we have N+1 problem
            assert counter.count <= 5, (
                f"N+1 query detected! Expected <= 5 queries, got {counter.count}. "
                f"This means we're querying reports individually for each session."
            )

        finally:
            event.remove(Engine, "before_cursor_execute", counter)

    def test_get_session_no_n_plus_1(
        self, db_session: Session, auth_headers, test_sessions_with_reports
    ):
        """
        Test GET /api/v1/sessions/{session_id} - Should not have N+1 queries

        Expected: Should use JOIN or exists() to check report in single query
        Not Expected: Separate query to count reports
        """
        sessions = test_sessions_with_reports["sessions"]
        session_id = str(sessions[0].id)  # This session has a report

        # Setup query counter
        counter = QueryCounter()
        event.listen(Engine, "before_cursor_execute", counter)

        try:
            with TestClient(app) as client:
                response = client.get(
                    f"/api/v1/sessions/{session_id}",
                    headers=auth_headers,
                )

            assert response.status_code == 200
            data = response.json()
            assert data["has_report"] is True

            # Count queries - should be minimal
            # Expected queries:
            # 1. Main SELECT with JOINs (Session + Client + Case)
            # 2. Check for reports (should be in same query or efficient subquery)
            print(f"\n[DEBUG] Total queries executed: {counter.count}")
            print(f"[DEBUG] Queries: {counter.queries}")

            # STRICT: Should not exceed 3 queries
            assert counter.count <= 3, (
                f"N+1 query detected! Expected <= 3 queries, got {counter.count}. "
                f"This means we're querying reports separately."
            )

        finally:
            event.remove(Engine, "before_cursor_execute", counter)

    def test_get_session_timeline_no_n_plus_1(
        self, db_session: Session, auth_headers, test_sessions_with_reports
    ):
        """
        Test GET /api/v1/sessions/timeline - Should not have N+1 queries

        This endpoint already uses proper JOIN - verify it stays efficient
        """
        client_id = str(test_sessions_with_reports["client"].id)

        # Setup query counter
        counter = QueryCounter()
        event.listen(Engine, "before_cursor_execute", counter)

        try:
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/sessions/timeline",
                    headers=auth_headers,
                    params={"client_id": client_id},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["total_sessions"] == 10

            # Count queries - should be minimal
            print(f"\n[DEBUG] Total queries executed: {counter.count}")
            print(f"[DEBUG] Queries: {counter.queries}")

            # STRICT: Should not exceed 3 queries (client check + sessions with reports)
            assert (
                counter.count <= 3
            ), f"N+1 query detected! Expected <= 3 queries, got {counter.count}."

        finally:
            event.remove(Engine, "before_cursor_execute", counter)
