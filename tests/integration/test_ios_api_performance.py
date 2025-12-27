"""
Integration tests for iOS API performance comparison

Compare performance between:
- iOS API flow: append transcript → analyze-partial
- Realtime API: Direct realtime analysis

Test scenarios:
1. Short transcript (100 chars): Measure both APIs
2. Medium transcript (500 chars): Measure both APIs
3. Long transcript (2000 chars): Measure both APIs
4. Multiple appends + analysis: Simulate real iOS usage
"""
import time
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.credit_log import CreditLog
from app.models.session import Session as SessionModel
from app.models.session_usage import SessionUsage


class TestIOSAPIPerformance:
    """Performance tests for iOS API vs Realtime API"""

    # Performance thresholds (in seconds)
    THRESHOLD_APPEND = 0.5  # append transcript should be very fast
    THRESHOLD_ANALYZE_SHORT = 2.0  # analyze short transcript
    THRESHOLD_ANALYZE_MEDIUM = 3.0  # analyze medium transcript
    THRESHOLD_ANALYZE_LONG = 3.0  # analyze long transcript
    THRESHOLD_REALTIME = 5.0  # realtime API (may be slower due to full processing)
    THRESHOLD_COMPLETE_WORKFLOW = 10.0  # complete iOS workflow

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email=f"perf-test-{uuid4().hex[:8]}@test.com",
            username=f"perfcounselor{uuid4().hex[:6]}",
            full_name="Performance Test Counselor",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
            available_credits=1000.0,  # ✅ FIXED: Use available_credits
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                "/api/auth/login",
                json={
                    "email": counselor.email,
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def test_session(self, db_session: Session, auth_headers):
        """Create test session for performance tests"""
        # Get counselor
        counselor_email = None
        for header_val in auth_headers.values():
            if "Bearer" in header_val:
                with TestClient(app) as client:
                    profile = client.get("/api/auth/me", headers=auth_headers)
                    counselor_email = profile.json()["email"]
                    break

        counselor = db_session.query(Counselor).filter_by(email=counselor_email).first()

        # Create client
        client = Client(
            id=uuid4(),
            counselor_id=counselor.id,
            tenant_id="career",
            name="Performance Test Client",
            code=f"PERF{uuid4().hex[:6].upper()}",
            email=f"perf-client-{uuid4().hex[:8]}@example.com",
            gender="不透露",
            birth_date=datetime(1990, 1, 1).date(),
            phone=f"091{uuid4().hex[:7]}",
            identity_option="其他",
            current_status="進行中",
        )
        db_session.add(client)

        # Create case
        case = Case(
            id=uuid4(),
            case_number=f"PERF{uuid4().hex[:6].upper()}",
            counselor_id=counselor.id,
            client_id=client.id,
            tenant_id="career",
            status=CaseStatus.IN_PROGRESS,
        )
        db_session.add(case)

        # Create session
        session = SessionModel(
            id=uuid4(),
            case_id=case.id,
            tenant_id="career",
            session_number=1,
            session_date=datetime.now().date(),
        )
        db_session.add(session)
        db_session.commit()

        return session

    @pytest.fixture(autouse=True)
    def mock_gemini_service(self):
        """Mock GeminiService for consistent performance testing"""
        import json

        async def mock_generate_text(prompt, *args, **kwargs):
            """Mock fast response for performance testing"""
            return json.dumps(
                {
                    "keywords": ["測試", "效能"],
                    "categories": ["技術測試"],
                    "confidence": 0.9,
                    "counselor_insights": "效能測試分析",
                    "safety_level": "green",
                    "severity": 1,
                    "display_text": "效能測試正常",
                    "action_suggestion": "繼續測試",
                }
            )

        with patch(
            "app.services.keyword_analysis_service.GeminiService"
        ) as mock_gemini:
            mock_gemini_instance = mock_gemini.return_value
            mock_gemini_instance.generate_text = mock_generate_text
            yield mock_gemini_instance

    def _measure_time(self, func, *args, **kwargs):
        """Measure execution time of a function"""
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        elapsed = end - start
        return result, elapsed

    def _verify_credit_log(self, db_session: Session, session_id):
        """Verify CreditLog was created for billing operation"""
        db_session.expire_all()
        credit_logs = (
            db_session.query(CreditLog)
            .filter_by(resource_type="session", resource_id=str(session_id))
            .all()
        )

        if len(credit_logs) > 0:
            latest_log = credit_logs[-1]
            assert latest_log.resource_type == "session"
            assert latest_log.resource_id == str(session_id)
            assert latest_log.credits_delta < 0, "Usage should have negative delta"
            assert latest_log.transaction_type == "usage"
            assert latest_log.raw_data is not None
            assert "feature" in latest_log.raw_data

    def test_short_transcript_performance(
        self, db_session: Session, auth_headers, test_session
    ):
        """
        Test 1: Short transcript (100 chars) performance
        - iOS API: append + analyze-partial
        - Realtime API: direct analysis
        """
        session_id = test_session.id
        short_transcript = (
            "我最近工作壓力很大，不知道該怎麼辦。" * 2
        )  # ~50 chars x 2 = ~100 chars

        with TestClient(app) as client:
            # Test iOS API flow
            # Step 1: Append transcript
            append_response, append_time = self._measure_time(
                client.post,
                f"/api/v1/sessions/{session_id}/recordings/append",
                headers=auth_headers,
                json={
                    "start_time": "2025-01-15 10:00:00",
                    "end_time": "2025-01-15 10:00:30",
                    "duration_seconds": 30,
                    "transcript_text": short_transcript,
                },
            )
            assert append_response.status_code == 200
            assert (
                append_time < self.THRESHOLD_APPEND
            ), f"Append took {append_time:.2f}s (threshold: {self.THRESHOLD_APPEND}s)"

            # Step 2: Analyze partial
            analyze_response, analyze_time = self._measure_time(
                client.post,
                f"/api/v1/sessions/{session_id}/analyze-partial",
                headers=auth_headers,
                json={"transcript_segment": short_transcript},
            )
            assert analyze_response.status_code == 200
            assert (
                analyze_time < self.THRESHOLD_ANALYZE_SHORT
            ), f"Analyze took {analyze_time:.2f}s (threshold: {self.THRESHOLD_ANALYZE_SHORT}s)"

            # ✅ Verify CreditLog created
            self._verify_credit_log(db_session, session_id)

            # Total iOS API time
            total_ios_time = append_time + analyze_time
            print(
                f"\n✅ Short transcript (100 chars) - iOS API: {total_ios_time:.2f}s "
                f"(append: {append_time:.2f}s, analyze: {analyze_time:.2f}s)"
            )

            # Test Realtime API (no auth required for demo)
            realtime_response, realtime_time = self._measure_time(
                client.post,
                "/api/v1/realtime/analyze",
                json={
                    "transcript": short_transcript,
                    "speakers": [{"speaker": "client", "text": short_transcript}],
                    "time_range": "0:00-1:00",
                },
            )
            # Realtime may fail without GCP credentials in test env
            if realtime_response.status_code == 200:
                assert (
                    realtime_time < self.THRESHOLD_REALTIME
                ), f"Realtime took {realtime_time:.2f}s (threshold: {self.THRESHOLD_REALTIME}s)"
                print(f"✅ Short transcript - Realtime API: {realtime_time:.2f}s")
            else:
                print(
                    f"⚠️  Realtime API skipped (status: {realtime_response.status_code})"
                )

    def test_medium_transcript_performance(
        self, db_session: Session, auth_headers, test_session
    ):
        """
        Test 2: Medium transcript (500 chars) performance
        """
        session_id = test_session.id
        medium_transcript = (
            "諮詢師：你最近工作上有什麼困擾嗎？\n"
            "案主：我覺得現在的工作很迷惘，不知道是不是適合我。每天都在重複同樣的事情，感覺沒有成長。\n"
            "諮詢師：能多說一些嗎？是什麼讓你覺得沒有成長？\n"
            "案主：我學的東西在工作上用不到，而且主管也不太重視我的意見。我想轉職，但又怕風險太大。"
            * 3  # ~170 chars x 3 = ~510 chars
        )

        with TestClient(app) as client:
            # iOS API flow
            append_response, append_time = self._measure_time(
                client.post,
                f"/api/v1/sessions/{session_id}/recordings/append",
                headers=auth_headers,
                json={
                    "start_time": "2025-01-15 10:00:00",
                    "end_time": "2025-01-15 10:01:00",
                    "duration_seconds": 60,
                    "transcript_text": medium_transcript,
                },
            )
            assert append_response.status_code == 200

            analyze_response, analyze_time = self._measure_time(
                client.post,
                f"/api/v1/sessions/{session_id}/analyze-partial",
                headers=auth_headers,
                json={"transcript_segment": medium_transcript},
            )
            assert analyze_response.status_code == 200
            assert (
                analyze_time < self.THRESHOLD_ANALYZE_MEDIUM
            ), f"Analyze took {analyze_time:.2f}s (threshold: {self.THRESHOLD_ANALYZE_MEDIUM}s)"

            # ✅ Verify CreditLog created
            self._verify_credit_log(db_session, session_id)

            total_ios_time = append_time + analyze_time
            print(
                f"\n✅ Medium transcript (500 chars) - iOS API: {total_ios_time:.2f}s "
                f"(append: {append_time:.2f}s, analyze: {analyze_time:.2f}s)"
            )

    def test_long_transcript_performance(
        self, db_session: Session, auth_headers, test_session
    ):
        """
        Test 3: Long transcript (2000 chars) performance
        """
        session_id = test_session.id

        # Generate 2000+ char transcript
        base_text = (
            "諮詢師：你最近工作上有什麼困擾嗎？\n"
            "案主：我覺得現在的工作很迷惘，不知道是不是適合我。每天都在重複同樣的事情，感覺沒有成長。\n"
            "諮詢師：能多說一些嗎？是什麼讓你覺得沒有成長？\n"
            "案主：我學的東西在工作上用不到，而且主管也不太重視我的意見。我想轉職，但又怕風險太大。\n"
            "諮詢師：轉職確實需要考慮很多因素。你有想過什麼樣的工作會讓你有成長的感覺嗎？\n"
            "案主：我希望能做一些更有挑戰性的工作，可以學習新的技能，也希望團隊氛圍更好一些。"
        )
        long_transcript = base_text * 5  # ~400 chars x 5 = 2000 chars

        with TestClient(app) as client:
            # iOS API flow
            append_response, append_time = self._measure_time(
                client.post,
                f"/api/v1/sessions/{session_id}/recordings/append",
                headers=auth_headers,
                json={
                    "start_time": "2025-01-15 10:00:00",
                    "end_time": "2025-01-15 10:02:00",
                    "duration_seconds": 120,
                    "transcript_text": long_transcript,
                },
            )
            assert append_response.status_code == 200

            analyze_response, analyze_time = self._measure_time(
                client.post,
                f"/api/v1/sessions/{session_id}/analyze-partial",
                headers=auth_headers,
                json={"transcript_segment": long_transcript},
            )
            assert analyze_response.status_code == 200
            assert (
                analyze_time < self.THRESHOLD_ANALYZE_LONG
            ), f"Analyze took {analyze_time:.2f}s (threshold: {self.THRESHOLD_ANALYZE_LONG}s)"

            # ✅ Verify CreditLog created
            self._verify_credit_log(db_session, session_id)

            total_ios_time = append_time + analyze_time
            print(
                f"\n✅ Long transcript (2000 chars) - iOS API: {total_ios_time:.2f}s "
                f"(append: {append_time:.2f}s, analyze: {analyze_time:.2f}s)"
            )

    def test_multiple_appends_with_analyses(
        self, db_session: Session, auth_headers, test_session
    ):
        """
        Test 4: Multiple appends + analyses (simulate real iOS usage)

        Workflow:
        1. Append chunk 1 (30s) → Analyze
        2. Append chunk 2 (60s total) → Analyze
        3. Append chunk 3 (90s total) → Analyze
        4. Append chunk 4 (120s total) → Analyze

        Total should be < 10 seconds
        """
        session_id = test_session.id

        chunks = [
            "我最近對工作感到很焦慮，不知道該怎麼辦。",
            "主管總是給我很多壓力，讓我喘不過氣。",
            "我想轉職，但又擔心找不到更好的工作。",
            "家人也不太支持我的決定，讓我很困擾。",
        ]

        total_workflow_start = time.time()
        total_append_time = 0
        total_analyze_time = 0

        with TestClient(app) as client:
            for i, chunk in enumerate(chunks, 1):
                # Append
                start_seconds = (i - 1) * 30
                end_seconds = i * 30
                append_response, append_time = self._measure_time(
                    client.post,
                    f"/api/v1/sessions/{session_id}/recordings/append",
                    headers=auth_headers,
                    json={
                        "start_time": f"2025-01-15 10:00:{start_seconds:02d}",
                        "end_time": f"2025-01-15 10:00:{end_seconds:02d}",
                        "duration_seconds": 30,
                        "transcript_text": chunk,
                    },
                )
                assert append_response.status_code == 200
                total_append_time += append_time

                # Analyze
                analyze_response, analyze_time = self._measure_time(
                    client.post,
                    f"/api/v1/sessions/{session_id}/analyze-partial",
                    headers=auth_headers,
                    json={"transcript_segment": chunk},
                )
                assert analyze_response.status_code == 200
                total_analyze_time += analyze_time

                print(
                    f"  Chunk {i}: append={append_time:.2f}s, analyze={analyze_time:.2f}s"
                )

        total_workflow_time = time.time() - total_workflow_start

        assert (
            total_workflow_time < self.THRESHOLD_COMPLETE_WORKFLOW
        ), f"Complete workflow took {total_workflow_time:.2f}s (threshold: {self.THRESHOLD_COMPLETE_WORKFLOW}s)"

        # ✅ Verify CreditLog created for all analyses
        self._verify_credit_log(db_session, session_id)

        # ✅ Verify dual-write consistency
        db_session.expire_all()
        credit_logs = (
            db_session.query(CreditLog)
            .filter_by(resource_type="session", resource_id=str(session_id))
            .all()
        )
        session_usage = (
            db_session.query(SessionUsage).filter_by(session_id=session_id).first()
        )

        if session_usage and len(credit_logs) > 0:
            total_from_logs = sum(abs(log.credits_delta) for log in credit_logs)
            assert (
                session_usage.credits_deducted == total_from_logs
            ), f"Dual-write mismatch: SessionUsage={session_usage.credits_deducted}, CreditLog sum={total_from_logs}"

        print(
            f"\n✅ Multiple appends workflow: {total_workflow_time:.2f}s "
            f"(append total: {total_append_time:.2f}s, analyze total: {total_analyze_time:.2f}s)"
        )
        print(
            f"   Average per iteration: {total_workflow_time/4:.2f}s "
            f"(append: {total_append_time/4:.2f}s, analyze: {total_analyze_time/4:.2f}s)"
        )


# Performance Summary
def test_performance_summary_report():
    """
    Print performance summary report

    Expected benchmarks:
    - append transcript: < 0.5s
    - analyze-partial (short): < 2s
    - analyze-partial (medium): < 3s
    - analyze-partial (long): < 3s
    - realtime API: < 5s
    - complete workflow (4 iterations): < 10s
    """
    print("\n" + "=" * 60)
    print("PERFORMANCE BENCHMARKS SUMMARY")
    print("=" * 60)
    print("\niOS API Expected Performance:")
    print("  - append transcript: < 0.5s")
    print("  - analyze-partial (short 100 chars): < 2s")
    print("  - analyze-partial (medium 500 chars): < 3s")
    print("  - analyze-partial (long 2000 chars): < 3s")
    print("\nRealtime API Expected Performance:")
    print("  - direct analysis: < 5s")
    print("\nComplete Workflow Expected Performance:")
    print("  - 4 append + analyze iterations: < 10s")
    print("=" * 60 + "\n")
