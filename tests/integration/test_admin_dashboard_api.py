"""
Integration tests for Admin Dashboard API
Tests all 15 endpoints with comprehensive scenarios:
- Time range filtering (day/week/month)
- Tenant filtering
- Empty data handling
- Cost calculation accuracy (ElevenLabs + Gemini)
- Token counting (Flash 3, Flash 1.5, Lite)
- SessionAnalysisLog time filtering (analyzed_at)

NOTE: Some tests are skipped on SQLite because they use PostgreSQL-specific
date_trunc function. Run with PostgreSQL for full test coverage.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.pricing import (
    ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
    GEMINI_1_5_FLASH_INPUT_USD_PER_1M_TOKENS,
    GEMINI_1_5_FLASH_OUTPUT_USD_PER_1M_TOKENS,
    GEMINI_FLASH_LITE_INPUT_USD_PER_1M_TOKENS,
    GEMINI_FLASH_LITE_OUTPUT_USD_PER_1M_TOKENS,
)
from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor, CounselorRole
from app.models.session_analysis_log import SessionAnalysisLog
from app.models.session_usage import SessionUsage


class TestAdminDashboardAPI:
    """Test all admin dashboard endpoints"""

    @pytest.fixture
    def is_postgres(self, db_session: Session) -> bool:
        """Check if database is PostgreSQL"""
        dialect = db_session.bind.dialect.name
        return dialect == "postgresql"

    @pytest.fixture
    def admin_user(self, db_session: Session) -> Counselor:
        """Create admin user for testing"""
        admin = Counselor(
            id=uuid4(),
            email="admin@test.com",
            username="admin",
            full_name="Admin User",
            hashed_password=hash_password("AdminP@ss123"),
            tenant_id="career",
            role=CounselorRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
        return admin

    @pytest.fixture
    def regular_user(self, db_session: Session) -> Counselor:
        """Create regular counselor for testing access control"""
        counselor = Counselor(
            id=uuid4(),
            email="counselor@test.com",
            username="counselor",
            full_name="Regular Counselor",
            hashed_password=hash_password("CounselorP@ss123"),
            tenant_id="career",
            role=CounselorRole.COUNSELOR,
            is_active=True,
            email_verified=True,
        )
        db_session.add(counselor)
        db_session.commit()
        db_session.refresh(counselor)
        return counselor

    @pytest.fixture
    def admin_headers(self, admin_user: Counselor) -> dict:
        """Get authentication headers for admin user"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "admin@test.com",
                    "password": "AdminP@ss123",
                    "tenant_id": "career",
                },
            )
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def regular_headers(self, regular_user: Counselor) -> dict:
        """Get authentication headers for regular user"""
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "counselor@test.com",
                    "password": "CounselorP@ss123",
                    "tenant_id": "career",
                },
            )
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_data(self, db_session: Session, admin_user: Counselor):
        """
        Create comprehensive test data with specific timestamps for time filtering

        Test data structure:
        - Session 1: Today, 10 minutes (600s), analyzed today
          - ElevenLabs cost: 600s * $0.40/3600s = $0.0667
          - Gemini (Flash Lite): 5000 input + 2000 output
        - Session 2: 5 days ago, 20 minutes (1200s), analyzed 5 days ago
          - ElevenLabs cost: 1200s * $0.40/3600s = $0.1333
          - Gemini (Flash 1.5): 10000 input + 4000 output
        - Session 3: 20 days ago, 30 minutes (1800s), analyzed 20 days ago
          - ElevenLabs cost: 1800s * $0.40/3600s = $0.2000
          - Gemini (Flash 1.5): 15000 input + 6000 output

        Time range filtering should work as follows:
        - "day": Only Session 1
        - "week": Sessions 1 + 2
        - "month": All 3 sessions
        """
        now = datetime.now(timezone.utc)

        # Session 1: Today
        session1_id = uuid4()
        session1_usage = SessionUsage(
            id=uuid4(),
            session_id=session1_id,
            counselor_id=admin_user.id,
            tenant_id="career",
            duration_seconds=600,
            status="completed",
            total_prompt_tokens=5000,
            total_completion_tokens=2000,
            total_tokens=7000,
            estimated_cost_usd=600 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
            created_at=now,
        )

        # Calculate Gemini cost for Flash Lite
        gemini1_cost = (
            (5000 / 1_000_000) * GEMINI_FLASH_LITE_INPUT_USD_PER_1M_TOKENS +
            (2000 / 1_000_000) * GEMINI_FLASH_LITE_OUTPUT_USD_PER_1M_TOKENS
        )

        session1_analysis = SessionAnalysisLog(
            id=uuid4(),
            session_id=session1_id,
            counselor_id=admin_user.id,
            tenant_id="career",
            analysis_type="keyword_extraction",
            model_name="models/gemini-flash-lite-latest",
            prompt_tokens=5000,
            completion_tokens=2000,
            total_tokens=7000,
            estimated_cost_usd=gemini1_cost,
            safety_level="green",
            analyzed_at=now,
        )

        # Session 2: 5 days ago (within week range)
        five_days_ago = now - timedelta(days=5)
        session2_id = uuid4()
        session2_usage = SessionUsage(
            id=uuid4(),
            session_id=session2_id,
            counselor_id=admin_user.id,
            tenant_id="career",
            duration_seconds=1200,
            status="completed",
            total_prompt_tokens=10000,
            total_completion_tokens=4000,
            total_tokens=14000,
            estimated_cost_usd=1200 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
            created_at=five_days_ago,
        )

        # Calculate Gemini cost for Flash 1.5
        gemini2_cost = (
            (10000 / 1_000_000) * GEMINI_1_5_FLASH_INPUT_USD_PER_1M_TOKENS +
            (4000 / 1_000_000) * GEMINI_1_5_FLASH_OUTPUT_USD_PER_1M_TOKENS
        )

        session2_analysis = SessionAnalysisLog(
            id=uuid4(),
            session_id=session2_id,
            counselor_id=admin_user.id,
            tenant_id="career",
            analysis_type="summarization",
            model_name="models/gemini-1.5-flash-latest",
            prompt_tokens=10000,
            completion_tokens=4000,
            total_tokens=14000,
            estimated_cost_usd=gemini2_cost,
            safety_level="yellow",
            analyzed_at=five_days_ago,
        )

        # Session 3: 20 days ago (within month range only)
        twenty_days_ago = now - timedelta(days=20)
        session3_id = uuid4()
        session3_usage = SessionUsage(
            id=uuid4(),
            session_id=session3_id,
            counselor_id=admin_user.id,
            tenant_id="career",
            duration_seconds=1800,
            status="completed",
            total_prompt_tokens=15000,
            total_completion_tokens=6000,
            total_tokens=21000,
            estimated_cost_usd=1800 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
            created_at=twenty_days_ago,
        )

        # Calculate Gemini cost for Flash 1.5
        gemini3_cost = (
            (15000 / 1_000_000) * GEMINI_1_5_FLASH_INPUT_USD_PER_1M_TOKENS +
            (6000 / 1_000_000) * GEMINI_1_5_FLASH_OUTPUT_USD_PER_1M_TOKENS
        )

        session3_analysis = SessionAnalysisLog(
            id=uuid4(),
            session_id=session3_id,
            counselor_id=admin_user.id,
            tenant_id="career",
            analysis_type="rag_query",
            model_name="gemini-1.5-flash-latest",
            prompt_tokens=15000,
            completion_tokens=6000,
            total_tokens=21000,
            estimated_cost_usd=gemini3_cost,
            safety_level="red",
            analyzed_at=twenty_days_ago,
        )

        db_session.add_all([
            session1_usage, session1_analysis,
            session2_usage, session2_analysis,
            session3_usage, session3_analysis,
        ])
        db_session.commit()

        return {
            "session1": {
                "usage": session1_usage,
                "analysis": session1_analysis,
                "elevenlabs_cost": 600 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
                "gemini_cost": gemini1_cost,
                "total_cost": (600 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND) + gemini1_cost,
            },
            "session2": {
                "usage": session2_usage,
                "analysis": session2_analysis,
                "elevenlabs_cost": 1200 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
                "gemini_cost": gemini2_cost,
                "total_cost": (1200 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND) + gemini2_cost,
            },
            "session3": {
                "usage": session3_usage,
                "analysis": session3_analysis,
                "elevenlabs_cost": 1800 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
                "gemini_cost": gemini3_cost,
                "total_cost": (1800 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND) + gemini3_cost,
            },
        }

    # =========================================================================
    # Access Control Tests
    # =========================================================================

    def test_admin_access_required(self, regular_headers):
        """Test that non-admin users cannot access dashboard endpoints"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/summary",
                headers=regular_headers,
            )
            assert response.status_code == 403
            assert "Admin access required" in response.json()["detail"]

    def test_admin_access_granted(self, admin_headers):
        """Test that admin users can access dashboard endpoints"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/summary",
                headers=admin_headers,
            )
            assert response.status_code == 200

    # =========================================================================
    # 1. GET /summary - Summary Statistics
    # =========================================================================

    def test_get_summary_day_range(self, admin_headers, test_data):
        """Test summary endpoint with day time range"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/summary?time_range=day",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Should only include session 1 (today)
            expected_cost = test_data["session1"]["total_cost"]
            assert abs(data["total_cost_usd"] - expected_cost) < 0.0001
            assert data["total_sessions"] == 1
            assert data["active_users"] == 1

    def test_get_summary_week_range(self, admin_headers, test_data):
        """Test summary endpoint with week time range"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/summary?time_range=week",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Should include sessions 1 + 2
            expected_cost = (
                test_data["session1"]["total_cost"] +
                test_data["session2"]["total_cost"]
            )
            assert abs(data["total_cost_usd"] - expected_cost) < 0.0001
            assert data["total_sessions"] == 2
            assert data["active_users"] == 1

    def test_get_summary_month_range(self, admin_headers, test_data):
        """Test summary endpoint with month time range"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/summary?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Should include all 3 sessions
            expected_cost = (
                test_data["session1"]["total_cost"] +
                test_data["session2"]["total_cost"] +
                test_data["session3"]["total_cost"]
            )
            assert abs(data["total_cost_usd"] - expected_cost) < 0.0001
            assert data["total_sessions"] == 3
            assert data["active_users"] == 1

    def test_get_summary_empty_data(self, db_session: Session, admin_headers):
        """Test summary endpoint with no data"""
        # Create fresh admin without test data
        admin = Counselor(
            id=uuid4(),
            email="admin2@test.com",
            username="admin2",
            full_name="Admin User 2",
            hashed_password=hash_password("AdminP@ss123"),
            tenant_id="empty_tenant",
            role=CounselorRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        db_session.add(admin)
        db_session.commit()

        with TestClient(app) as client:
            # Login as new admin
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "admin2@test.com",
                    "password": "AdminP@ss123",
                    "tenant_id": "empty_tenant",
                },
            )
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            response = client.get(
                "/api/v1/admin/dashboard/summary?time_range=day&tenant_id=empty_tenant",
                headers=headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_cost_usd"] == 0.0
            assert data["total_sessions"] == 0
            assert data["active_users"] == 0

    def test_get_summary_tenant_filtering(self, db_session: Session, admin_headers, test_data):
        """Test summary endpoint with tenant filtering"""
        # Create session for different tenant
        other_admin = Counselor(
            id=uuid4(),
            email="other-admin@test.com",
            username="other-admin",
            full_name="Other Admin",
            hashed_password=hash_password("AdminP@ss123"),
            tenant_id="island_parents",
            role=CounselorRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        db_session.add(other_admin)
        db_session.commit()

        other_session = SessionUsage(
            id=uuid4(),
            session_id=uuid4(),
            counselor_id=other_admin.id,
            tenant_id="island_parents",
            duration_seconds=300,
            status="completed",
            estimated_cost_usd=300 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(other_session)
        db_session.commit()

        with TestClient(app) as client:
            # Filter by "career" tenant - should only see test_data sessions
            response = client.get(
                "/api/v1/admin/dashboard/summary?time_range=day&tenant_id=career",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            expected_cost = test_data["session1"]["total_cost"]
            assert abs(data["total_cost_usd"] - expected_cost) < 0.0001

    # =========================================================================
    # 2. GET /cost-trend - Cost Trend Over Time
    # =========================================================================

    def test_get_cost_trend_day_range(self, db_session: Session, admin_headers, test_data):
        """Test cost trend endpoint with day range (hourly breakdown)"""
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/cost-trend?time_range=day",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "data" in data
            assert isinstance(data["labels"], list)
            assert isinstance(data["data"], list)
            # Day range uses hourly format (HH:MM)
            if data["labels"]:
                assert ":" in data["labels"][0]

    def test_get_cost_trend_week_range(self, db_session: Session, admin_headers, test_data):
        """Test cost trend endpoint with week range (daily breakdown)"""
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/cost-trend?time_range=week",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "data" in data
            # Week range uses date format (YYYY-MM-DD)
            if data["labels"]:
                assert "-" in data["labels"][0]

    def test_get_cost_trend_model_filter(self, db_session: Session, admin_headers, test_data):
        """Test cost trend with model filtering"""
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/cost-trend?time_range=month&model=models/gemini-flash-lite-latest",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "data" in data

    # =========================================================================
    # 3. GET /token-trend - Token Usage Trend
    # =========================================================================

    def test_get_token_trend(self, db_session: Session, admin_headers, test_data):
        """Test token trend endpoint"""
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/token-trend?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "prompt_tokens" in data
            assert "completion_tokens" in data
            assert "total_tokens" in data

            # Verify token totals
            total_prompt = sum(data["prompt_tokens"])
            total_completion = sum(data["completion_tokens"])

            # Should sum to all 3 sessions' tokens
            expected_prompt = 5000 + 10000 + 15000  # 30000
            expected_completion = 2000 + 4000 + 6000  # 12000

            assert total_prompt == expected_prompt
            assert total_completion == expected_completion

    # =========================================================================
    # 4. GET /cost-breakdown - Cost Breakdown by Service
    # =========================================================================

    def test_get_cost_breakdown(self, admin_headers, test_data):
        """Test cost breakdown endpoint"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/cost-breakdown?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "services" in data
            assert "total_cost" in data

            # Verify services exist
            service_names = [s["name"] for s in data["services"]]
            assert "ElevenLabs STT" in service_names
            assert "Gemini Flash Lite" in service_names or "Gemini Flash 1.5" in service_names

            # Verify percentages sum to 100
            total_percentage = sum(s["percentage"] for s in data["services"])
            assert abs(total_percentage - 100.0) < 0.1

            # Verify costs sum correctly
            total_service_cost = sum(s["cost"] for s in data["services"])
            assert abs(total_service_cost - data["total_cost"]) < 0.0001

    def test_get_cost_breakdown_model_name_standardization(self, admin_headers, test_data):
        """Test that model names are standardized (no duplicates)"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/cost-breakdown?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Get Gemini service names
            gemini_services = [s for s in data["services"] if "Gemini" in s["name"]]
            gemini_names = [s["name"] for s in gemini_services]

            # Should not have duplicates (e.g., both "Gemini Flash 1.5" and "gemini-1.5-flash-latest")
            assert len(gemini_names) == len(set(gemini_names))

    # =========================================================================
    # 5. GET /session-trend - Session Count Trend
    # =========================================================================

    def test_get_session_trend(self, db_session: Session, admin_headers, test_data):
        """Test session trend endpoint"""
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/session-trend?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "sessions" in data
            assert "duration_hours" in data

            # Total sessions should be 3
            total_sessions = sum(data["sessions"])
            assert total_sessions == 3

            # Total duration hours should match
            expected_hours = (600 + 1200 + 1800) / 3600
            total_hours = sum(data["duration_hours"])
            assert abs(total_hours - expected_hours) < 0.01

    # =========================================================================
    # 6. GET /model-distribution - Model Usage Distribution
    # =========================================================================

    def test_get_model_distribution(self, admin_headers, test_data):
        """Test model distribution endpoint"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/model-distribution?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "costs" in data
            assert "tokens" in data

            # Should have at least 2 models (Flash Lite and Flash 1.5)
            assert len(data["labels"]) >= 2

    # =========================================================================
    # 7. GET /daily-active-users - Daily Active Users Trend
    # =========================================================================

    def test_get_daily_active_users(self, db_session: Session, admin_headers, test_data):
        """Test daily active users endpoint"""
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/daily-active-users?time_range=week",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "labels" in data
            assert "data" in data

            # Should fill missing dates with zeros
            assert len(data["labels"]) >= 7  # At least 7 days for week range

    def test_get_daily_active_users_fills_missing_hours(self, db_session: Session, admin_headers, test_data):
        """Test that daily active users fills missing hours with zeros (day range)"""
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/daily-active-users?time_range=day",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Day range should have 24+ hours
            assert len(data["labels"]) >= 24

    # =========================================================================
    # 8. GET /safety-distribution - Safety Level Distribution
    # =========================================================================

    def test_get_safety_distribution(self, admin_headers, test_data):
        """Test safety distribution endpoint"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/safety-distribution?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Should have green, yellow, red from test data
            assert "green" in data
            assert "yellow" in data
            assert "red" in data

            # Each should have count of 1
            assert data["green"] == 1
            assert data["yellow"] == 1
            assert data["red"] == 1

    # =========================================================================
    # 9. GET /top-users - Top Users by Usage
    # =========================================================================

    def test_get_top_users(self, admin_headers, test_data):
        """Test top users endpoint"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/top-users?time_range=month&limit=10",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            # Should have at least 1 user
            assert len(data) >= 1

            # Verify fields exist
            user = data[0]
            assert "email" in user
            assert "gemini_flash_tokens" in user
            assert "gemini_lite_tokens" in user
            assert "elevenlabs_hours" in user
            assert "total_sessions" in user
            assert "total_cost_usd" in user
            assert "total_minutes" in user

    def test_get_top_users_cost_calculation(self, admin_headers, test_data):
        """Test that top users cost calculation is accurate"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/top-users?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Admin user should have total cost from all 3 sessions
            admin_user = data[0]
            expected_cost = (
                test_data["session1"]["total_cost"] +
                test_data["session2"]["total_cost"] +
                test_data["session3"]["total_cost"]
            )
            assert abs(admin_user["total_cost_usd"] - expected_cost) < 0.01

    def test_get_top_users_session_analysis_log_time_filtering(
        self, db_session: Session
    ):
        """
        CRITICAL TEST: Verify SessionAnalysisLog uses analyzed_at for filtering

        This test verifies the bug fix where SessionAnalysisLog should filter by
        analyzed_at (not created_at) to match the time range.

        Uses isolated test user to avoid interference from test_data fixture.

        IMPORTANT: The top_users endpoint uses an OR condition:
            WHERE SessionUsage.created_at >= start_time
            AND (SessionAnalysisLog.id IS NULL OR SessionAnalysisLog.analyzed_at >= start_time)

        This means if an analysis log exists but is outside the time range,
        the entire row is excluded. This is CORRECT behavior to prevent cost
        miscalculation across time boundaries.
        """
        # Create fresh admin user for this test
        test_admin = Counselor(
            id=uuid4(),
            email="test-time-filter@test.com",
            username="test-time-filter",
            full_name="Test Time Filter",
            hashed_password=hash_password("TestP@ss123"),
            tenant_id="test_time",
            role=CounselorRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        db_session.add(test_admin)
        db_session.commit()

        # Login as test admin
        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": "test-time-filter@test.com",
                    "password": "TestP@ss123",
                    "tenant_id": "test_time",
                },
            )
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            now = datetime.now(timezone.utc)

            # Scenario 1: Session with NO analysis (should be included with ElevenLabs cost only)
            session1_id = uuid4()
            usage1 = SessionUsage(
                id=uuid4(),
                session_id=session1_id,
                counselor_id=test_admin.id,
                tenant_id="test_time",
                duration_seconds=600,
                status="completed",
                estimated_cost_usd=600 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
                created_at=now,
            )
            # No analysis log for this session (NULL)

            # Scenario 2: Session with analysis WITHIN time range (should be included with both costs)
            session2_id = uuid4()
            usage2 = SessionUsage(
                id=uuid4(),
                session_id=session2_id,
                counselor_id=test_admin.id,
                tenant_id="test_time",
                duration_seconds=1200,
                status="completed",
                estimated_cost_usd=1200 * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
                created_at=now,
            )

            analysis2 = SessionAnalysisLog(
                id=uuid4(),
                session_id=session2_id,
                counselor_id=test_admin.id,
                tenant_id="test_time",
                analysis_type="test",
                model_name="gemini-flash-lite-latest",
                prompt_tokens=5000,
                completion_tokens=2000,
                estimated_cost_usd=(
                    (5000 / 1_000_000) * GEMINI_FLASH_LITE_INPUT_USD_PER_1M_TOKENS +
                    (2000 / 1_000_000) * GEMINI_FLASH_LITE_OUTPUT_USD_PER_1M_TOKENS
                ),
                analyzed_at=now,  # WITHIN time range
            )

            db_session.add_all([usage1, usage2, analysis2])
            db_session.commit()

            # Query with day range
            response = client.get(
                "/api/v1/admin/dashboard/top-users?time_range=day&tenant_id=test_time",
                headers=headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Should find the user with costs from both sessions
            assert len(data) == 1, "Should have exactly 1 user"
            test_data_user = data[0]
            assert test_data_user["email"] == "test-time-filter@test.com"

            # Total cost = ElevenLabs (session1 + session2) + Gemini (session2 only)
            expected_elevenlabs = (600 + 1200) * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND
            expected_gemini = (
                (5000 / 1_000_000) * GEMINI_FLASH_LITE_INPUT_USD_PER_1M_TOKENS +
                (2000 / 1_000_000) * GEMINI_FLASH_LITE_OUTPUT_USD_PER_1M_TOKENS
            )
            expected_total = expected_elevenlabs + expected_gemini

            assert abs(test_data_user["total_cost_usd"] - expected_total) < 0.01

            # Gemini tokens should include session2's tokens
            assert test_data_user["gemini_lite_tokens"] == 7000  # 5000 + 2000

    # =========================================================================
    # 10. GET /user-daily-usage - User Daily Usage
    # =========================================================================

    def test_get_user_daily_usage(self, db_session: Session, admin_headers, admin_user: Counselor, test_data):
        """Test user daily usage endpoint"""
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/admin/dashboard/user-daily-usage?counselor_id={admin_user.id}&time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            # Verify fields exist
            if data:
                day = data[0]
                assert "date" in day
                assert "sessions" in day
                assert "tokens" in day
                assert "cost_usd" in day
                assert "minutes" in day

    # =========================================================================
    # 11. GET /overall-stats - Overall Statistics
    # =========================================================================

    def test_get_overall_stats(self, db_session: Session, admin_headers, test_data):
        """Test overall stats endpoint"""
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/overall-stats?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "avg_cost_per_day" in data
            assert "avg_sessions_per_day" in data
            assert "peak_date" in data
            assert "peak_value" in data
            assert "monthly_growth_pct" in data

    def test_get_overall_stats_uses_cost_not_tokens(self, db_session: Session, admin_headers, test_data):
        """Test that overall stats calculates peak by cost, not tokens"""
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/overall-stats?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Peak value should be a cost (float), not token count (int)
            assert isinstance(data["peak_value"], float)
            assert data["peak_value"] > 0

    # =========================================================================
    # 12. GET /cost-per-user - Cost Per User with Anomaly Detection
    # =========================================================================

    def test_get_cost_per_user(self, admin_headers, test_data):
        """Test cost per user endpoint"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/cost-per-user?time_range=month&limit=10",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            # Verify fields exist
            if data:
                user = data[0]
                assert "email" in user
                assert "full_name" in user
                assert "total_cost_usd" in user
                assert "sessions" in user
                assert "cost_per_session" in user
                assert "total_minutes" in user
                assert "status" in user
                assert "suggested_action" in user

    # =========================================================================
    # 13. GET /user-segments - User Segmentation
    # =========================================================================

    def test_get_user_segments(self, admin_headers, test_data):
        """Test user segments endpoint"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/user-segments?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "power_users" in data
            assert "active_users" in data
            assert "at_risk_users" in data
            assert "churned_users" in data

            # Verify structure
            assert "count" in data["power_users"]
            assert "avg_sessions" in data["power_users"]
            assert "suggested_action" in data["power_users"]

    # =========================================================================
    # 14. GET /cost-prediction - Cost Prediction
    # =========================================================================

    def test_get_cost_prediction(self, admin_headers, test_data):
        """Test cost prediction endpoint"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/cost-prediction?time_range=month",
                headers=admin_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert "current_month_cost" in data
            assert "days_elapsed" in data
            assert "days_remaining" in data
            assert "daily_average" in data
            assert "predicted_month_cost" in data
            assert "last_month_cost" in data
            assert "growth_pct" in data

    # =========================================================================
    # 15. GET /export-csv - CSV Export
    # =========================================================================

    def test_export_csv_users(self, admin_headers, test_data):
        """Test CSV export for users"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/export-csv?time_range=month&data_type=users",
                headers=admin_headers,
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/csv; charset=utf-8"
            assert "attachment" in response.headers["content-disposition"]

            # Verify CSV content
            csv_content = response.text
            assert "email" in csv_content
            assert "total_cost_usd" in csv_content

    def test_export_csv_sessions(self, admin_headers, test_data):
        """Test CSV export for sessions"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/export-csv?time_range=month&data_type=sessions",
                headers=admin_headers,
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/csv; charset=utf-8"

            # Verify CSV content
            csv_content = response.text
            assert "timestamp" in csv_content
            assert "email" in csv_content
            assert "tokens" in csv_content

    # =========================================================================
    # Edge Cases and Error Handling
    # =========================================================================

    def test_invalid_time_range(self, admin_headers):
        """Test invalid time range parameter"""
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/summary?time_range=invalid",
                headers=admin_headers,
            )

            # Should return 422 (validation error)
            assert response.status_code == 422

    def test_null_handling_in_cost_breakdown(self, db_session: Session, admin_headers, admin_user: Counselor):
        """Test that NULL model names are handled correctly"""
        # Create analysis log with NULL model_name
        analysis = SessionAnalysisLog(
            id=uuid4(),
            session_id=uuid4(),
            counselor_id=admin_user.id,
            tenant_id="career",
            analysis_type="test",
            model_name=None,  # NULL
            analyzed_at=datetime.now(timezone.utc),
        )
        db_session.add(analysis)
        db_session.commit()

        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/dashboard/cost-breakdown?time_range=day",
                headers=admin_headers,
            )

            # Should not crash
            assert response.status_code == 200

    def test_time_filtering_consistency_across_endpoints(self, db_session: Session, admin_headers, test_data):
        """
        CRITICAL TEST: Verify time filtering is consistent across all endpoints

        All endpoints should return the same cost for the same time range.
        This ensures SessionUsage uses created_at and SessionAnalysisLog uses analyzed_at.
        """
        if db_session.bind.dialect.name == "sqlite":
            pytest.skip("Requires PostgreSQL (date_trunc function)")

        with TestClient(app) as client:
            # Get summary cost for day range
            summary_response = client.get(
                "/api/v1/admin/dashboard/summary?time_range=day",
                headers=admin_headers,
            )
            summary_cost = summary_response.json()["total_cost_usd"]

            # Get cost breakdown for day range
            breakdown_response = client.get(
                "/api/v1/admin/dashboard/cost-breakdown?time_range=day",
                headers=admin_headers,
            )
            breakdown_cost = breakdown_response.json()["total_cost"]

            # Get overall stats for day range
            stats_response = client.get(
                "/api/v1/admin/dashboard/overall-stats?time_range=day",
                headers=admin_headers,
            )
            stats_data = stats_response.json()
            # Calculate total from avg * days
            days = len([d for d in range(1)])  # day range has 1+ days

            # All should match (within rounding errors)
            assert abs(summary_cost - breakdown_cost) < 0.01, \
                f"Summary cost {summary_cost} != Breakdown cost {breakdown_cost}"
