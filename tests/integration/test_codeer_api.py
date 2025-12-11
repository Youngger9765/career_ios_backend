"""
Integration tests for Codeer API Client
TDD - RED Phase: These tests will fail until implementation is complete
"""

import pytest

from app.services.codeer_client import CodeerAPIError, CodeerClient


@pytest.fixture
async def codeer_client():
    """
    Fixture providing CodeerClient instance with async context manager

    Yields:
        CodeerClient: Configured client instance
    """
    async with CodeerClient() as client:
        yield client


@pytest.fixture
async def test_chat(codeer_client):
    """
    Fixture providing a test chat instance for message-related tests

    Yields:
        Dict: Chat object with id and other properties
    """
    chat = await codeer_client.create_chat(name="Test Chat for Integration Tests")
    yield chat
    # Cleanup is optional - chats can be kept or deleted based on API capabilities


class TestCodeerClientBasics:
    """Test basic API operations and client lifecycle"""

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self):
        """Verify async context manager properly initializes and closes connection"""
        # Act & Assert
        async with CodeerClient() as client:
            # Client should be usable within context
            assert client is not None
            # Verify connection by making a simple API call
            agents = await client.list_published_agents()
            assert isinstance(agents, list)

        # After exiting context, client should be closed
        # Any subsequent calls should fail gracefully

    @pytest.mark.asyncio
    async def test_invalid_api_key_raises_error(self):
        """Verify that invalid API key raises appropriate error"""
        # Act & Assert - pass invalid API key to test authentication failure
        async with CodeerClient(api_key="invalid_key_12345") as client:
            with pytest.raises(CodeerAPIError) as exc_info:
                await client.list_published_agents()

        # Verify error contains useful information
        assert (
            "authentication" in str(exc_info.value).lower()
            or "api key" in str(exc_info.value).lower()
            or "unauthorized" in str(exc_info.value).lower()
        )


class TestCodeerAgents:
    """Test agent-related API endpoints"""

    @pytest.mark.asyncio
    async def test_list_published_agents_returns_list(self, codeer_client):
        """Verify we can retrieve published agents from Codeer API"""
        # Act
        agents = await codeer_client.list_published_agents()

        # Assert
        assert isinstance(agents, list), "Should return a list of agents"
        assert len(agents) >= 0, "Should return zero or more agents"

    @pytest.mark.asyncio
    async def test_list_published_agents_structure(self, codeer_client):
        """Verify agent objects have expected fields"""
        # Act
        agents = await codeer_client.list_published_agents()

        # Assert
        if agents:  # If there are agents available
            agent = agents[0]
            assert "id" in agent, "Agent should have id field"
            assert "name" in agent, "Agent should have name field"
            assert isinstance(agent["id"], str), "Agent id should be string"
            assert isinstance(agent["name"], str), "Agent name should be string"

    @pytest.mark.asyncio
    async def test_list_published_agents_shows_llm_model(self, codeer_client):
        """Verify agent objects include llm_model field (NEW: 2025-12-11)"""
        # Act
        agents = await codeer_client.list_published_agents()

        # Assert
        if agents:  # If there are agents available
            agent = agents[0]
            assert "llm_model" in agent, "Agent should have llm_model field"
            assert isinstance(
                agent["llm_model"], str
            ), "Agent llm_model should be string"
            assert len(agent["llm_model"]) > 0, "Agent llm_model should not be empty"
            # Example format: "openai/gpt-5-mini;gpt-5 mini" or similar


class TestCodeerChats:
    """Test chat management endpoints"""

    @pytest.mark.asyncio
    async def test_create_chat_with_name(self, codeer_client):
        """Verify we can create a new chat with given name"""
        # Arrange
        chat_name = "Test Chat - Integration Test"

        # Act
        chat = await codeer_client.create_chat(name=chat_name)

        # Assert
        assert isinstance(chat, dict), "Should return chat object"
        assert "id" in chat, "Chat should have id field"
        assert isinstance(chat["id"], int), "Chat id should be integer"
        assert "name" in chat, "Chat should have name field"
        assert chat["name"] == chat_name, "Chat name should match requested name"

    @pytest.mark.asyncio
    async def test_create_chat_with_agent(self, codeer_client):
        """Verify we can create a chat with specific agent"""
        # Arrange - get first available agent
        agents = await codeer_client.list_published_agents()
        if not agents:
            pytest.skip("No agents available for testing")

        agent_id = agents[0]["id"]
        chat_name = "Test Chat with Agent"

        # Act
        chat = await codeer_client.create_chat(name=chat_name, agent_id=agent_id)

        # Assert
        assert isinstance(chat, dict), "Should return chat object"
        assert "id" in chat, "Chat should have id"
        assert "agent_id" in chat or "agent" in chat, "Chat should reference agent"

    @pytest.mark.asyncio
    async def test_list_chats_returns_list(self, codeer_client):
        """Verify we can retrieve list of chats"""
        # Act
        chats = await codeer_client.list_chats()

        # Assert
        assert isinstance(chats, list), "Should return list of chats"
        assert len(chats) >= 0, "Should return zero or more chats"

    @pytest.mark.asyncio
    async def test_list_chats_with_pagination(self, codeer_client):
        """Verify pagination parameters work correctly"""
        # Arrange - create multiple chats if needed
        await codeer_client.create_chat(name="Pagination Test Chat 1")
        await codeer_client.create_chat(name="Pagination Test Chat 2")

        # Act
        chats_limit_1 = await codeer_client.list_chats(limit=1)
        chats_limit_2 = await codeer_client.list_chats(limit=2)
        chats_offset_1 = await codeer_client.list_chats(limit=1, offset=1)

        # Assert
        assert len(chats_limit_1) <= 1, "Should respect limit=1"
        assert len(chats_limit_2) <= 2, "Should respect limit=2"
        assert isinstance(chats_offset_1, list), "Should handle offset parameter"

    @pytest.mark.asyncio
    async def test_list_chats_structure(self, codeer_client):
        """Verify chat objects have expected fields"""
        # Arrange - ensure at least one chat exists
        await codeer_client.create_chat(name="Structure Test Chat")

        # Act
        chats = await codeer_client.list_chats(limit=1)

        # Assert
        if chats:
            chat = chats[0]
            assert "id" in chat, "Chat should have id field"
            assert "name" in chat, "Chat should have name field"
            assert isinstance(chat["id"], int), "Chat id should be integer"


class TestCodeerMessages:
    """Test message-related endpoints"""

    @pytest.mark.asyncio
    async def test_list_chat_messages_for_new_chat(self, test_chat, codeer_client):
        """Verify we can list messages for a newly created chat (should be empty)"""
        # Act
        messages = await codeer_client.list_chat_messages(chat_id=test_chat["id"])

        # Assert
        assert isinstance(messages, list), "Should return list of messages"
        # New chat may have empty messages or system messages
        assert len(messages) >= 0, "Should handle empty message list"

    @pytest.mark.asyncio
    async def test_list_chat_messages_with_pagination(self, test_chat, codeer_client):
        """Verify message pagination parameters work"""
        # Act
        messages_limit_10 = await codeer_client.list_chat_messages(
            chat_id=test_chat["id"], limit=10
        )
        messages_limit_5 = await codeer_client.list_chat_messages(
            chat_id=test_chat["id"], limit=5
        )

        # Assert
        assert isinstance(messages_limit_10, list), "Should return list with limit=10"
        assert isinstance(messages_limit_5, list), "Should return list with limit=5"
        assert len(messages_limit_10) <= 10, "Should respect limit=10"
        assert len(messages_limit_5) <= 5, "Should respect limit=5"

    @pytest.mark.asyncio
    async def test_send_message_non_streaming(self, test_chat, codeer_client):
        """Verify we can send a message without streaming"""
        # Arrange
        message_text = "Hello, this is a test message"

        # Act
        response = await codeer_client.send_message(
            chat_id=test_chat["id"], message=message_text, stream=False
        )

        # Assert
        assert isinstance(response, dict), "Should return response dict"
        assert (
            "content" in response or "message" in response or "text" in response
        ), "Response should contain message content"

    @pytest.mark.asyncio
    async def test_send_message_streaming_with_callback(self, test_chat, codeer_client):
        """Verify SSE streaming works with callback function"""
        # Arrange
        message_text = "Tell me a short story"
        chunks_received = []

        def chunk_callback(chunk: str):
            """Callback to accumulate streaming chunks"""
            chunks_received.append(chunk)

        # Act
        response = await codeer_client.send_message(
            chat_id=test_chat["id"],
            message=message_text,
            stream=True,
            on_chunk=chunk_callback,
        )

        # Assert
        assert isinstance(response, dict), "Should return final response dict"
        assert len(chunks_received) > 0, "Should have received streaming chunks"
        assert all(
            isinstance(chunk, str) for chunk in chunks_received
        ), "All chunks should be strings"

        # Verify chunks form coherent response
        full_text = "".join(chunks_received)
        assert len(full_text) > 0, "Combined chunks should form non-empty text"

    @pytest.mark.asyncio
    async def test_send_message_with_agent_id(self, test_chat, codeer_client):
        """Verify we can send message with specific agent_id"""
        # Arrange
        agents = await codeer_client.list_published_agents()
        if not agents:
            pytest.skip("No agents available for testing")

        agent_id = agents[0]["id"]
        message_text = "Test message with agent"

        # Act
        response = await codeer_client.send_message(
            chat_id=test_chat["id"],
            message=message_text,
            stream=False,
            agent_id=agent_id,
        )

        # Assert
        assert isinstance(response, dict), "Should return response with agent"
        assert (
            "content" in response or "message" in response or "text" in response
        ), "Response should contain content"

    @pytest.mark.asyncio
    async def test_list_messages_after_sending(self, test_chat, codeer_client):
        """Verify sent messages appear in chat history"""
        # Arrange
        message_text = "Message for history test"

        # Act
        await codeer_client.send_message(
            chat_id=test_chat["id"], message=message_text, stream=False
        )
        messages = await codeer_client.list_chat_messages(chat_id=test_chat["id"])

        # Assert
        assert len(messages) > 0, "Should have messages after sending"
        # Verify message structure
        if messages:
            message = messages[0]
            assert (
                "content" in message or "text" in message or "message" in message
            ), "Message should have content field"


class TestCodeerErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_invalid_chat_id_raises_error(self, codeer_client):
        """Verify that invalid chat_id raises CodeerAPIError"""
        # Arrange
        invalid_chat_id = 99999999

        # Act & Assert
        with pytest.raises(CodeerAPIError) as exc_info:
            await codeer_client.send_message(
                chat_id=invalid_chat_id, message="Test message to non-existent chat"
            )

        # Verify error contains useful information
        error_msg = str(exc_info.value).lower()
        assert (
            "not found" in error_msg or "invalid" in error_msg or "404" in error_msg
        ), "Error should indicate chat not found"

    @pytest.mark.asyncio
    async def test_invalid_agent_id_raises_error(self, test_chat, codeer_client):
        """Verify that invalid agent_id raises appropriate error"""
        # Arrange
        invalid_agent_id = "non-existent-agent-id"

        # Act & Assert
        with pytest.raises(CodeerAPIError) as exc_info:
            await codeer_client.create_chat(name="Test Chat", agent_id=invalid_agent_id)

        # Error should indicate agent not found
        error_msg = str(exc_info.value).lower()
        assert (
            "agent" in error_msg or "not found" in error_msg or "invalid" in error_msg
        )

    @pytest.mark.asyncio
    async def test_empty_message_handling(self, test_chat, codeer_client):
        """Verify handling of empty message"""
        # Act & Assert - should either raise error or handle gracefully
        try:
            response = await codeer_client.send_message(
                chat_id=test_chat["id"], message=""
            )
            # If no error, response should still be valid
            assert isinstance(response, dict)
        except CodeerAPIError as e:
            # If error raised, it should be about empty message
            assert "empty" in str(e).lower() or "required" in str(e).lower()

    @pytest.mark.asyncio
    async def test_invalid_pagination_parameters(self, codeer_client):
        """Verify handling of invalid pagination parameters"""
        # Act - should handle gracefully or raise clear error
        try:
            chats = await codeer_client.list_chats(limit=-1)
            assert isinstance(chats, list)  # Should handle gracefully
        except CodeerAPIError as e:
            # If error raised, should be about invalid parameters
            assert "invalid" in str(e).lower() or "parameter" in str(e).lower()


class TestCodeerStreamingEdgeCases:
    """Test streaming-specific edge cases and scenarios"""

    @pytest.mark.asyncio
    async def test_streaming_without_callback(self, test_chat, codeer_client):
        """Verify streaming works even without callback function"""
        # Act
        response = await codeer_client.send_message(
            chat_id=test_chat["id"],
            message="Test streaming without callback",
            stream=True,
            on_chunk=None,  # No callback provided
        )

        # Assert
        assert isinstance(
            response, dict
        ), "Should still return response without callback"

    @pytest.mark.asyncio
    async def test_streaming_callback_exception_handling(
        self, test_chat, codeer_client
    ):
        """Verify that callback exceptions are handled gracefully"""

        # Arrange
        def failing_callback(chunk: str):
            """Callback that raises exception"""
            if len(chunk) > 10:
                raise ValueError("Simulated callback error")

        # Act & Assert - should handle callback error gracefully
        try:
            response = await codeer_client.send_message(
                chat_id=test_chat["id"],
                message="Test callback exception handling",
                stream=True,
                on_chunk=failing_callback,
            )
            # Should complete despite callback error
            assert isinstance(response, dict)
        except CodeerAPIError:
            # Or raise CodeerAPIError wrapping the callback error
            pass  # Either behavior is acceptable


class TestCodeerModelSelection:
    """Test multi-model support via get_codeer_agent_id()"""

    @pytest.mark.asyncio
    async def test_get_agent_id_claude_sonnet(self):
        """Verify claude-sonnet model returns correct agent ID"""
        from app.core.config import settings
        from app.services.codeer_client import get_codeer_agent_id

        # Act
        agent_id = get_codeer_agent_id("claude-sonnet")

        # Assert
        assert agent_id == settings.CODEER_AGENT_CLAUDE_SONNET
        assert len(agent_id) > 0, "Agent ID should not be empty"

    @pytest.mark.asyncio
    async def test_get_agent_id_claude_alias(self):
        """Verify 'claude' alias works for claude-sonnet"""
        from app.core.config import settings
        from app.services.codeer_client import get_codeer_agent_id

        # Act
        agent_id = get_codeer_agent_id("claude")

        # Assert
        assert agent_id == settings.CODEER_AGENT_CLAUDE_SONNET

    @pytest.mark.asyncio
    async def test_get_agent_id_gemini_flash(self):
        """Verify gemini-flash model returns correct agent ID"""
        from app.core.config import settings
        from app.services.codeer_client import get_codeer_agent_id

        # Act
        agent_id = get_codeer_agent_id("gemini-flash")

        # Assert
        assert agent_id == settings.CODEER_AGENT_GEMINI_FLASH
        assert len(agent_id) > 0, "Agent ID should not be empty"

    @pytest.mark.asyncio
    async def test_get_agent_id_gemini_alias(self):
        """Verify 'gemini' alias works for gemini-flash"""
        from app.core.config import settings
        from app.services.codeer_client import get_codeer_agent_id

        # Act
        agent_id = get_codeer_agent_id("gemini")

        # Assert
        assert agent_id == settings.CODEER_AGENT_GEMINI_FLASH

    @pytest.mark.asyncio
    async def test_get_agent_id_gpt5_mini(self):
        """Verify gpt5-mini model returns correct agent ID"""
        from app.core.config import settings
        from app.services.codeer_client import get_codeer_agent_id

        # Act
        agent_id = get_codeer_agent_id("gpt5-mini")

        # Assert
        assert agent_id == settings.CODEER_AGENT_GPT5_MINI
        assert len(agent_id) > 0, "Agent ID should not be empty"

    @pytest.mark.asyncio
    async def test_get_agent_id_gpt5_alias(self):
        """Verify 'gpt5' alias works for gpt5-mini"""
        from app.core.config import settings
        from app.services.codeer_client import get_codeer_agent_id

        # Act
        agent_id = get_codeer_agent_id("gpt5")

        # Assert
        assert agent_id == settings.CODEER_AGENT_GPT5_MINI

    @pytest.mark.asyncio
    async def test_get_agent_id_gpt_alias(self):
        """Verify 'gpt' alias works for gpt5-mini"""
        from app.core.config import settings
        from app.services.codeer_client import get_codeer_agent_id

        # Act
        agent_id = get_codeer_agent_id("gpt")

        # Assert
        assert agent_id == settings.CODEER_AGENT_GPT5_MINI

    @pytest.mark.asyncio
    async def test_get_agent_id_case_insensitive(self):
        """Verify model names are case-insensitive"""
        from app.core.config import settings
        from app.services.codeer_client import get_codeer_agent_id

        # Act
        agent_id_upper = get_codeer_agent_id("CLAUDE-SONNET")
        agent_id_mixed = get_codeer_agent_id("Gemini-Flash")
        agent_id_lower = get_codeer_agent_id("gpt5-mini")

        # Assert
        assert agent_id_upper == settings.CODEER_AGENT_CLAUDE_SONNET
        assert agent_id_mixed == settings.CODEER_AGENT_GEMINI_FLASH
        assert agent_id_lower == settings.CODEER_AGENT_GPT5_MINI

    @pytest.mark.asyncio
    async def test_get_agent_id_unsupported_model_with_default(self):
        """Verify unsupported model falls back to default agent if available"""
        from app.core.config import settings
        from app.services.codeer_client import get_codeer_agent_id

        # If default agent is configured, should fall back
        if settings.CODEER_DEFAULT_AGENT:
            # Act - should not raise error, use default
            agent_id = get_codeer_agent_id("unsupported-model")

            # Assert - should return default agent
            assert agent_id == settings.CODEER_DEFAULT_AGENT
        else:
            # If no default agent, should raise error
            from app.services.codeer_client import CodeerAPIError

            with pytest.raises(CodeerAPIError) as exc_info:
                get_codeer_agent_id("unsupported-model")

            error_msg = str(exc_info.value).lower()
            assert "unsupported" in error_msg or "not supported" in error_msg

    @pytest.mark.asyncio
    async def test_all_agent_ids_configured(self):
        """Verify all three agent IDs are configured in .env"""
        from app.core.config import settings

        # Assert
        assert (
            settings.CODEER_AGENT_CLAUDE_SONNET
        ), "CODEER_AGENT_CLAUDE_SONNET must be set"
        assert (
            settings.CODEER_AGENT_GEMINI_FLASH
        ), "CODEER_AGENT_GEMINI_FLASH must be set"
        assert settings.CODEER_AGENT_GPT5_MINI, "CODEER_AGENT_GPT5_MINI must be set"

        # Verify they are different (each model has unique agent)
        agents = {
            settings.CODEER_AGENT_CLAUDE_SONNET,
            settings.CODEER_AGENT_GEMINI_FLASH,
            settings.CODEER_AGENT_GPT5_MINI,
        }
        assert len(agents) == 3, "All three agent IDs should be unique"


# Integration test summary documentation
"""
Test Coverage Summary:
- Basic client lifecycle (context manager)
- Authentication and API key validation
- Agent listing and structure
- Chat creation (with/without agent)
- Chat listing with pagination
- Message listing with pagination
- Message sending (streaming and non-streaming)
- Streaming with callbacks
- Error handling for invalid IDs
- Edge cases (empty messages, invalid parameters)
- Callback exception handling

Expected RED Phase Results:
- All tests will FAIL because app.services.codeer_client doesn't exist yet
- Import errors: "No module named 'app.services.codeer_client'"
- This is CORRECT TDD behavior - implementation comes AFTER tests

Next Step (GREEN Phase):
- Invoke code-generator subagent to implement CodeerClient
- Implementation must satisfy all test contracts
- Re-run tests to verify GREEN state
"""
