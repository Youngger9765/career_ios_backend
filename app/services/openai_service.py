"""OpenAI service for embeddings and chat completions"""

from openai import AsyncOpenAI

# Import settings when available
try:
    from app.core.config import settings

    OPENAI_API_KEY = settings.OPENAI_API_KEY
    EMBEDDING_MODEL = getattr(
        settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
    )
    CHAT_MODEL = getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4.1-mini")
except ImportError:
    import os

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")


class OpenAIService:
    """Service for interacting with OpenAI API"""

    def __init__(self):
        """Initialize OpenAI client"""
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.embedding_model = EMBEDDING_MODEL
        self.chat_model = CHAT_MODEL

    async def create_embedding(self, text: str) -> list[float]:
        """
        Create embedding vector for text

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        response = await self.client.embeddings.create(
            model=self.embedding_model, input=text
        )

        return response.data[0].embedding

    async def create_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Create embeddings for multiple texts in batch

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        response = await self.client.embeddings.create(
            model=self.embedding_model, input=texts
        )

        return [item.embedding for item in response.data]

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        response_format: dict = None,
    ) -> str:
        """
        Get chat completion from OpenAI

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            response_format: Optional response format (e.g., {"type": "json_schema", "json_schema": {...}})

        Returns:
            Response text from assistant
        """
        kwargs = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = await self.client.chat.completions.create(**kwargs)

        return response.choices[0].message.content or ""

    async def chat_completion_with_context(
        self,
        question: str,
        context: str,
        system_prompt: str = "You are a helpful assistant. Answer based on the provided context.",
        temperature: float = 0.7,
    ) -> str:
        """
        Get chat completion with RAG context

        Args:
            question: User's question
            context: Retrieved context from vector search
            system_prompt: System prompt for the assistant
            temperature: Sampling temperature

        Returns:
            Response text from assistant
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ]

        return await self.chat_completion(messages=messages, temperature=temperature)
