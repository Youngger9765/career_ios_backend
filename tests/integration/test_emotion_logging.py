"""
Integration test for Emotion API logging to DB and BigQuery

Tests verify that emotion analysis results are properly logged to:
1. SessionAnalysisLog table (PostgreSQL)
2. BigQuery (via background task)
"""
import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session as SessionModel
from app.models.session_analysis_log import SessionAnalysisLog

# Skip in CI due to Gemini API usage (expensive)
pytestmark = pytest.mark.skip(
    reason="Skipped in CI due to Gemini API usage (expensive)"
)


class TestEmotionLogging:
    """Test that emotion analysis is properly logged to DB and BigQuery"""

    @pytest.fixture
    def auth_headers(self, db_session: Session):
        """Create authenticated counselor and return auth headers"""
        counselor = Counselor(
            id=uuid4(),
            email="log-test@island-parents.com",
            username="logtest",
            full_name="Log Test Counselor",
            hashed_password=hash_password("ValidP@ssw0rd123"),
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
                    "email": "log-test@island-parents.com",
                    "password": "ValidP@ssw0rd123",
                    "tenant_id": "island_parents",
                },
            )
            token = login_response.json()["access_token"]

        return {"Authorization": f"Bearer {token}"}, counselor.id

    @pytest.fixture
    def test_session_obj(self, db_session: Session, auth_headers):
        """Create a test session for logging tests"""
        from datetime import date

        auth_header, counselor_id = auth_headers

        client = Client(
            id=uuid4(),
            counselor_id=counselor_id,
            tenant_id="island_parents",
            name="日誌測試家長",
            code="LOGCLI001",
            email="logcli001@example.com",
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
            case_number="LOGCASE001",
            counselor_id=counselor_id,
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
            name="日誌測試會談",
        )
        db_session.add(session)
        db_session.commit()

        return session, auth_header

    def test_emotion_analysis_creates_log_entry(
        self, db_session: Session, test_session_obj
    ):
        """
        Test that emotion analysis creates a SessionAnalysisLog entry

        Flow:
        1. Call emotion-feedback API
        2. Wait for background task to complete
        3. Verify log entry exists in SessionAnalysisLog table
        4. Verify log contains correct data
        """
        session, auth_header = test_session_obj

        # Count existing logs before API call
        log_count_before = (
            db_session.query(SessionAnalysisLog)
            .filter_by(session_id=session.id)
            .count()
        )

        # Call emotion-feedback API
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/emotion-feedback",
                headers=auth_header,
                json={
                    "context": "小明：今天好累\n媽媽：早點休息吧",
                    "target": "你辛苦了，早點睡",
                },
            )

            assert response.status_code == 200, f"API failed: {response.json()}"

        # Wait for background task to complete (max 3 seconds)
        time.sleep(3)

        # Refresh session to get latest data
        db_session.expire_all()

        # Verify log entry was created
        log_count_after = (
            db_session.query(SessionAnalysisLog)
            .filter_by(session_id=session.id)
            .count()
        )

        assert (
            log_count_after == log_count_before + 1
        ), f"Expected 1 new log entry, found {log_count_after - log_count_before}"

        # Get the latest log entry
        latest_log = (
            db_session.query(SessionAnalysisLog)
            .filter_by(session_id=session.id)
            .order_by(SessionAnalysisLog.created_at.desc())
            .first()
        )

        # Verify log content
        assert latest_log is not None, "Log entry not found"
        assert latest_log.analysis_type is None or "emotion" in str(
            latest_log.result_data
        ), "Log should contain emotion analysis data"
        assert latest_log.result_data is not None, "result_data should not be None"
        assert (
            "level" in latest_log.result_data
        ), "result_data should contain 'level'"
        assert "hint" in latest_log.result_data, "result_data should contain 'hint'"

        # Verify token usage was tracked
        assert (
            latest_log.prompt_tokens is not None
        ), "prompt_tokens should be tracked"
        assert (
            latest_log.completion_tokens is not None
        ), "completion_tokens should be tracked"
        assert latest_log.total_tokens is not None, "total_tokens should be tracked"

        print(f"✓ Log entry created with ID: {latest_log.id}")
        print(f"✓ Emotion level: {latest_log.result_data.get('level')}")
        print(f"✓ Hint: {latest_log.result_data.get('hint')}")
        print(
            f"✓ Token usage: {latest_log.prompt_tokens}p + {latest_log.completion_tokens}c = {latest_log.total_tokens}t"
        )

    def test_emotion_logging_includes_context_preview(
        self, db_session: Session, test_session_obj
    ):
        """
        Test that logged data includes context preview for debugging

        Verify:
        1. transcript_segment contains context preview
        2. result_data contains target sentence
        3. Metadata includes latency
        """
        session, auth_header = test_session_obj

        context_text = "小明：我考試不及格\n媽媽：你有認真準備嗎？\n小明：我有啊！"
        target_text = "你就是不用功！"

        # Call emotion-feedback API
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/sessions/{session.id}/emotion-feedback",
                headers=auth_header,
                json={
                    "context": context_text,
                    "target": target_text,
                },
            )

            assert response.status_code == 200, f"API failed: {response.json()}"

        # Wait for background task
        time.sleep(3)
        db_session.expire_all()

        # Get the latest log entry
        latest_log = (
            db_session.query(SessionAnalysisLog)
            .filter_by(session_id=session.id)
            .order_by(SessionAnalysisLog.created_at.desc())
            .first()
        )

        assert latest_log is not None, "Log entry not found"

        # Verify transcript_segment contains context (first 500 chars)
        assert (
            latest_log.transcript_segment is not None
        ), "transcript_segment should not be None"
        assert (
            context_text[:100] in latest_log.transcript_segment
        ), "transcript_segment should contain context preview"

        # Verify result_data contains target
        assert (
            "target" in latest_log.result_data
        ), "result_data should contain target"
        assert (
            latest_log.result_data["target"] == target_text
        ), "target should match input"

        # Verify metadata includes latency
        assert (
            "_metadata" in latest_log.result_data
        ), "result_data should contain _metadata"
        assert (
            "latency_ms" in latest_log.result_data["_metadata"]
        ), "metadata should contain latency_ms"
        assert (
            latest_log.result_data["_metadata"]["latency_ms"] > 0
        ), "latency_ms should be positive"

        print(f"✓ Context preview logged: {latest_log.transcript_segment[:50]}...")
        print(f"✓ Target logged: {latest_log.result_data['target']}")
        print(
            f"✓ Latency: {latest_log.result_data['_metadata']['latency_ms']}ms"
        )
