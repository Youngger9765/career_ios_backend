"""
Integration Tests for Realtime API GBQ Persistence (Phase 1.3)
TDD RED PHASE - Tests written FIRST to define expected behavior

These tests validate that realtime analysis results are persisted to BigQuery.
"""
from unittest.mock import patch

import pytest


# Skip these tests if Google Cloud credentials are not available
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

skip_without_gcp = pytest.mark.skipif(
    not HAS_VALID_GCP_CREDENTIALS,
    reason="Valid Google Cloud credentials not available (run: gcloud auth application-default login)",
)


class TestRealtimeGBQPersistence:
    """Test GBQ persistence for Realtime API analysis results

    Expected behavior (TDD RED - will fail until implemented):
    1. After successful analysis, data is written to BigQuery asynchronously
    2. GBQ write failures do not block API response
    3. Data format matches the schema defined in Parents_RAG_refine.md
    4. tenant_id is always "island_parents" for web version
    5. session_id is None for web version
    """

    @skip_without_gcp
    def test_realtime_analysis_writes_to_gbq_async(self, client, db_session):
        """Realtime analysis should write results to BigQuery asynchronously

        Expected behavior (RED - will fail until implemented):
        - API returns immediately (not blocked by GBQ write)
        - GBQ write happens in background
        - Data includes all required fields from schema
        """
        with patch("app.api.realtime.write_to_gbq_async") as mock_gbq_write:
            # Configure mock to simulate async execution
            mock_gbq_write.return_value = None

            request = {
                "transcript": "家長：你今天在學校過得如何？\n孩子：還不錯，老師稱讚我了。",
                "speakers": [
                    {"speaker": "client", "text": "你今天在學校過得如何？"},
                    {"speaker": "client", "text": "還不錯，老師稱讚我了。"},
                ],
                "time_range": "0:00-1:00",
                "mode": "emergency",
                "provider": "gemini",
            }

            # Make API call
            response = client.post("/api/v1/transcript/deep-analyze", json=request)

            # API should return immediately (200 OK)
            assert response.status_code == 200

            # Verify GBQ write was called
            assert mock_gbq_write.called, "GBQ write function should be called"

            # Extract the call arguments
            call_args = mock_gbq_write.call_args
            gbq_data = call_args[0][0] if call_args[0] else call_args[1].get("data")

            # Validate GBQ data structure
            assert "id" in gbq_data, "GBQ data should have UUID id"
            assert "tenant_id" in gbq_data
            assert gbq_data["tenant_id"] == "island_parents"
            assert "session_id" in gbq_data
            assert (
                gbq_data["session_id"] is None
            ), "Web version should have None session_id"
            assert "analyzed_at" in gbq_data
            assert "analysis_type" in gbq_data
            assert gbq_data["analysis_type"] == "emergency"
            assert "safety_level" in gbq_data
            assert gbq_data["safety_level"] in ["green", "yellow", "red"]
            assert "matched_suggestions" in gbq_data
            assert isinstance(gbq_data["matched_suggestions"], list)
            assert "transcript_segment" in gbq_data
            assert "response_time_ms" in gbq_data
            assert isinstance(gbq_data["response_time_ms"], (int, float))
            assert "created_at" in gbq_data

    @skip_without_gcp
    def test_gbq_write_failure_does_not_block_api_response(self, client, db_session):
        """GBQ write failures should not prevent API from returning success

        Expected behavior (RED - will fail until implemented):
        - If GBQ write fails, API still returns 200
        - Error is logged but not raised
        - User gets analysis results despite GBQ failure
        """
        with patch(
            "app.services.gbq_service.gbq_service.write_analysis_log"
        ) as mock_gbq_write:
            # Simulate GBQ write failure (async)
            async def async_exception(*args, **kwargs):
                raise Exception("GBQ unavailable")

            mock_gbq_write.side_effect = async_exception

            request = {
                "transcript": "家長：你今天在學校過得如何？",
                "speakers": [{"speaker": "client", "text": "你今天在學校過得如何？"}],
                "time_range": "0:00-1:00",
                "mode": "emergency",
                "provider": "gemini",
            }

            # API should still return 200 despite GBQ failure
            response = client.post("/api/v1/transcript/deep-analyze", json=request)
            assert response.status_code == 200

            # Response should contain analysis results
            data = response.json()
            assert "safety_level" in data
            assert "suggestions" in data

    @skip_without_gcp
    def test_practice_mode_writes_correct_analysis_type_to_gbq(
        self, client, db_session
    ):
        """Practice mode should write analysis_type='practice' to GBQ

        Expected behavior (RED - will fail until implemented):
        - analysis_type matches the mode parameter
        - practice mode data includes 3-4 suggestions
        """
        with patch("app.api.realtime.write_to_gbq_async") as mock_gbq_write:
            mock_gbq_write.return_value = None

            request = {
                "transcript": "家長：孩子最近很煩人，不過我知道是因為他壓力大。",
                "speakers": [
                    {"speaker": "client", "text": "孩子最近很煩人"},
                    {"speaker": "client", "text": "不過我知道是因為他壓力大"},
                ],
                "time_range": "0:00-1:00",
                "mode": "practice",
                "provider": "gemini",
            }

            response = client.post("/api/v1/transcript/deep-analyze", json=request)
            assert response.status_code == 200

            # Verify GBQ data
            call_args = mock_gbq_write.call_args
            gbq_data = call_args[0][0] if call_args[0] else call_args[1].get("data")

            assert gbq_data["analysis_type"] == "practice"
            assert (
                3 <= len(gbq_data["matched_suggestions"]) <= 4
            ), "Practice mode should have 3-4 suggestions"

    @skip_without_gcp
    def test_gbq_data_includes_response_time_metric(self, client, db_session):
        """GBQ data should include API response time for performance monitoring

        Expected behavior (RED - will fail until implemented):
        - response_time_ms is calculated and included
        - Value is positive integer/float in milliseconds
        """
        with patch("app.api.realtime.write_to_gbq_async") as mock_gbq_write:
            mock_gbq_write.return_value = None

            request = {
                "transcript": "家長：你今天在學校過得如何？",
                "speakers": [{"speaker": "client", "text": "你今天在學校過得如何？"}],
                "time_range": "0:00-1:00",
                "mode": "emergency",
                "provider": "gemini",
            }

            response = client.post("/api/v1/transcript/deep-analyze", json=request)
            assert response.status_code == 200

            # Verify response time is recorded
            call_args = mock_gbq_write.call_args
            gbq_data = call_args[0][0] if call_args[0] else call_args[1].get("data")

            assert "response_time_ms" in gbq_data
            assert isinstance(gbq_data["response_time_ms"], (int, float))
            assert gbq_data["response_time_ms"] > 0, "Response time should be positive"

    @skip_without_gcp
    def test_gbq_write_logs_errors_without_failing_silently(
        self, client, db_session, caplog
    ):
        """GBQ write errors should be logged, not fail silently

        Expected behavior (RED - will fail until implemented):
        - Errors are logged with appropriate severity
        - Error message includes context (what failed)
        - No silent failures
        """
        import logging

        with patch(
            "app.services.gbq_service.gbq_service.write_analysis_log"
        ) as mock_gbq_write:
            # Simulate GBQ error (async)
            async def async_exception(*args, **kwargs):
                raise Exception("BigQuery API error: quota exceeded")

            mock_gbq_write.side_effect = async_exception

            request = {
                "transcript": "家長：你今天在學校過得如何？",
                "speakers": [{"speaker": "client", "text": "你今天在學校過得如何？"}],
                "time_range": "0:00-1:00",
                "mode": "emergency",
                "provider": "gemini",
            }

            with caplog.at_level(logging.ERROR):
                response = client.post("/api/v1/transcript/deep-analyze", json=request)
                assert response.status_code == 200

            # Verify error was logged
            assert any(
                "BigQuery" in record.message or "GBQ" in record.message
                for record in caplog.records
            ), "GBQ errors should be logged"
