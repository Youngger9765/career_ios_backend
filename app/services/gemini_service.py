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

    async def analyze_realtime_transcript(
        self,
        transcript: str,
        speakers: List[Dict[str, str]],
        rag_context: str = "",
    ) -> Dict[str, Any]:
        """Analyze realtime counseling transcript for AI supervision.

        Args:
            transcript: Full transcript text
            speakers: List of speaker segments with speaker role and text
            rag_context: Optional RAG knowledge base context

        Returns:
            Dict with: summary, alerts, suggestions
        """
        # Build speaker context
        speaker_context = "\n".join([f"{s['speaker']}: {s['text']}" for s in speakers])

        # Detect suicide risk keywords for alerts
        suicide_keywords = ["自殺", "想死", "活著沒意義", "不想活", "結束生命"]
        has_suicide_risk = any(keyword in transcript for keyword in suicide_keywords)

        prompt = f"""你是專業諮商督導，分析即時諮商對話。

對話內容：
{speaker_context}
{rag_context}

請提供：
1. summary: 簡短摘要（1-2 句，歸納對話重點）
2. alerts: 提醒事項（列表，3-5 點，標注重要關注點）
3. suggestions: 給諮商師的建議（列表，2-3 點，具體可執行的回應建議）
{"   - 如果有職涯知識庫內容，請在建議中適當引用相關知識" if rag_context else ""}

{
    "如果發現自殺風險（關鍵字：自殺、想死、活著沒意義等）" if has_suicide_risk else ""
}

回傳純 JSON 格式（不要 markdown code block）：
{{"summary": "...", "alerts": ["...", "..."], "suggestions": ["...", "..."]}}
"""

        response = await self.generate_text(
            prompt=prompt,
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        # Parse JSON from response
        import json

        try:
            result = json.loads(response)

            # Ensure lists are present
            if "alerts" not in result:
                result["alerts"] = []
            if "suggestions" not in result:
                result["suggestions"] = []
            if "summary" not in result:
                result["summary"] = "分析中..."

            return result
        except json.JSONDecodeError as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Response text: {response}")

            # Fallback: try to extract JSON from text
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

            # Final fallback
            return {
                "summary": "分析失敗，請稍後再試",
                "alerts": ["無法解析 AI 回應"],
                "suggestions": ["請檢查輸入內容"],
            }


# Create singleton instance
gemini_service = GeminiService()
