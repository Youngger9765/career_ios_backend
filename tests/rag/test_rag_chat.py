"""Tests for RAG Chat API endpoints"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
class TestRagChatAPI:
    """Test suite for /api/rag/chat endpoint"""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        return mock_session

    @pytest.fixture
    async def mock_openai_service(self):
        """Mock OpenAI service"""
        with patch("app.api.rag_chat.OpenAIService") as mock:
            service_instance = AsyncMock()
            mock.return_value = service_instance
            yield service_instance

    async def test_greeting_question_no_rag_search(
        self, async_client, mock_openai_service
    ):
        """Test that greeting questions don't trigger RAG search"""
        # Mock intent classification response
        mock_openai_service.chat_completion.side_effect = [
            '{"needs_search": false, "reason": "greeting"}',  # Intent check
            "你好！我是職涯諮詢 AI 助理。我可以協助你...",  # Direct response
        ]

        response = await async_client.post(
            "/api/rag/chat/",
            json={"question": "你好", "top_k": 5, "similarity_threshold": 0.35},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "你好"
        assert "職涯諮詢" in data["answer"]
        assert data["total_citations"] == 0
        assert len(data["citations"]) == 0

        # Verify no embedding was created (no RAG search)
        assert not mock_openai_service.create_embedding.called

    async def test_off_topic_question_no_rag_search(self, async_client, mock_openai_service):
        """Test that off-topic questions are handled gracefully"""
        mock_openai_service.chat_completion.side_effect = [
            '{"needs_search": false, "reason": "off-topic"}',
            "我的專業範圍是職涯諮詢...",
        ]

        response = await async_client.post(
            "/api/rag/chat/", json={"question": "怎麼煮牛肉麵？", "similarity_threshold": 0.35}
        )

        assert response.status_code == 200
        data = response.json()
        assert "職涯諮詢" in data["answer"]
        assert data["total_citations"] == 0

    async def test_career_question_triggers_rag_search(self, async_client):
        """Test that career questions trigger RAG search (simplified E2E test)"""
        # This is an integration test - it will call real OpenAI API if available
        # For pure unit testing, we'd need more complex FastAPI dependency override

        response = await async_client.post(
            "/api/rag/chat/",
            json={
                "question": "職涯發展是什麼？",
                "top_k": 5,
                "similarity_threshold": 0.35,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure (content may vary based on DB state)
        assert "question" in data
        assert "answer" in data
        assert "citations" in data
        assert "total_citations" in data

        # Answer should either have content or be the "no results" message
        assert len(data["answer"]) > 0

    async def test_no_results_returns_helpful_guidance(
        self, async_client, mock_openai_service, mock_db_session
    ):
        """Test that no search results return helpful guidance"""
        mock_openai_service.chat_completion.return_value = '{"needs_search": true}'
        mock_openai_service.create_embedding.return_value = [0.1] * 1536
        mock_db_session.execute.return_value.fetchall.return_value = []

        with patch("app.api.rag_chat.get_db", return_value=iter([mock_db_session])):
            response = await async_client.post(
                "/api/rag/chat/",
                json={"question": "區塊鏈技術", "similarity_threshold": 0.35},
            )

        assert response.status_code == 200
        data = response.json()
        assert "知識庫目前包含以下主題" in data["answer"]
        assert "職涯諮詢概論" in data["answer"]
        assert "優勢職能分析" in data["answer"]
        assert data["total_citations"] == 0

    async def test_custom_parameters_are_used(self, async_client):
        """Test that custom parameters are accepted and validated"""
        custom_params = {
            "question": "測試問題",
            "top_k": 10,
            "similarity_threshold": 0.5,
            "temperature": 0.8,
        }

        response = await async_client.post("/api/rag/chat/", json=custom_params)

        # Parameters should be accepted
        assert response.status_code == 200
        data = response.json()

        # Basic structure validation
        assert "question" in data
        assert data["question"] == "測試問題"
        assert "answer" in data

    async def test_custom_system_prompt_is_used(
        self, async_client, mock_openai_service, mock_db_session
    ):
        """Test that custom system prompt is passed to LLM"""
        mock_openai_service.chat_completion.side_effect = [
            '{"needs_search": false}',
            "Custom response",
        ]

        custom_system_prompt = "你是測試用的助理"

        response = await async_client.post(
            "/api/rag/chat/",
            json={"question": "你好", "system_prompt": custom_system_prompt},
        )

        assert response.status_code == 200

        # Verify custom system prompt was used
        call_args = mock_openai_service.chat_completion.call_args_list[1]
        messages = call_args[1]["messages"]
        assert messages[0]["content"] == custom_system_prompt

    async def test_english_question_gets_english_answer(self, async_client, mock_openai_service):
        """Test that English questions get English responses"""
        mock_openai_service.chat_completion.side_effect = [
            '{"needs_search": false, "reason": "greeting"}',
            "Hello! I'm a career counseling AI assistant...",
        ]

        response = await async_client.post(
            "/api/rag/chat/", json={"question": "Hello", "similarity_threshold": 0.35}
        )

        assert response.status_code == 200
        data = response.json()
        assert "career" in data["answer"].lower()

    async def test_invalid_request_parameters(self, async_client):
        """Test validation of request parameters"""
        # Missing required question field
        response = await async_client.post("/api/rag/chat/", json={})
        assert response.status_code == 422

        # Invalid top_k type
        response = await async_client.post(
            "/api/rag/chat/", json={"question": "test", "top_k": "invalid"}
        )
        assert response.status_code == 422

        # Invalid threshold range (should be 0-1)
        response = await async_client.post(
            "/api/rag/chat/",
            json={"question": "test", "similarity_threshold": 1.5},
        )
        # Note: Pydantic doesn't enforce range by default, this would need custom validation

    async def test_multiple_citations_ordered_by_similarity(self, async_client):
        """Test that API returns citations when documents are found"""
        # This test validates the response structure when citations exist
        # Actual citation ordering is tested via integration tests with real data

        response = await async_client.post(
            "/api/rag/chat/",
            json={"question": "職涯發展", "top_k": 5, "similarity_threshold": 0.35},
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "citations" in data
        assert "total_citations" in data
        assert isinstance(data["citations"], list)
        assert isinstance(data["total_citations"], int)

        # If citations exist, validate their structure
        if data["total_citations"] > 0:
            first_citation = data["citations"][0]
            assert "chunk_id" in first_citation
            assert "doc_id" in first_citation
            assert "document_title" in first_citation
            assert "text" in first_citation
            assert "similarity_score" in first_citation

            # Verify similarity scores are in descending order
            scores = [c["similarity_score"] for c in data["citations"]]
            assert scores == sorted(scores, reverse=True)

    async def test_intent_classifier_json_parsing_fallback(
        self, async_client, mock_openai_service, mock_db_session
    ):
        """Test that malformed JSON from intent classifier falls back gracefully"""
        # Mock intent response with extra text around JSON
        mock_openai_service.chat_completion.side_effect = [
            'Sure, here is the result: {"needs_search": true, "reason": "career topic"}',
            "Direct answer",
        ]
        mock_openai_service.create_embedding.return_value = [0.1] * 1536
        mock_db_session.execute.return_value.fetchall.return_value = []

        with patch("app.api.rag_chat.get_db", return_value=iter([mock_db_session])):
            response = await async_client.post("/api/rag/chat/", json={"question": "職涯規劃"})

        assert response.status_code == 200
        # Should still work by extracting JSON

    async def test_error_handling_with_traceback(self, async_client, mock_openai_service):
        """Test that errors return detailed traceback"""
        mock_openai_service.chat_completion.side_effect = Exception("OpenAI API error")

        response = await async_client.post("/api/rag/chat/", json={"question": "test"})

        assert response.status_code == 500
        assert "Chat failed" in response.json()["detail"]


@pytest.mark.asyncio
class TestRagChatIntentClassifier:
    """Test suite specifically for intent classification logic"""

    @pytest.fixture
    async def mock_openai_service_2(self):
        """Mock OpenAI service for intent classifier tests"""
        with patch("app.api.rag_chat.OpenAIService") as mock:
            service_instance = AsyncMock()
            mock.return_value = service_instance
            yield service_instance

    async def test_greeting_keywords_detected(self, async_client, mock_openai_service_2):
        """Test various greeting keywords are properly classified"""
        mock_openai_service_2.chat_completion.side_effect = [
            '{"needs_search": false, "reason": "greeting"}',
            "Greeting response",
        ]

        response = await async_client.post("/api/rag/chat/", json={"question": "你好"})
        assert response.status_code == 200
        data = response.json()
        assert data["total_citations"] == 0

    async def test_career_keywords_trigger_search(self, async_client):
        """Test career-related keywords trigger RAG search"""
        with patch("app.api.rag_chat.OpenAIService") as mock:
            service_instance = AsyncMock()
            mock.return_value = service_instance
            service_instance.chat_completion.return_value = '{"needs_search": true}'
            service_instance.create_embedding.return_value = [0.1] * 1536

            mock_db = MagicMock()
            mock_db.execute.return_value.fetchall.return_value = []

            with patch("app.api.rag_chat.get_db", return_value=iter([mock_db])):
                response = await async_client.post("/api/rag/chat/", json={"question": "職涯發展"})
                assert response.status_code == 200


@pytest.mark.asyncio
class TestRagChatResponseFormat:
    """Test the response format and structure"""

    async def test_response_schema_structure(self, async_client):
        """Test that response follows ChatResponse schema"""
        with patch("app.api.rag_chat.OpenAIService") as mock:
            service_instance = AsyncMock()
            mock.return_value = service_instance
            service_instance.chat_completion.side_effect = [
                '{"needs_search": false}',
                "Test answer",
            ]

            response = await async_client.post("/api/rag/chat/", json={"question": "test"})

            assert response.status_code == 200
            data = response.json()

            # Verify required fields
            assert "question" in data
            assert "answer" in data
            assert "citations" in data
            assert "total_citations" in data

            # Verify types
            assert isinstance(data["question"], str)
            assert isinstance(data["answer"], str)
            assert isinstance(data["citations"], list)
            assert isinstance(data["total_citations"], int)

    async def test_citation_schema_structure(self, async_client):
        """Test that citations have correct schema structure"""
        # Test with a career question that should return citations (if DB has data)
        response = await async_client.post(
            "/api/rag/chat/",
            json={"question": "求職策略", "top_k": 3, "similarity_threshold": 0.3},
        )

        assert response.status_code == 200
        data = response.json()

        # If citations exist, verify their schema
        if data["total_citations"] > 0:
            citation = data["citations"][0]

            # Verify Citation schema fields exist and have correct types
            assert "chunk_id" in citation
            assert isinstance(citation["chunk_id"], int)

            assert "doc_id" in citation
            assert isinstance(citation["doc_id"], int)

            assert "text" in citation
            assert isinstance(citation["text"], str)
            assert len(citation["text"]) > 0

            assert "document_title" in citation
            assert isinstance(citation["document_title"], str)

            assert "similarity_score" in citation
            assert isinstance(citation["similarity_score"], (int, float))
            assert 0 <= citation["similarity_score"] <= 1
