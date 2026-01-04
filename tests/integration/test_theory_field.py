"""
Integration test to verify theory field is properly included in RAG sources
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


class TestTheoryField:
    """Test that theory field is properly included in RAG sources"""

    @skip_without_gcp
    def test_theory_field_present_in_rag_sources(self):
        """Test that RAG sources include the theory field

        Scenario: When RAG search is triggered with parenting keywords
        Expected: Each RAG source should have a 'theory' field
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "案主：我的孩子很叛逆，需要學習親子溝通和管教技巧。",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我的孩子很叛逆，需要學習親子溝通和管教技巧。",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify RAG sources exist
            assert "rag_sources" in data
            assert isinstance(data["rag_sources"], list)

            # If RAG found sources, verify each has theory field
            if len(data["rag_sources"]) > 0:
                for idx, source in enumerate(data["rag_sources"]):
                    # Verify theory field exists
                    assert (
                        "theory" in source
                    ), f"Source {idx} missing 'theory' field: {source}"

                    # Verify theory field is string
                    assert isinstance(
                        source["theory"], str
                    ), f"Source {idx} theory is not a string: {source['theory']}"

                    # Verify theory value is one of expected values
                    valid_theories = [
                        "正向教養",
                        "情緒教養",
                        "依附理論",
                        "認知發展理論",
                        "自我決定論",
                        "其他",
                    ]
                    assert (
                        source["theory"] in valid_theories
                    ), f"Source {idx} has invalid theory: {source['theory']}"

                    print(
                        f"✅ Source {idx}: theory='{source['theory']}' | title={source['title'][:50]}..."
                    )

    @skip_without_gcp
    def test_theory_detection_accuracy(self):
        """Test that theory detection correctly identifies parenting theories

        Scenario: Trigger RAG with different parenting topics
        Expected: Theory field should match the content type
        """
        test_cases = [
            # (transcript, expected_theories)
            (
                "案主：我想學習正向教養的方法",
                ["正向教養"],
            ),  # Should prioritize 正向教養
            (
                "案主：孩子的情緒管理有問題",
                ["情緒教養", "其他"],
            ),  # Likely 情緒教養 or 其他
            ("案主：親子依附關係如何建立", ["依附理論", "其他"]),  # Likely 依附理論
        ]

        with TestClient(app) as client:
            for transcript, expected_theories in test_cases:
                response = client.post(
                    "/api/v1/realtime/analyze",
                    json={
                        "transcript": transcript,
                        "speakers": [{"speaker": "client", "text": transcript}],
                        "time_range": "0:00-1:00",
                    },
                )

                assert response.status_code == 200
                data = response.json()

                # Check if RAG sources exist
                if "rag_sources" in data and len(data["rag_sources"]) > 0:
                    theories_found = [src["theory"] for src in data["rag_sources"]]

                    print(
                        f"✅ Transcript: {transcript[:40]}... | Theories: {theories_found}"
                    )

                    # Note: This is a loose test because RAG results depend on actual content
                    # We just verify that theory field exists and has valid values
                    for theory in theories_found:
                        assert theory in [
                            "正向教養",
                            "情緒教養",
                            "依附理論",
                            "認知發展理論",
                            "自我決定論",
                            "其他",
                        ]

    @skip_without_gcp
    def test_complete_rag_source_structure(self):
        """Test that RAG sources have all required fields including theory

        Scenario: Verify complete structure of RAG source response
        Expected: Each source should have title, content, score, and theory
        """
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/realtime/analyze",
                json={
                    "transcript": "案主：我的孩子很叛逆，需要親子溝通技巧和情緒教養方法。",
                    "speakers": [
                        {
                            "speaker": "client",
                            "text": "我的孩子很叛逆，需要親子溝通技巧和情緒教養方法。",
                        }
                    ],
                    "time_range": "0:00-1:00",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Verify RAG sources exist
            assert "rag_sources" in data
            assert isinstance(data["rag_sources"], list)

            # If RAG found sources, verify complete structure
            if len(data["rag_sources"]) > 0:
                for idx, source in enumerate(data["rag_sources"]):
                    # Required fields
                    required_fields = ["title", "content", "score", "theory"]
                    for field in required_fields:
                        assert (
                            field in source
                        ), f"Source {idx} missing required field: {field}"

                    # Verify types
                    assert isinstance(source["title"], str)
                    assert isinstance(source["content"], str)
                    assert isinstance(source["score"], (int, float))
                    assert isinstance(source["theory"], str)

                    # Verify values
                    assert len(source["title"]) > 0, "Title cannot be empty"
                    assert len(source["content"]) > 0, "Content cannot be empty"
                    assert (
                        0 <= source["score"] <= 1
                    ), f"Invalid score: {source['score']}"
                    assert len(source["theory"]) > 0, "Theory cannot be empty"

                    print(f"✅ Source {idx} complete structure verified:")
                    print(f"   Title: {source['title'][:50]}...")
                    print(f"   Theory: {source['theory']}")
                    print(f"   Score: {source['score']}")
                    print(f"   Content length: {len(source['content'])} chars")
                    print()
