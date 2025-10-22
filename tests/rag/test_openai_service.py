"""Unit tests for OpenAI service"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.openai_service import OpenAIService


class TestOpenAIService:
    """Test suite for OpenAIService"""

    @pytest.mark.asyncio
    async def test_create_embedding_returns_correct_dimensions(self):
        """Test that create_embedding returns 1536-dimensional vector"""
        service = OpenAIService()

        with patch.object(
            service.client.embeddings,
            "create",
            new_callable=AsyncMock,
            return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 1536)]),
        ):
            embedding = await service.create_embedding("test text")

            assert len(embedding) == 1536
            assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_create_embedding_with_empty_text_raises_error(self):
        """Test that empty text raises ValueError"""
        service = OpenAIService()

        with pytest.raises(ValueError, match="Text cannot be empty"):
            await service.create_embedding("")

    @pytest.mark.asyncio
    async def test_create_embeddings_batch(self):
        """Test creating embeddings for multiple texts"""
        service = OpenAIService()
        texts = ["text 1", "text 2", "text 3"]

        with patch.object(
            service.client.embeddings,
            "create",
            new_callable=AsyncMock,
            return_value=MagicMock(
                data=[
                    MagicMock(embedding=[0.1] * 1536),
                    MagicMock(embedding=[0.2] * 1536),
                    MagicMock(embedding=[0.3] * 1536),
                ]
            ),
        ):
            embeddings = await service.create_embeddings_batch(texts)

            assert len(embeddings) == 3
            assert all(len(emb) == 1536 for emb in embeddings)

    @pytest.mark.asyncio
    async def test_chat_completion_returns_text(self):
        """Test chat completion returns text response"""
        service = OpenAIService()
        messages = [{"role": "user", "content": "Hello"}]

        mock_response = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Hello! How can I help?"))]
        )

        with patch.object(
            service.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            response = await service.chat_completion(messages)

            assert response == "Hello! How can I help?"
            assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_chat_completion_with_context(self):
        """Test chat completion with context from RAG"""
        service = OpenAIService()
        question = "What is TDD?"
        context = "TDD stands for Test-Driven Development."

        mock_response = MagicMock(
            choices=[MagicMock(message=MagicMock(content="TDD is Test-Driven Development"))]
        )

        with patch.object(
            service.client.chat.completions,
            "create",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_create:
            response = await service.chat_completion_with_context(question, context)

            # Verify context was included in the prompt
            call_args = mock_create.call_args
            messages = call_args.kwargs["messages"]
            assert any(context in str(msg) for msg in messages)
            assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_openai_api_error_handling(self):
        """Test that OpenAI API errors are properly handled"""
        service = OpenAIService()

        with patch.object(
            service.client.embeddings,
            "create",
            new_callable=AsyncMock,
            side_effect=Exception("API Error"),
        ):
            with pytest.raises(Exception, match="API Error"):
                await service.create_embedding("test")
