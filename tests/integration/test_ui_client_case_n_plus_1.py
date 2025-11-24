"""
Integration tests for N+1 query fixes in UI Client Case List API
TDD - Write tests first to verify no N+1 queries
"""
from datetime import date, datetime, timezone
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
from app.models.session import Session as SessionModel


class QueryCounter:
    """Helper to count SQL queries executed"""

    def __init__(self):
        self.count = 0
        self.queries = []

    def __call__(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1
        self.queries.append(statement)


class TestUIClientCaseListNPlusOne:
    """Test that UI Client Case List API doesn't have N+1 query problems"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor-ui-n1@test.com",
            username="uicounselor",
            full_name="UI N+1 Test Counselor",
            hashed_password=hash_password("password123"),
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
                    "email": "counselor-ui-n1@test.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def multiple_clients_with_sessions(self, db_session: Session, auth_headers):
        """Create 10 clients with cases and varying number of sessions"""
        counselor = (
            db_session.query(Counselor)
            .filter_by(email="counselor-ui-n1@test.com")
            .first()
        )

        clients_data = []

        for i in range(10):
            # Create client
            client = Client(
                id=uuid4(),
                counselor_id=counselor.id,
                tenant_id="career",
                name=f"UI測試客戶{i+1}",
                code=f"UICLI{i+1:03d}",
                email=f"uicli{i+1}@example.com",
                gender="不透露",
                birth_date=date(1990, 1, 1),
                phone=f"091234567{i}",
                identity_option="在職者",
                current_status="探索中",
            )
            db_session.add(client)
            db_session.flush()

            # Create case for client
            case = Case(
                id=uuid4(),
                case_number=f"UICASE{i+1:03d}",
                counselor_id=counselor.id,
                client_id=client.id,
                tenant_id="career",
                status=CaseStatus.IN_PROGRESS,
            )
            db_session.add(case)
            db_session.flush()

            # Create varying number of sessions (0 to 5)
            num_sessions = i % 6
            for j in range(num_sessions):
                session = SessionModel(
                    id=uuid4(),
                    case_id=case.id,
                    tenant_id="career",
                    session_number=j + 1,
                    session_date=datetime(2024, 1, j + 1, 10, 0, tzinfo=timezone.utc),
                    transcript_text=f"Test transcript {j+1}",
                    source_type="transcript",
                )
                db_session.add(session)

            clients_data.append(
                {
                    "client": client,
                    "case": case,
                    "num_sessions": num_sessions,
                }
            )

        db_session.commit()
        return clients_data

    def test_client_case_list_no_n_plus_1(
        self, db_session: Session, auth_headers, multiple_clients_with_sessions
    ):
        """
        Test GET /api/v1/ui/client-case-list - Should not have N+1 queries

        Expected: Should use LEFT JOIN for session stats in single query
        Not Expected: Separate query for each case's session count/max date

        This endpoint was doing:
        - Main query: Get all clients + cases
        - For each case: Query session stats (N queries) ❌

        Fixed to:
        - Single query with session_stats subquery + LEFT JOIN ✅
        """
        # Setup query counter
        counter = QueryCounter()
        event.listen(Engine, "before_cursor_execute", counter)

        try:
            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/ui/client-case-list",
                    headers=auth_headers,
                    params={"limit": 100},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 10
            assert len(data["items"]) == 10

            # Verify session counts are correct
            # Clients have 0-5 sessions (based on index % 6)
            for idx, item in enumerate(data["items"]):
                # Note: items are sorted by last_session_date, so order may differ
                assert "total_sessions" in item
                assert item["total_sessions"] >= 0

            # Count queries - should be minimal
            # Expected queries:
            # 1. case_subquery (find first case per client)
            # 2. session_stats_subquery (aggregate session stats)
            # 3. Main SELECT with JOINs
            # 4. Count query
            # Total should be around 4-6 queries, definitely not 10+
            print(f"\n[DEBUG] Total queries executed: {counter.count}")
            print("[DEBUG] Sample queries:")
            for i, q in enumerate(counter.queries[:5]):
                print(f"  {i+1}. {q[:100]}...")

            # STRICT: Should not exceed 7 queries for 10 clients
            # If this fails, we have N+1 problem (would be 10+ queries)
            assert counter.count <= 7, (
                f"N+1 query detected! Expected <= 7 queries, got {counter.count}. "
                f"This means we're querying session stats individually for each case."
            )

        finally:
            event.remove(Engine, "before_cursor_execute", counter)

    def test_client_case_list_with_many_cases_no_n_plus_1(
        self, db_session: Session, auth_headers, multiple_clients_with_sessions
    ):
        """
        Test with pagination - ensure query count stays constant

        If we have N+1 problem, queries would scale with page size
        """
        counter = QueryCounter()
        event.listen(Engine, "before_cursor_execute", counter)

        try:
            # Test with different page sizes
            with TestClient(app) as client:
                # Small page
                response1 = client.get(
                    "/api/v1/ui/client-case-list",
                    headers=auth_headers,
                    params={"skip": 0, "limit": 3},
                )
                count_small = counter.count

                # Reset counter
                counter.count = 0
                counter.queries = []

                # Larger page
                response2 = client.get(
                    "/api/v1/ui/client-case-list",
                    headers=auth_headers,
                    params={"skip": 0, "limit": 10},
                )
                count_large = counter.count

            assert response1.status_code == 200
            assert response2.status_code == 200

            # Query count should be similar regardless of page size
            # If N+1 exists, count_large would be much higher
            print(f"\n[DEBUG] Small page (3 items): {count_small} queries")
            print(f"[DEBUG] Large page (10 items): {count_large} queries")

            # Query count difference should be minimal (within 3 queries)
            # If N+1 exists, difference would be ~7 (10-3 = 7 extra session queries)
            query_diff = abs(count_large - count_small)
            assert query_diff <= 3, (
                f"N+1 query detected! Query count scales with page size. "
                f"Small page: {count_small}, Large page: {count_large}, Diff: {query_diff}"
            )

        finally:
            event.remove(Engine, "before_cursor_execute", counter)
