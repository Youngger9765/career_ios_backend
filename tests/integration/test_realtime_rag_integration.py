"""
Integration tests for RAG integration with Realtime Analysis API
TDD - RED Phase: Write tests first, expect them to fail
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


# Skip these tests if Google Cloud credentials are not available or invalid
def _check_gcp_credentials():
    """Check if valid GCP credentials are available"""
    try:
        from google.auth import default
        from google.auth.exceptions import DefaultCredentialsError, RefreshError

        try:
            credentials, project = default()
            # Try to refresh to check if credentials are valid
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


class TestRealtimeRAGIntegration:
    """Test RAG integration with Realtime Analysis API"""

    @skip_without_gcp
    def test_rag_query_triggered_with_career_keywords(self):
        """Test 1: RAG query triggered when transcript contains career keywords

        Scenario: Given a transcript with career-related keywords (轉職, 履歷)
        Expected: API should trigger RAG search and include rag_sources in response
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：你想轉職嗎？\n案主：是的，但我不知道怎麼寫履歷。",
                    "speakers": [
                        {"speaker": "counselor", "text": "你想轉職嗎？"},
                        {"speaker": "client", "text": "是的，但我不知道怎麼寫履歷。"},
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            # Should return 200 OK
            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "summary" in data
            assert "alerts" in data
            assert "suggestions" in data
            assert "rag_sources" in data  # NEW: RAG sources field

            # Verify rag_sources is present and has valid structure
            assert isinstance(data["rag_sources"], list)

            # If RAG found relevant content, verify source structure
            if len(data["rag_sources"]) > 0:
                source = data["rag_sources"][0]
                assert "title" in source
                assert "content" in source
                assert "score" in source
                assert isinstance(source["score"], (int, float))
                assert 0 <= source["score"] <= 1  # Similarity score range

    @skip_without_gcp
    def test_rag_results_integrated_in_suggestions(self):
        """Test 2: RAG results are integrated into AI suggestions

        Scenario: Given transcript: "我想轉職但不知道怎麼寫履歷"
        Expected: AI suggestions should reference knowledge from RAG sources
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "案主：我想轉職，但不知道怎麼寫履歷，也不知道怎麼準備面試。",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我想轉職，但不知道怎麼寫履歷，也不知道怎麼準備面試。",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify suggestions are provided
            assert len(data["suggestions"]) > 0

            # Verify RAG sources are included
            assert "rag_sources" in data

            # If RAG found sources, verify suggestions reference career knowledge
            if len(data["rag_sources"]) > 0:
                suggestions_text = " ".join(data["suggestions"])
                # Suggestions should contain career-related advice
                assert any(
                    keyword in suggestions_text
                    for keyword in ["履歷", "面試", "轉職", "職涯", "求職"]
                )

    @skip_without_gcp
    def test_rag_fallback_when_no_relevant_knowledge(self):
        """Test 3: Fallback gracefully when RAG finds no relevant content

        Scenario: Given transcript with non-career topic
        Expected: API should still work, rag_sources can be empty, no crash
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "諮詢師：今天天氣如何？\n案主：天氣很好。",
                    "speakers": [
                        {"speaker": "counselor", "text": "今天天氣如何？"},
                        {"speaker": "client", "text": "天氣很好。"},
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            # Should still return 200 OK (no crash)
            assert response.status_code == 200
            data = response.json()

            # Should have all required fields
            assert "summary" in data
            assert "alerts" in data
            assert "suggestions" in data
            assert "rag_sources" in data

            # RAG sources can be empty for non-career topics
            assert isinstance(data["rag_sources"], list)

            # API should still provide basic counseling suggestions
            assert len(data["suggestions"]) >= 1

    @skip_without_gcp
    def test_keyword_detection_triggers_rag(self):
        """Test 4: Keyword detection correctly triggers RAG search

        Scenario: Test multiple career keywords: 轉職, 履歷, 面試, 職涯規劃, 離職, 求職
        Expected: All these keywords should trigger RAG search
        """
        keywords_to_test = [
            ("轉職", "我想轉職到科技業。"),
            ("履歷", "我的履歷需要怎麼寫？"),
            ("面試", "面試時該注意什麼？"),
            ("職涯規劃", "我需要做職涯規劃。"),
            ("離職", "我想離職了。"),
            ("求職", "求職過程很艱難。"),
        ]

        with TestClient(app) as client:
            for keyword, text in keywords_to_test:
                response = client.post(
                    "/api/v1/realtime/analyze",
                    json={
                        "transcript": f"案主：{text}",
                        "speakers": [{"speaker": "client", "text": text}],
                        "time_range": "0:00-1:00",
                    },
                )

                assert response.status_code == 200, f"Failed for keyword: {keyword}"
                data = response.json()

                # Should have rag_sources field
                assert (
                    "rag_sources" in data
                ), f"Missing rag_sources for keyword: {keyword}"

                # Should be a list (can be empty if no match, but field must exist)
                assert isinstance(
                    data["rag_sources"], list
                ), f"rag_sources not a list for keyword: {keyword}"

    @skip_without_gcp
    def test_rag_response_schema_validation(self):
        """Test 5: Validate rag_sources response schema

        Scenario: Verify rag_sources has correct structure
        Expected: rag_sources should be List[dict] with title, content, score fields
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "案主：我想轉職，需要準備履歷和面試技巧。",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我想轉職，需要準備履歷和面試技巧。",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify complete response schema
            assert "summary" in data
            assert "alerts" in data
            assert "suggestions" in data
            assert "time_range" in data
            assert "timestamp" in data
            assert "rag_sources" in data  # NEW FIELD

            # Verify rag_sources schema
            assert isinstance(data["rag_sources"], list)

            # If sources exist, validate each source structure
            for source in data["rag_sources"]:
                assert "title" in source, "Source missing 'title' field"
                assert "content" in source, "Source missing 'content' field"
                assert "score" in source, "Source missing 'score' field"

                # Validate types
                assert isinstance(source["title"], str)
                assert isinstance(source["content"], str)
                assert isinstance(source["score"], (int, float))

                # Validate score range
                assert (
                    0 <= source["score"] <= 1
                ), f"Score out of range: {source['score']}"

                # Validate content is not empty
                assert len(source["content"]) > 0, "Source content is empty"

    @skip_without_gcp
    def test_rag_integration_performance(self):
        """Test 6: Verify API performance with RAG integration

        Scenario: RAG query should not slow down API too much
        Expected: API should respond within 5 seconds (including RAG query)
        """
        import time

        with TestClient(app) as client:
            start_time = time.time()

            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "案主：我想轉職，但不知道怎麼寫履歷。",
                    "speakers": [
                        {"speaker": "client", "text": "我想轉職，但不知道怎麼寫履歷。"}
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            elapsed_time = time.time() - start_time

            assert response.status_code == 200

            # API should respond within 5 seconds (including RAG query)
            assert elapsed_time < 5.0, f"API too slow: {elapsed_time:.2f}s"

            data = response.json()
            assert "rag_sources" in data

    @skip_without_gcp
    def test_rag_top_k_limit(self):
        """Test 7: Verify RAG returns limited number of sources

        Scenario: RAG should return top_k=3 most relevant sources
        Expected: rag_sources should have at most 3 items
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "案主：我想了解職涯規劃、履歷撰寫、面試技巧、求職策略等所有相關知識。",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我想了解職涯規劃、履歷撰寫、面試技巧、求職策略等所有相關知識。",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert "rag_sources" in data

            # Should return at most 3 sources (top_k=3)
            assert len(data["rag_sources"]) <= 3, "Too many RAG sources returned"

    @skip_without_gcp
    def test_rag_similarity_threshold(self):
        """Test 8: Verify RAG respects similarity threshold

        Scenario: Only high-quality matches should be returned
        Expected: All returned sources should have score >= 0.7 (similarity_threshold)
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "案主：我想轉職到科技業。",
                    "speakers": [{"speaker": "client", "text": "我想轉職到科技業。"}],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert "rag_sources" in data

            # All returned sources should meet similarity threshold
            for source in data["rag_sources"]:
                assert (
                    source["score"] >= 0.7
                ), f"Source score below threshold: {source['score']}"
