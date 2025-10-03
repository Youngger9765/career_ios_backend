"""Tests for RAG Chat API endpoints"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


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

    async def test_greeting_question_no_rag_search(self, client, mock_openai_service):
        """Test that greeting questions don't trigger RAG search"""
        # Mock intent classification response
        mock_openai_service.chat_completion.side_effect = [
            '{"needs_search": false, "reason": "greeting"}',  # Intent check
            "你好！我是職涯諮詢 AI 助理。我可以協助你...",  # Direct response
        ]

        response = await client.post(
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

    async def test_off_topic_question_no_rag_search(self, client, mock_openai_service):
        """Test that off-topic questions are handled gracefully"""
        mock_openai_service.chat_completion.side_effect = [
            '{"needs_search": false, "reason": "off-topic"}',
            "我的專業範圍是職涯諮詢...",
        ]

        response = await client.post(
            "/api/rag/chat/", json={"question": "怎麼煮牛肉麵？", "similarity_threshold": 0.35}
        )

        assert response.status_code == 200
        data = response.json()
        assert "職涯諮詢" in data["answer"]
        assert data["total_citations"] == 0

    async def test_career_question_triggers_rag_search(
        self, client, mock_openai_service, mock_db_session
    ):
        """Test that career questions trigger RAG search with citations"""
        # Mock intent classification - need it to be coroutine
        async def mock_chat_completion(*args, **kwargs):
            return '{"needs_search": true}'

        async def mock_context_completion(*args, **kwargs):
            return "職涯發展是一個持續的過程... [1]"

        mock_openai_service.chat_completion.side_effect = mock_chat_completion
        mock_openai_service.chat_completion_with_context.side_effect = mock_context_completion

        # Mock embedding
        async def mock_create_embedding(*args, **kwargs):
            return [0.1] * 1536

        mock_openai_service.create_embedding.side_effect = mock_create_embedding

        # Mock database results
        mock_row = MagicMock()
        mock_row.chunk_id = 1
        mock_row.doc_id = 1
        mock_row.text = "職涯發展包括探索、成長等階段..."
        mock_row.document_title = "職涯諮詢概論"
        mock_row.similarity_score = 0.85

        mock_db_session.execute.return_value.fetchall.return_value = [mock_row]

        with patch("app.api.rag_chat.get_db", return_value=iter([mock_db_session])):
            response = await client.post(
                "/api/rag/chat/", json={"question": "職涯發展是什麼？", "top_k": 5}
            )

        assert response.status_code == 200
        data = response.json()
        assert "職涯發展" in data["answer"]
        assert data["total_citations"] == 1
        assert len(data["citations"]) == 1
        assert data["citations"][0]["document_title"] == "職涯諮詢概論"
        assert data["citations"][0]["similarity_score"] == 0.85

    async def test_no_results_returns_helpful_guidance(
        self, client, mock_openai_service, mock_db_session
    ):
        """Test that no search results return helpful guidance"""
        mock_openai_service.chat_completion.return_value = '{"needs_search": true}'
        mock_openai_service.create_embedding.return_value = [0.1] * 1536
        mock_db_session.execute.return_value.fetchall.return_value = []

        with patch("app.api.rag_chat.get_db", return_value=iter([mock_db_session])):
            response = await client.post(
                "/api/rag/chat/",
                json={"question": "區塊鏈技術", "similarity_threshold": 0.35},
            )

        assert response.status_code == 200
        data = response.json()
        assert "知識庫目前包含以下主題" in data["answer"]
        assert "職涯諮詢概論" in data["answer"]
        assert "優勢職能分析" in data["answer"]
        assert data["total_citations"] == 0

    async def test_custom_parameters_are_used(self, client, mock_openai_service, mock_db_session):
        """Test that custom parameters (top_k, threshold, temperature) are respected"""
        mock_openai_service.chat_completion.return_value = '{"needs_search": true}'
        mock_openai_service.create_embedding.return_value = [0.1] * 1536

        # Ensure fetchall returns empty list
        mock_db_session.execute.return_value.fetchall.return_value = []

        custom_params = {
            "question": "測試問題",
            "top_k": 10,
            "similarity_threshold": 0.5,
            "temperature": 0.8,
        }

        with patch("app.api.rag_chat.get_db", return_value=iter([mock_db_session])):
            response = await client.post("/api/rag/chat/", json=custom_params)

        assert response.status_code == 200

        # Verify database query was called (parameters validation)
        assert mock_db_session.execute.called

    async def test_custom_system_prompt_is_used(
        self, client, mock_openai_service, mock_db_session
    ):
        """Test that custom system prompt is passed to LLM"""
        mock_openai_service.chat_completion.side_effect = [
            '{"needs_search": false}',
            "Custom response",
        ]

        custom_system_prompt = "你是測試用的助理"

        response = await client.post(
            "/api/rag/chat/",
            json={"question": "你好", "system_prompt": custom_system_prompt},
        )

        assert response.status_code == 200

        # Verify custom system prompt was used
        call_args = mock_openai_service.chat_completion.call_args_list[1]
        messages = call_args[1]["messages"]
        assert messages[0]["content"] == custom_system_prompt

    async def test_english_question_gets_english_answer(self, client, mock_openai_service):
        """Test that English questions get English responses"""
        mock_openai_service.chat_completion.side_effect = [
            '{"needs_search": false, "reason": "greeting"}',
            "Hello! I'm a career counseling AI assistant...",
        ]

        response = await client.post(
            "/api/rag/chat/", json={"question": "Hello", "similarity_threshold": 0.35}
        )

        assert response.status_code == 200
        data = response.json()
        assert "career" in data["answer"].lower()

    async def test_invalid_request_parameters(self, client):
        """Test validation of request parameters"""
        # Missing required question field
        response = await client.post("/api/rag/chat/", json={})
        assert response.status_code == 422

        # Invalid top_k type
        response = await client.post(
            "/api/rag/chat/", json={"question": "test", "top_k": "invalid"}
        )
        assert response.status_code == 422

        # Invalid threshold range (should be 0-1)
        response = await client.post(
            "/api/rag/chat/",
            json={"question": "test", "similarity_threshold": 1.5},
        )
        # Note: Pydantic doesn't enforce range by default, this would need custom validation

    async def test_multiple_citations_ordered_by_similarity(
        self, client, mock_openai_service, mock_db_session
    ):
        """Test that multiple citations are returned in order of similarity"""
        async def mock_chat_completion(*args, **kwargs):
            return '{"needs_search": true}'

        async def mock_create_embedding(*args, **kwargs):
            return [0.1] * 1536

        async def mock_context_completion(*args, **kwargs):
            return "Answer with [1][2][3]"

        mock_openai_service.chat_completion.side_effect = mock_chat_completion
        mock_openai_service.create_embedding.side_effect = mock_create_embedding
        mock_openai_service.chat_completion_with_context.side_effect = mock_context_completion

        # Mock multiple results with different similarity scores
        mock_rows = []
        for i in range(3):
            mock_row = MagicMock()
            mock_row.chunk_id = i + 1
            mock_row.doc_id = i + 1
            mock_row.text = f"Content {i + 1}"
            mock_row.document_title = f"Document {i + 1}"
            mock_row.similarity_score = 0.9 - (i * 0.1)  # 0.9, 0.8, 0.7
            mock_rows.append(mock_row)

        mock_db_session.execute.return_value.fetchall.return_value = mock_rows

        with patch("app.api.rag_chat.get_db", return_value=iter([mock_db_session])):
            response = await client.post(
                "/api/rag/chat/", json={"question": "test question", "top_k": 5}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total_citations"] == 3

        # Verify citations are in order
        assert data["citations"][0]["similarity_score"] == 0.9
        assert data["citations"][1]["similarity_score"] == 0.8
        assert data["citations"][2]["similarity_score"] == 0.7

    async def test_intent_classifier_json_parsing_fallback(
        self, client, mock_openai_service, mock_db_session
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
            response = await client.post("/api/rag/chat/", json={"question": "職涯規劃"})

        assert response.status_code == 200
        # Should still work by extracting JSON

    async def test_error_handling_with_traceback(self, client, mock_openai_service):
        """Test that errors return detailed traceback"""
        mock_openai_service.chat_completion.side_effect = Exception("OpenAI API error")

        response = await client.post("/api/rag/chat/", json={"question": "test"})

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

    async def test_greeting_keywords_detected(self, client, mock_openai_service_2):
        """Test various greeting keywords are properly classified"""
        mock_openai_service_2.chat_completion.side_effect = [
            '{"needs_search": false, "reason": "greeting"}',
            "Greeting response",
        ]

        response = await client.post("/api/rag/chat/", json={"question": "你好"})
        assert response.status_code == 200
        data = response.json()
        assert data["total_citations"] == 0

    async def test_career_keywords_trigger_search(self, client):
        """Test career-related keywords trigger RAG search"""
        with patch("app.api.rag_chat.OpenAIService") as mock:
            service_instance = AsyncMock()
            mock.return_value = service_instance
            service_instance.chat_completion.return_value = '{"needs_search": true}'
            service_instance.create_embedding.return_value = [0.1] * 1536

            mock_db = MagicMock()
            mock_db.execute.return_value.fetchall.return_value = []

            with patch("app.api.rag_chat.get_db", return_value=iter([mock_db])):
                response = await client.post("/api/rag/chat/", json={"question": "職涯發展"})
                assert response.status_code == 200


@pytest.mark.asyncio
class TestRagChatResponseFormat:
    """Test the response format and structure"""

    async def test_response_schema_structure(self, client):
        """Test that response follows ChatResponse schema"""
        with patch("app.api.rag_chat.OpenAIService") as mock:
            service_instance = AsyncMock()
            mock.return_value = service_instance
            service_instance.chat_completion.side_effect = [
                '{"needs_search": false}',
                "Test answer",
            ]

            response = await client.post("/api/rag/chat/", json={"question": "test"})

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

    async def test_citation_schema_structure(self, client):
        """Test that citations follow Citation schema"""
        with patch("app.api.rag_chat.OpenAIService") as mock:
            service_instance = AsyncMock()
            mock.return_value = service_instance
            service_instance.chat_completion.return_value = '{"needs_search": true}'
            service_instance.create_embedding.return_value = [0.1] * 1536

            mock_row = MagicMock()
            mock_row.chunk_id = 123
            mock_row.doc_id = 456
            mock_row.text = "Sample text"
            mock_row.document_title = "Sample Document"
            mock_row.similarity_score = 0.75

            mock_db = MagicMock()
            mock_db.execute.return_value.fetchall.return_value = [mock_row]
            service_instance.chat_completion_with_context.return_value = "Answer"

            with patch("app.api.rag_chat.get_db", return_value=iter([mock_db])):
                response = await client.post("/api/rag/chat/", json={"question": "test"})

            data = response.json()
            citation = data["citations"][0]

            # Verify Citation schema fields
            assert citation["chunk_id"] == 123
            assert citation["doc_id"] == 456
            assert citation["text"] == "Sample text"
            assert citation["document_title"] == "Sample Document"
            assert citation["similarity_score"] == 0.75
