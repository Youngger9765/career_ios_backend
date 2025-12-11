"""
Codeer AI API Client with SSE streaming support

Provides async HTTP client for interacting with Codeer AI API endpoints:
- Published agents listing
- Chat creation and management
- Message sending (streaming and non-streaming)
- SSE (Server-Sent Events) streaming with callbacks

MODEL SELECTION CAPABILITIES:
---------------------------------
IMPORTANT: Codeer uses AGENT-BASED selection, NOT direct model selection.

- ✅ Agent selection via `agent_id` parameter (e.g., 親子專家)
- ✅ Multiple agents can be listed via `list_published_agents()`
- ✅ LLM model information visible in agent metadata (NEW: 2025-12-11)
- ✅ Agent `llm_model` field shows underlying model (e.g., "openai/gpt-5-mini;gpt-5 mini")
- ⚠️ Model selection is INDIRECT (create separate agents for different models)
- ❌ NO direct model selection parameter (cannot choose GPT-4, Gemini, Grok)
- ❌ NO runtime model switching within same agent

Each agent has a pre-configured underlying model. Model information is now
VISIBLE via the `llm_model` field in agent metadata, but you still cannot
directly select models at runtime. To use different models, create separate
agents in the Codeer platform (e.g., "親子專家 - GPT-4", "親子專家 - Gemini").

Example:
    # Correct: Select agent and see its model
    client = CodeerClient()
    agents = await client.list_published_agents()
    print(f"Agent: {agents[0]['name']}")
    print(f"Model: {agents[0]['llm_model']}")  # NEW: Shows "openai/gpt-5-mini;gpt-5 mini"
    chat = await client.create_chat(name="Session", agent_id=agents[0]["id"])

    # NOT POSSIBLE: Select model directly at runtime
    # chat = await client.create_chat(name="Session", model="gpt-4")  # ❌ No such parameter

For detailed comparison with Gemini, see: docs/LLM_PROVIDER_COMPARISON.md
"""

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Import settings when available
try:
    from app.core.config import settings

    CODEER_API_KEY = settings.CODEER_API_KEY
    CODEER_API_ROOT = settings.CODEER_API_ROOT
    CODEER_DEFAULT_AGENT = settings.CODEER_DEFAULT_AGENT
    CODEER_AGENT_CLAUDE_SONNET = settings.CODEER_AGENT_CLAUDE_SONNET
    CODEER_AGENT_GEMINI_FLASH = settings.CODEER_AGENT_GEMINI_FLASH
    CODEER_AGENT_GPT5_MINI = settings.CODEER_AGENT_GPT5_MINI
except ImportError:
    CODEER_API_KEY = os.getenv("CODEER_API_KEY", "")
    CODEER_API_ROOT = os.getenv("CODEER_API_ROOT", "https://api.codeer.ai")
    CODEER_DEFAULT_AGENT = os.getenv("CODEER_DEFAULT_AGENT")
    CODEER_AGENT_CLAUDE_SONNET = os.getenv("CODEER_AGENT_CLAUDE_SONNET", "")
    CODEER_AGENT_GEMINI_FLASH = os.getenv("CODEER_AGENT_GEMINI_FLASH", "")
    CODEER_AGENT_GPT5_MINI = os.getenv("CODEER_AGENT_GPT5_MINI", "")


class CodeerAPIError(Exception):
    """Exception raised for Codeer API errors"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        """
        Initialize CodeerAPIError

        Args:
            message: Error message
            status_code: HTTP status code if applicable
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


def get_codeer_agent_id(model: str = "gpt5-mini") -> str:
    """
    Get Codeer agent ID based on model name

    Args:
        model: Model identifier. Supported values:
            - "claude-sonnet" or "claude": Claude Sonnet 4.5
            - "gemini-flash" or "gemini": Gemini 2.5 Flash
            - "gpt5-mini" or "gpt5" or "gpt": GPT-5 Mini (default)

    Returns:
        Agent ID string

    Raises:
        CodeerAPIError: If model is not supported or agent ID is not configured

    Example:
        agent_id = get_codeer_agent_id("claude-sonnet")
        chat = await client.create_chat(name="Session", agent_id=agent_id)
    """
    # Normalize model name
    model_lower = model.lower().strip()

    # Map model names to agent IDs
    if model_lower in ["claude-sonnet", "claude"]:
        agent_id = CODEER_AGENT_CLAUDE_SONNET
        if not agent_id:
            raise CodeerAPIError(
                "Claude Sonnet agent not configured. "
                "Please set CODEER_AGENT_CLAUDE_SONNET in .env"
            )
        return agent_id

    elif model_lower in ["gemini-flash", "gemini"]:
        agent_id = CODEER_AGENT_GEMINI_FLASH
        if not agent_id:
            raise CodeerAPIError(
                "Gemini Flash agent not configured. "
                "Please set CODEER_AGENT_GEMINI_FLASH in .env"
            )
        return agent_id

    elif model_lower in ["gpt5-mini", "gpt5", "gpt"]:
        agent_id = CODEER_AGENT_GPT5_MINI or CODEER_DEFAULT_AGENT
        if not agent_id:
            raise CodeerAPIError(
                "GPT-5 Mini agent not configured. "
                "Please set CODEER_AGENT_GPT5_MINI in .env"
            )
        return agent_id

    else:
        # Fallback to default agent if available
        if CODEER_DEFAULT_AGENT:
            logger.warning(
                f"Unknown model '{model}', using default agent: {CODEER_DEFAULT_AGENT}"
            )
            return CODEER_DEFAULT_AGENT

        raise CodeerAPIError(
            f"Unsupported model: {model}. "
            f"Supported models: claude-sonnet, gemini-flash, gpt5-mini"
        )


class CodeerClient:
    """Async HTTP client for Codeer AI API with SSE streaming support"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize Codeer API client

        Args:
            api_key: Codeer API key (defaults to CODEER_API_KEY env var)
            base_url: API base URL (defaults to CODEER_API_ROOT)
        """
        self.api_key = api_key or CODEER_API_KEY
        self.base_url = (base_url or CODEER_API_ROOT).rstrip("/")
        self.default_agent = CODEER_DEFAULT_AGENT

        # Initialize httpx async client
        self.client = httpx.AsyncClient(
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self):
        """Close the HTTP client connection"""
        await self.client.aclose()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close client"""
        await self.close()

    def _check_response(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Check API response and extract data

        Args:
            response: httpx Response object

        Returns:
            Data from response

        Raises:
            CodeerAPIError: If response indicates error
        """
        # Check HTTP status code
        if response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", response.text)
            except Exception:
                error_msg = response.text or f"HTTP {response.status_code} error"

            raise CodeerAPIError(error_msg, status_code=response.status_code)

        # Parse JSON response
        try:
            response_data = response.json()
        except Exception as e:
            raise CodeerAPIError(f"Failed to parse JSON response: {str(e)}")

        # Check error_code field
        error_code = response_data.get("error_code", 0)
        if error_code != 0:
            error_msg = response_data.get("message", "Unknown API error")
            raise CodeerAPIError(error_msg, status_code=response.status_code)

        # Return data field
        return response_data.get("data", response_data)

    async def list_published_agents(self) -> List[Dict]:
        """
        List all published agents (model selection alternative)

        Returns:
            List of agent dictionaries with id, name, llm_model, and other properties

        Note:
            This is the ONLY way to discover available "models" in Codeer.
            Agents are pre-configured with specific LLM models. As of 2025-12-11,
            the `llm_model` field is now available in agent metadata, showing
            which underlying model (GPT, Gemini, etc.) each agent uses.

        Example:
            agents = await client.list_published_agents()
            for agent in agents:
                print(f"Agent: {agent['name']} (ID: {agent['id']})")
                print(f"Model: {agent['llm_model']}")  # NEW: Shows model info
                # Example: "openai/gpt-5-mini;gpt-5 mini"

        Raises:
            CodeerAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v1/chats/published-agents"

        try:
            response = await self.client.get(url)
            return self._check_response(response)
        except httpx.HTTPError as e:
            raise CodeerAPIError(f"Failed to list agents: {str(e)}")

    async def create_chat(
        self, name: str, agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new chat

        Args:
            name: Chat name
            agent_id: Agent ID (required by API, uses default from settings if not provided)
                     NOTE: This is AGENT selection, NOT model selection.
                     Each agent has a pre-configured underlying LLM model.
                     You cannot directly choose GPT-4, Gemini, Grok, etc.

        Returns:
            Chat object with id, name, and other properties

        Raises:
            CodeerAPIError: If API request fails or no agent_id available

        Example:
            # Use default parenting expert agent
            chat = await client.create_chat(name="Session-123")

            # Use different agent (if available)
            agents = await client.list_published_agents()
            chat = await client.create_chat(name="Session-123", agent_id=agents[0]["id"])
        """
        # agent_id is required by the API
        effective_agent_id = agent_id or self.default_agent
        if not effective_agent_id:
            raise CodeerAPIError(
                "agent_id is required. Provide agent_id parameter or set CODEER_DEFAULT_AGENT in settings."
            )

        url = f"{self.base_url}/api/v1/chats"
        payload = {
            "name": name,
            "agent_id": effective_agent_id,
        }

        try:
            response = await self.client.post(url, json=payload)
            return self._check_response(response)
        except httpx.HTTPError as e:
            raise CodeerAPIError(f"Failed to create chat: {str(e)}")

    async def list_chats(
        self,
        limit: int = 20,
        offset: int = 0,
        order_by: str = "-created_at",
        agent_id: Optional[str] = None,
        external_user_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        List chats with pagination and filtering

        Args:
            limit: Maximum number of chats to return (default 20)
            offset: Number of chats to skip (default 0)
            order_by: Sort order (default "-created_at" for newest first)
            agent_id: Filter by agent ID
            external_user_id: Filter by external user ID

        Returns:
            List of chat dictionaries

        Raises:
            CodeerAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v1/chats"
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "order_by": order_by,
        }

        if agent_id:
            params["agent_id"] = agent_id
        if external_user_id:
            params["external_user_id"] = external_user_id

        try:
            response = await self.client.get(url, params=params)
            return self._check_response(response)
        except httpx.HTTPError as e:
            raise CodeerAPIError(f"Failed to list chats: {str(e)}")

    async def list_chat_messages(
        self,
        chat_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """
        List messages in a chat

        Args:
            chat_id: Chat ID
            limit: Maximum number of messages to return (default 50)
            offset: Number of messages to skip (default 0)

        Returns:
            List of message dictionaries

        Raises:
            CodeerAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v1/chats/{chat_id}/messages"
        params = {
            "limit": limit,
            "offset": offset,
        }

        try:
            response = await self.client.get(url, params=params)
            return self._check_response(response)
        except httpx.HTTPError as e:
            raise CodeerAPIError(f"Failed to list messages: {str(e)}")

    async def send_message(
        self,
        chat_id: int,
        message: str,
        stream: bool = False,
        agent_id: Optional[str] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a chat

        Args:
            chat_id: Chat ID
            message: Message text to send
            stream: Whether to use SSE streaming (default False)
            agent_id: Agent ID (uses default from settings if not provided)
            on_chunk: Optional callback function for streaming chunks

        Returns:
            Response dictionary with message content

        Raises:
            CodeerAPIError: If API request fails
        """
        # Use provided agent_id or default
        effective_agent_id = agent_id or self.default_agent

        url = f"{self.base_url}/api/v1/chats/{chat_id}/messages"
        payload: Dict[str, Any] = {
            "message": message,
            "stream": stream,
        }

        if effective_agent_id:
            payload["agent_id"] = effective_agent_id

        try:
            if stream:
                return await self._send_message_streaming(
                    url, payload, on_chunk=on_chunk
                )
            else:
                response = await self.client.post(url, json=payload)
                return self._check_response(response)
        except httpx.HTTPError as e:
            raise CodeerAPIError(f"Failed to send message: {str(e)}")

    async def _send_message_streaming(
        self,
        url: str,
        payload: Dict[str, Any],
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Send message with SSE streaming

        Args:
            url: API endpoint URL
            payload: Request payload
            on_chunk: Optional callback for streaming chunks

        Returns:
            Final response dictionary

        Raises:
            CodeerAPIError: If streaming fails
        """
        full_text = ""
        current_event = None
        data_lines: List[str] = []

        try:
            async with self.client.stream("POST", url, json=payload) as response:
                # Check initial response status
                if response.status_code >= 400:
                    error_text = await response.aread()
                    raise CodeerAPIError(
                        f"Streaming request failed: {error_text.decode()}",
                        status_code=response.status_code,
                    )

                async for line in response.aiter_lines():
                    line = line.strip()

                    if not line:
                        # Blank line = event boundary
                        if data_lines:
                            json_data = self._process_sse_event(
                                current_event, data_lines, on_chunk
                            )
                            if json_data and "full_text" in json_data:
                                full_text = json_data["full_text"]
                            elif json_data and "delta" in json_data:
                                full_text += json_data["delta"]

                            data_lines = []
                            current_event = None
                        continue

                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                    elif line.startswith("data:"):
                        data_content = line[5:].strip()
                        if data_content == "[DONE]":
                            break
                        data_lines.append(data_content)

                # Process any remaining data
                if data_lines:
                    json_data = self._process_sse_event(
                        current_event, data_lines, on_chunk
                    )
                    if json_data and "full_text" in json_data:
                        full_text = json_data["full_text"]

        except httpx.HTTPError as e:
            raise CodeerAPIError(f"Streaming failed: {str(e)}")

        # Return final response
        return {
            "content": full_text,
            "text": full_text,
            "message": full_text,
        }

    def _process_sse_event(
        self,
        event: Optional[str],
        data_lines: List[str],
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single SSE event

        Args:
            event: Event type
            data_lines: Lines of data for this event
            on_chunk: Optional callback for chunks

        Returns:
            Parsed JSON data or None

        Raises:
            CodeerAPIError: If event indicates error
        """
        if not data_lines:
            return None

        try:
            json_str = "".join(data_lines)
            json_data = json.loads(json_str)

            # Handle error events
            if event == "error":
                error_msg = json_data.get("message", "Unknown streaming error")
                raise CodeerAPIError(f"Streaming error: {error_msg}")

            # Handle delta events
            if event == "response.output_text.delta" and "delta" in json_data:
                delta = json_data["delta"]
                if on_chunk and delta:
                    try:
                        on_chunk(delta)
                    except Exception as e:
                        logger.warning(f"Callback error: {e}")
                return json_data

            # Handle completed events
            if event == "response.output_text.completed" and "full_text" in json_data:
                return json_data

            return json_data

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse SSE data: {e}")
            return None
