"""Gemini service for chat completions using Vertex AI"""

import logging
import os
from typing import Any, Dict, List, Optional

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

# Import settings when available
try:
    from app.core.config import settings

    PROJECT_ID = getattr(settings, "GEMINI_PROJECT_ID", "groovy-iris-473015-h3")
    LOCATION = getattr(settings, "GEMINI_LOCATION", "us-central1")
    CHAT_MODEL = getattr(settings, "GEMINI_CHAT_MODEL", "gemini-2.5-flash")
except ImportError:
    PROJECT_ID = os.getenv("GEMINI_PROJECT_ID", "groovy-iris-473015-h3")
    LOCATION = os.getenv("GEMINI_LOCATION", "us-central1")
    CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.5-flash")


class GeminiService:
    """Service for Gemini LLM chat completions via Vertex AI"""

    def __init__(self, model_name: Optional[str] = None):
        """Initialize Gemini client (lazy loading)

        Args:
            model_name: Model name to use (default: from config)
        """
        self.project_id = PROJECT_ID
        self.location = LOCATION
        self.model_name = model_name or CHAT_MODEL
        self._chat_model = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of models"""
        if not self._initialized:
            vertexai.init(project=self.project_id, location=self.location)
            self._chat_model = GenerativeModel(self.model_name)
            self._initialized = True

    @property
    def chat_model(self):
        self._ensure_initialized()
        return self._chat_model

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate text using Gemini

        Args:
            prompt: The prompt to generate from
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            Generated text
        """
        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        # Add JSON mode if requested
        if response_format and response_format.get("type") == "json_object":
            generation_config["response_mime_type"] = "application/json"

        config = GenerationConfig(**generation_config)
        response = self.chat_model.generate_content(prompt, generation_config=config)

        # Log response details
        logger = logging.getLogger(__name__)
        logger.info(
            f"Gemini generate_content completed. Response text length: {len(response.text)}"
        )

        # Check for finish_reason to detect truncation
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "finish_reason"):
                logger.info(f"Finish reason: {candidate.finish_reason}")
                if candidate.finish_reason != 1:  # 1 = STOP (normal completion)
                    logger.warning(
                        f"Response may be incomplete. Finish reason: {candidate.finish_reason}"
                    )

        return response.text

    async def chat_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Chat completion using Gemini (alias for generate_text for compatibility)

        Args:
            prompt: The prompt to generate from
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            Generated text
        """
        return await self.generate_text(
            prompt, temperature, max_tokens, response_format
        )

    async def chat_completion_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 8192,
        response_format: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Chat completion using OpenAI-style messages format

        Converts OpenAI messages format to Gemini prompt format.

        Args:
            messages: List of message dicts with 'role' and 'content'
                     Supported roles: system, user, assistant
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            Generated text
        """
        # Convert OpenAI messages to Gemini prompt
        prompt_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")

        prompt = "\n\n".join(prompt_parts)

        return await self.generate_text(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )


# Create singleton instance
gemini_service = GeminiService()
