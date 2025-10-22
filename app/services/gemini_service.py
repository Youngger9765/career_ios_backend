"""Gemini service for chat completions using Vertex AI"""

import os

import vertexai
from vertexai.generative_models import GenerativeModel

# Import settings when available
try:
    from app.core.config import settings
    PROJECT_ID = getattr(settings, "GCS_PROJECT", "groovy-iris-473015-h3")
    LOCATION = getattr(settings, "VERTEX_LOCATION", "us-central1")
except ImportError:
    PROJECT_ID = os.getenv("GCS_PROJECT", "groovy-iris-473015-h3")
    LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")


class GeminiService:
    """Service for Gemini LLM chat completions via Vertex AI"""

    def __init__(self):
        """Initialize Gemini client (lazy loading)"""
        self.project_id = PROJECT_ID
        self.location = LOCATION
        self._chat_model = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of models"""
        if not self._initialized:
            vertexai.init(project=self.project_id, location=self.location)
            self._chat_model = GenerativeModel("gemini-2.5-flash")
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
    ) -> str:
        """
        Generate text using Gemini

        Args:
            prompt: The prompt to generate from
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        response = self.chat_model.generate_content(
            prompt,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
        )
        return response.text

    async def chat_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> str:
        """
        Chat completion using Gemini (alias for generate_text for compatibility)

        Args:
            prompt: The prompt to generate from
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        return await self.generate_text(prompt, temperature, max_tokens)


# Create singleton instance
gemini_service = GeminiService()
