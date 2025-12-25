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
            response = client.post("/api/v1/realtime/analyze", json=request)

            # API should return immediately (200 OK)
            assert response.status_code == 200

            # Verify GBQ write was called
            assert mock_gbq_write.called, "GBQ write function should be called"

            # Extract the call arguments
            call_args = mock_gbq_write.call_args
            gbq_data = call_args[0][0] if call_args[0] else call_args[1].get("data")

            # Validate GBQ data structure - Basic info
            assert "id" in gbq_data, "GBQ data should have UUID id"
            assert "tenant_id" in gbq_data
            assert gbq_data["tenant_id"] == "island_parents"
            assert "session_id" in gbq_data
            assert "analyzed_at" in gbq_data
            assert "created_at" in gbq_data

            # Analysis results
            assert "analysis_type" in gbq_data
            assert gbq_data["analysis_type"] == "emergency"
            assert "safety_level" in gbq_data
            assert gbq_data["safety_level"] in ["green", "yellow", "red"]
            assert "matched_suggestions" in gbq_data
            assert isinstance(gbq_data["matched_suggestions"], list)

            # Complete transcript (NO truncation!)
            assert "transcript" in gbq_data, "Should have full transcript"
            assert (
                gbq_data["transcript"] == request["transcript"]
            ), "Transcript should NOT be truncated"
            assert "time_range" in gbq_data
            assert gbq_data["time_range"] == "0:00-1:00"

            # Complete analysis result
            assert "analysis_result" in gbq_data
            assert isinstance(gbq_data["analysis_result"], dict)

            # NEW: Prompt information
            assert "system_prompt" in gbq_data, "Should capture system prompt"
            assert "user_prompt" in gbq_data, "Should capture user prompt"
            assert "prompt_template" in gbq_data, "Should capture prompt template name"

            # RAG information
            assert "rag_used" in gbq_data
            assert isinstance(gbq_data["rag_used"], bool)
            assert "rag_documents" in gbq_data
            assert "rag_sources" in gbq_data
            assert isinstance(gbq_data["rag_sources"], list)
            # NEW: RAG metadata
            assert "rag_query" in gbq_data, "Should capture RAG query"
            assert "rag_top_k" in gbq_data, "Should capture RAG top_k parameter"
            assert (
                "rag_similarity_threshold" in gbq_data
            ), "Should capture similarity threshold"

            # Model & Provider info
            assert "provider" in gbq_data
            assert gbq_data["provider"] == "gemini"
            assert "model_name" in gbq_data
            assert gbq_data["model_name"] != ""
            # NEW: Model version
            assert "model_version" in gbq_data, "Should capture model version"

            # Token usage
            assert "prompt_tokens" in gbq_data
            assert isinstance(gbq_data["prompt_tokens"], int)
            assert "completion_tokens" in gbq_data
            assert isinstance(gbq_data["completion_tokens"], int)
            assert "total_tokens" in gbq_data
            assert isinstance(gbq_data["total_tokens"], int)
            assert "estimated_cost_usd" in gbq_data
            assert isinstance(gbq_data["estimated_cost_usd"], float)
            # NEW: Cached tokens
            assert "cached_tokens" in gbq_data, "Should track cached tokens"
            assert isinstance(gbq_data["cached_tokens"], int)

            # Performance metrics
            assert "start_time" in gbq_data
            assert "end_time" in gbq_data
            assert "duration_ms" in gbq_data
            assert isinstance(gbq_data["duration_ms"], int)
            assert gbq_data["duration_ms"] > 0
            assert "api_response_time_ms" in gbq_data
            assert isinstance(gbq_data["api_response_time_ms"], (int, float))
            # NEW: Detailed timing breakdown
            assert "rag_search_time_ms" in gbq_data, "Should track RAG search time"
            assert isinstance(gbq_data["rag_search_time_ms"], int)
            assert "llm_call_time_ms" in gbq_data, "Should track LLM call time"
            assert isinstance(gbq_data["llm_call_time_ms"], int)

            # NEW: LLM response metadata
            assert "llm_raw_response" in gbq_data, "Should capture raw LLM response"
            assert (
                "analysis_reasoning" in gbq_data
            ), "Should capture reasoning from analysis"

            # Cache information
            assert "use_cache" in gbq_data
            assert isinstance(gbq_data["use_cache"], bool)
            # NEW: Extended cache metadata
            assert "cache_hit" in gbq_data, "Should track cache hit"
            assert isinstance(gbq_data["cache_hit"], bool)
            assert "cache_key" in gbq_data, "Should track cache key"
            assert "gemini_cache_ttl" in gbq_data, "Should track cache TTL"

            # Request context
            assert "speakers" in gbq_data
            assert isinstance(gbq_data["speakers"], list)
            assert len(gbq_data["speakers"]) == 2
            assert "mode" in gbq_data
            assert gbq_data["mode"] == "emergency"
            # NEW: Request ID
            assert "request_id" in gbq_data, "Should have request ID"

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
            response = client.post("/api/v1/realtime/analyze", json=request)
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

            response = client.post("/api/v1/realtime/analyze", json=request)
            assert response.status_code == 200

            # Verify GBQ data
            call_args = mock_gbq_write.call_args
            gbq_data = call_args[0][0] if call_args[0] else call_args[1].get("data")

            assert gbq_data["analysis_type"] == "practice"
            assert (
                3 <= len(gbq_data["matched_suggestions"]) <= 4
            ), "Practice mode should have 3-4 suggestions"

    @skip_without_gcp
    def test_gbq_data_includes_performance_metrics(self, client, db_session):
        """GBQ data should include complete performance metrics for monitoring

        Expected behavior (RED - will fail until implemented):
        - start_time, end_time, duration_ms are calculated and included
        - api_response_time_ms is calculated
        - All values are valid and positive
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

            response = client.post("/api/v1/realtime/analyze", json=request)
            assert response.status_code == 200

            # Verify performance metrics
            call_args = mock_gbq_write.call_args
            gbq_data = call_args[0][0] if call_args[0] else call_args[1].get("data")

            assert "start_time" in gbq_data
            assert "end_time" in gbq_data
            assert "duration_ms" in gbq_data
            assert isinstance(gbq_data["duration_ms"], int)
            assert gbq_data["duration_ms"] > 0, "Duration should be positive"

            assert "api_response_time_ms" in gbq_data
            assert isinstance(gbq_data["api_response_time_ms"], (int, float))
            assert (
                gbq_data["api_response_time_ms"] > 0
            ), "API response time should be positive"

    @skip_without_gcp
    def test_complete_transcript_stored_without_truncation(self, client, db_session):
        """Complete transcript should be stored WITHOUT any truncation

        Expected behavior (RED - will fail until implemented):
        - Full transcript is stored, not limited to 1000 chars
        - Long transcripts (> 1000 chars) are stored completely
        - time_range is included
        """
        with patch("app.api.realtime.write_to_gbq_async") as mock_gbq_write:
            mock_gbq_write.return_value = None

            # Create a long transcript (> 1000 chars)
            long_transcript = "家長：" + "這是很長的對話內容。" * 100  # ~1500 chars

            request = {
                "transcript": long_transcript,
                "speakers": [{"speaker": "client", "text": long_transcript}],
                "time_range": "0:00-2:30",
                "mode": "emergency",
                "provider": "gemini",
            }

            response = client.post("/api/v1/realtime/analyze", json=request)
            assert response.status_code == 200

            # Verify complete transcript is stored
            call_args = mock_gbq_write.call_args
            gbq_data = call_args[0][0] if call_args[0] else call_args[1].get("data")

            assert "transcript" in gbq_data
            assert (
                gbq_data["transcript"] == long_transcript
            ), "Transcript should NOT be truncated"
            assert (
                len(gbq_data["transcript"]) > 1000
            ), "Long transcript should exceed 1000 chars"
            assert "time_range" in gbq_data
            assert gbq_data["time_range"] == "0:00-2:30"

    @skip_without_gcp
    def test_rag_metadata_stored_when_rag_used(self, client, db_session):
        """RAG metadata should be stored when RAG is triggered

        Expected behavior (RED - will fail until implemented):
        - rag_used is True when parenting keywords detected
        - rag_documents contains full RAG search results
        - rag_sources contains document titles
        """
        with patch("app.api.realtime.write_to_gbq_async") as mock_gbq_write:
            mock_gbq_write.return_value = None

            # Use parenting keywords to trigger RAG
            request = {
                "transcript": "家長：孩子最近很叛逆，情緒管理很差，我該怎麼教養他？",
                "speakers": [
                    {
                        "speaker": "client",
                        "text": "孩子最近很叛逆，情緒管理很差，我該怎麼教養他？",
                    }
                ],
                "time_range": "0:00-1:00",
                "mode": "practice",
                "provider": "gemini",
            }

            response = client.post("/api/v1/realtime/analyze", json=request)
            assert response.status_code == 200

            # Verify RAG metadata
            call_args = mock_gbq_write.call_args
            gbq_data = call_args[0][0] if call_args[0] else call_args[1].get("data")

            assert "rag_used" in gbq_data
            assert isinstance(gbq_data["rag_used"], bool)
            # RAG may or may not be used depending on database content
            # Just verify fields are present
            assert "rag_documents" in gbq_data
            assert "rag_sources" in gbq_data
            assert isinstance(gbq_data["rag_sources"], list)

    @skip_without_gcp
    def test_token_usage_and_cost_tracked(self, client, db_session):
        """Token usage and estimated cost should be tracked for all providers

        Expected behavior (RED - will fail until implemented):
        - prompt_tokens, completion_tokens, total_tokens are recorded
        - estimated_cost_usd is calculated
        - Values are non-negative
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

            response = client.post("/api/v1/realtime/analyze", json=request)
            assert response.status_code == 200

            # Verify token usage and cost
            call_args = mock_gbq_write.call_args
            gbq_data = call_args[0][0] if call_args[0] else call_args[1].get("data")

            assert "prompt_tokens" in gbq_data
            assert isinstance(gbq_data["prompt_tokens"], int)
            assert gbq_data["prompt_tokens"] >= 0

            assert "completion_tokens" in gbq_data
            assert isinstance(gbq_data["completion_tokens"], int)
            assert gbq_data["completion_tokens"] >= 0

            assert "total_tokens" in gbq_data
            assert isinstance(gbq_data["total_tokens"], int)
            assert gbq_data["total_tokens"] >= 0

            assert "estimated_cost_usd" in gbq_data
            assert isinstance(gbq_data["estimated_cost_usd"], float)
            assert gbq_data["estimated_cost_usd"] >= 0.0

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
                response = client.post("/api/v1/realtime/analyze", json=request)
                assert response.status_code == 200

            # Verify error was logged
            assert any(
                "BigQuery" in record.message or "GBQ" in record.message
                for record in caplog.records
            ), "GBQ errors should be logged"

    @skip_without_gcp
    def test_rag_timing_and_prompts_tracked(self, client, db_session):
        """RAG search timing and prompts should be tracked for observability

        Expected behavior (RED - will fail until implemented):
        - rag_search_time_ms is tracked when RAG is used
        - system_prompt and user_prompt are captured
        - llm_raw_response is stored
        - All timing values are non-negative
        """
        with patch("app.api.realtime.write_to_gbq_async") as mock_gbq_write:
            mock_gbq_write.return_value = None

            # Use parenting keywords to potentially trigger RAG
            request = {
                "transcript": "家長：孩子最近很叛逆，情緒管理很差，我該怎麼教養他？",
                "speakers": [
                    {
                        "speaker": "client",
                        "text": "孩子最近很叛逆，情緒管理很差，我該怎麼教養他？",
                    }
                ],
                "time_range": "0:00-1:00",
                "mode": "practice",
                "provider": "gemini",
            }

            response = client.post("/api/v1/realtime/analyze", json=request)
            assert response.status_code == 200

            # Verify timing and prompt tracking
            call_args = mock_gbq_write.call_args
            gbq_data = call_args[0][0] if call_args[0] else call_args[1].get("data")

            # Timing breakdown
            assert "rag_search_time_ms" in gbq_data
            assert isinstance(gbq_data["rag_search_time_ms"], int)
            assert gbq_data["rag_search_time_ms"] >= 0

            assert "llm_call_time_ms" in gbq_data
            assert isinstance(gbq_data["llm_call_time_ms"], int)
            assert gbq_data["llm_call_time_ms"] > 0

            # Prompts
            assert "system_prompt" in gbq_data
            assert gbq_data["system_prompt"] is not None
            assert (
                len(gbq_data["system_prompt"]) > 100
            )  # Should have substantial content

            assert "user_prompt" in gbq_data
            assert gbq_data["user_prompt"] is not None
            assert request["transcript"] in gbq_data["user_prompt"]

            # LLM raw response
            assert "llm_raw_response" in gbq_data
            assert gbq_data["llm_raw_response"] is not None

            # Request ID
            assert "request_id" in gbq_data
            assert gbq_data["request_id"] is not None
