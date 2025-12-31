"""Gemini service for chat completions using Vertex AI"""

import logging
from typing import Any, Dict, List, Optional

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel
from vertexai.preview import caching

from app.core.config import settings


class GeminiService:
    """Service for Gemini LLM chat completions via Vertex AI"""

    def __init__(self, model_name: Optional[str] = None):
        """Initialize Gemini client (lazy loading)

        Args:
            model_name: Model name to use (default: from config)
        """
        self.project_id = settings.GEMINI_PROJECT_ID
        self.location = settings.GEMINI_LOCATION
        self.model_name = model_name or settings.GEMINI_CHAT_MODEL
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
    ):
        """
        Generate text using Gemini

        Args:
            prompt: The prompt to generate from
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (e.g., {"type": "json_object"})

        Returns:
            Full Gemini response object with text and usage_metadata attributes
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

        # Log usage metadata for cache performance tracking
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            logger.info(f"📊 Usage metadata: {usage}")
            if hasattr(usage, "cached_content_token_count"):
                logger.info(f"🎯 Cached tokens: {usage.cached_content_token_count}")
            if hasattr(usage, "prompt_token_count"):
                logger.info(f"📝 Prompt tokens: {usage.prompt_token_count}")
            if hasattr(usage, "candidates_token_count"):
                logger.info(f"💬 Output tokens: {usage.candidates_token_count}")

        return response

    async def chat_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
        response_format: Optional[Dict[str, str]] = None,
        return_metadata: bool = False,
    ) -> str | Dict[str, Any]:
        """
        Chat completion using Gemini (alias for generate_text for compatibility)

        Args:
            prompt: The prompt to generate from
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (e.g., {"type": "json_object"})
            return_metadata: If True, return dict with 'text' and 'usage_metadata'

        Returns:
            Generated text, or dict with text and metadata if return_metadata=True
        """
        response = await self.generate_text(
            prompt, temperature, max_tokens, response_format
        )

        if return_metadata:
            # Extract usage metadata
            usage_metadata = {}
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                for attr in [
                    "cached_content_token_count",
                    "prompt_token_count",
                    "candidates_token_count",
                    "total_token_count",
                ]:
                    if hasattr(usage, attr):
                        usage_metadata[attr] = getattr(usage, attr)

            return {
                "text": response.text,
                "usage_metadata": usage_metadata,
            }

        # Return just text for backward compatibility
        return response.text

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

        response = await self.generate_text(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )

        # Return just text for backward compatibility
        return response.text

    async def analyze_realtime_transcript(
        self,
        transcript: str,
        speakers: List[Dict[str, str]],
        rag_context: str = "",
        custom_prompt: str = "",
    ) -> Dict[str, Any]:
        """Analyze realtime counseling transcript for AI supervision.

        Args:
            transcript: Full transcript text
            speakers: List of speaker segments with speaker role and text
            rag_context: Optional RAG knowledge base context
            custom_prompt: Optional custom prompt (overrides default prompt)

        Returns:
            Dict with: summary, alerts, suggestions
        """
        # Detect suicide risk keywords for alerts
        suicide_keywords = ["自殺", "想死", "活著沒意義", "不想活", "結束生命"]
        has_suicide_risk = any(keyword in transcript for keyword in suicide_keywords)

        # Use custom prompt if provided, otherwise use default
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = f"""你是專業諮詢督導，分析即時諮詢對話。你的角色是站在案主與諮詢師之間，提供溫暖、同理且具體可行的專業建議。

【角色定義】CRITICAL - 必須嚴格遵守：
- "counselor" = 諮詢師/輔導師（專業助人者，提供協助的一方）
- "client" = 案主/個案/家長（求助者，有困擾需要協助的一方）
- 所有問題、困擾、症狀都是「案主/個案」面臨的，不是諮詢師的問題
- 分析焦點：案主的狀況、需求、風險
- 建議對象：給諮詢師的專業建議（如何協助案主）

【分析範圍】CRITICAL - 必須嚴格遵守：
🎯 **主要分析焦點**：最新一分鐘內的對話內容
   - 你會收到完整的對話記錄（可能長達數十分鐘）
   - 但你的分析必須聚焦在「最後出現的對話」（最新一分鐘）
   - 前面的對話僅作為背景脈絡參考，幫助你理解前因後果

📚 **背景脈絡參考**：前面的對話內容
   - 了解案主和諮詢師的互動歷程即可
   - 不需要在分析中詳細提及過早的歷史內容

✅ **輸出要求**：
   - summary：聚焦最新一分鐘的核心議題和互動重點
   - alerts：針對最新一分鐘需要立即關注的狀況
   - suggestions：基於最新一分鐘的對話，給出具體行動建議

❌ **避免**：
   - 不要對整段對話做總體性的回顧或總結
   - 不要提及過早的歷史內容（除非與當下直接相關）
   - 不要像寫報告一樣總結全部內容

✅ **正確心態**：像一個實時在旁觀察的督導，針對「當下這一刻」給出即時建議

【核心原則】同理優先、溫和引導、具體行動：

1. **同理與理解為先**
   - 永遠先理解與同理案主（家長）的感受和處境
   - 認可教養壓力、情緒失控是正常的人性反應
   - 避免批判、指責或讓案主感到被否定

2. **溫和、非批判的語氣**
   - ❌ 禁止用語：「表達出對孩子使用身體暴力的衝動」「可能造成傷害」「不當管教」
   - ✅ 建議用語：「理解到在教養壓力下，父母有時會感到情緒失控是很正常的」
   - ✅ 使用：「可以考慮」「或許」「試試看」等柔和引導詞
   - ✅ 焦點放在「如何調整」而非「哪裡做錯」

3. **具體、簡潔的建議**
   - 建議要具體可行，但保持簡短（不超過 50 字）
   - 避免抽象概念，用具體做法
   - 不要冗長的步驟說明或對話範例

【輸出格式與範例】

對話內容：
{transcript}
{rag_context}

【簡潔性要求】CRITICAL - 必須遵守：
- ✅ summary：1-2 句話即可，抓核心重點
- ✅ alerts：最多 2-3 項，每項 1 句話
- ✅ suggestions：最多 2-3 項，每項簡明扼要（不超過 50 字）
- ❌ 不要過度詳細的步驟說明（如「第一步、第二步、第三步」）
- ❌ 不要冗長的對話範例（簡短提示即可）
- ❌ 不要重複或冗餘的內容

請提供以下 JSON 格式回應（不要 markdown code block）：

{{
  "summary": "案主處境簡述（1-2 句）",

  "alerts": [
    "💡 同理案主感受（1 句）",
    "⚠️ 需關注的部分（1 句）"
  ],

  "suggestions": [
    "💡 核心建議（簡短，< 50 字）",
    "💡 具體做法（簡短，< 50 字）"
  ]
}}

【語氣要求】溫和、同理、簡潔，避免批判或過度說教。

{
    "⚠️ 自殺風險警示：如果發現自殺相關關鍵字（自殺、想死、活著沒意義等），請在 alerts 第一項明確標示『🚨 自殺風險警示』並建議立即評估與轉介。" if has_suicide_risk else ""
}

請嚴格遵守上述原則，以溫暖、專業、具體的方式提供督導建議。
"""

        logger = logging.getLogger(__name__)
        logger.info(
            f"Starting realtime transcript analysis. Transcript length: {len(transcript)}, "
            f"Speakers: {len(speakers)}, RAG context length: {len(rag_context)}"
        )

        # Generate response with metadata tracking
        generation_config: Dict[str, Any] = {
            "temperature": 0.7,
            "max_output_tokens": 4000,
            "response_mime_type": "application/json",
        }

        config = GenerationConfig(**generation_config)
        response = self.chat_model.generate_content(prompt, generation_config=config)

        # Extract usage metadata
        usage_metadata = {}

        # Extract usage metadata for cache performance tracking
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            logger.info(f"📊 Usage metadata: {usage}")

            # Extract token counts
            for attr in [
                "cached_content_token_count",
                "prompt_token_count",
                "candidates_token_count",
                "total_token_count",
            ]:
                if hasattr(usage, attr):
                    value = getattr(usage, attr)
                    usage_metadata[attr] = value
                    logger.debug(f"Token count - {attr}: {value}")
        else:
            logger.warning("⚠️ Response has NO usage_metadata attribute!")

        # Parse JSON from response
        import json

        try:
            result = json.loads(response.text)

            # Ensure lists are present
            if "alerts" not in result:
                result["alerts"] = []
            if "suggestions" not in result:
                result["suggestions"] = []
            if "summary" not in result:
                result["summary"] = "分析中..."

            # Add usage metadata to result
            if usage_metadata:
                result["usage_metadata"] = usage_metadata

            logger.info(
                f"Successfully parsed Gemini response. Summary length: {len(result.get('summary', ''))}, "
                f"Alerts: {len(result.get('alerts', []))}, Suggestions: {len(result.get('suggestions', []))}"
            )

            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Response text length: {len(response.text)}")
            logger.error(f"Response text (first 500 chars): {response.text[:500]}")
            logger.error(f"Response text (last 500 chars): {response.text[-500:]}")

            # Check if response was truncated by examining finish_reason
            # Note: The response here is already text, but we can check if it's incomplete
            if len(response.text) >= 7900:  # Near max_tokens limit
                logger.warning(
                    f"Response length ({len(response.text)}) is near max_tokens (8000). "
                    "Response may have been truncated. Consider increasing max_tokens."
                )

            # Fallback: try to extract JSON from text
            import re

            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                logger.info("Attempting to extract JSON from response using regex...")
                try:
                    extracted_result = json.loads(json_match.group())
                    logger.info("Successfully extracted JSON from response")
                    return extracted_result
                except json.JSONDecodeError as regex_error:
                    logger.error(f"Failed to parse extracted JSON: {regex_error}")
                    logger.error(
                        f"Extracted JSON (first 500 chars): {json_match.group()[:500]}"
                    )

            # Log fallback usage
            logger.error(
                "All JSON parsing attempts failed. Returning fallback error response."
            )

            # Final fallback
            return {
                "summary": "分析失敗，請稍後再試",
                "alerts": ["無法解析 AI 回應"],
                "suggestions": ["請檢查輸入內容"],
            }

    async def analyze_with_cache(
        self,
        cached_content: caching.CachedContent,
        transcript: str,
        speakers: List[Dict[str, str]],
        rag_context: str = "",
        custom_prompt: str = "",
    ) -> Dict[str, Any]:
        """Analyze realtime transcript using cached content.

        Args:
            cached_content: CachedContent object from cache manager
            transcript: Full transcript text
            speakers: List of speaker segments with speaker role and text
            rag_context: Optional RAG knowledge base context
            custom_prompt: Optional custom prompt (overrides default prompt)

        Returns:
            Dict with: summary, alerts, suggestions, and usage_metadata
        """
        # Detect suicide risk keywords for alerts
        suicide_keywords = ["自殺", "想死", "活著沒意義", "不想活", "結束生命"]
        has_suicide_risk = any(keyword in transcript for keyword in suicide_keywords)

        # Use custom prompt if provided, otherwise build default prompt
        if custom_prompt:
            user_prompt = custom_prompt
        else:
            # Build user prompt (only the new content, not the accumulated transcript)
            user_prompt = f"""對話內容：
{transcript}
{rag_context}

{
    "⚠️ 自殺風險警示：如果發現自殺相關關鍵字（自殺、想死、活著沒意義等），請在 alerts 第一項明確標示『🚨 自殺風險警示』並建議立即評估與轉介。" if has_suicide_risk else ""
}

【提醒】如上方有提供 RAG 知識庫內容，請優先參考專業理論和方法。

請嚴格遵守上述原則，以溫暖、專業、具體的方式提供督導建議。
"""

        logger = logging.getLogger(__name__)
        logger.info(
            f"Starting cached analysis. Transcript length: {len(transcript)}, "
            f"Speakers: {len(speakers)}, RAG context length: {len(rag_context)}"
        )

        # Create model from cached content
        model = GenerativeModel.from_cached_content(cached_content=cached_content)

        # Generate response with metadata tracking
        generation_config: Dict[str, Any] = {
            "temperature": 0.7,
            "max_output_tokens": 4000,
            "response_mime_type": "application/json",
        }

        config = GenerationConfig(**generation_config)
        response = model.generate_content(user_prompt, generation_config=config)

        # Extract usage metadata
        usage_metadata = {}

        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            logger.info(f"📊 Usage metadata: {usage}")

            # Extract token counts
            for attr in [
                "cached_content_token_count",
                "prompt_token_count",
                "candidates_token_count",
                "total_token_count",
            ]:
                if hasattr(usage, attr):
                    value = getattr(usage, attr)
                    usage_metadata[attr] = value
                    logger.debug(f"Token count - {attr}: {value}")

            # Log cache hit metrics
            if hasattr(usage, "cached_content_token_count"):
                cached_tokens = usage.cached_content_token_count
                prompt_tokens = getattr(usage, "prompt_token_count", 0)
                total_input = cached_tokens + prompt_tokens
                cache_ratio = (
                    (cached_tokens / total_input * 100) if total_input > 0 else 0
                )
                logger.info(
                    f"🎯 Cache hit: {cached_tokens} tokens ({cache_ratio:.1f}%)"
                )
        else:
            logger.warning("⚠️ Response has NO usage_metadata attribute!")

        # Parse JSON from response
        import json

        try:
            result = json.loads(response.text)

            # Ensure lists are present
            if "alerts" not in result:
                result["alerts"] = []
            if "suggestions" not in result:
                result["suggestions"] = []
            if "summary" not in result:
                result["summary"] = "分析中..."

            # Add usage metadata to result
            if usage_metadata:
                result["usage_metadata"] = usage_metadata

            logger.info(
                f"Successfully parsed cached Gemini response. Summary length: {len(result.get('summary', ''))}, "
                f"Alerts: {len(result.get('alerts', []))}, Suggestions: {len(result.get('suggestions', []))}"
            )

            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Response text length: {len(response.text)}")
            logger.error(f"Response text (first 500 chars): {response.text[:500]}")
            logger.error(f"Response text (last 500 chars): {response.text[-500:]}")

            # Check if response was truncated
            if len(response.text) >= 3900:
                logger.warning(
                    f"Response length ({len(response.text)}) is near max_tokens (4000). "
                    "Response may have been truncated. Consider increasing max_tokens."
                )

            # Fallback: try to extract JSON from text
            import re

            json_match = re.search(r"\{.*\}", response.text, re.DOTALL)
            if json_match:
                logger.info("Attempting to extract JSON from response using regex...")
                try:
                    extracted_result = json.loads(json_match.group())
                    logger.info("Successfully extracted JSON from response")
                    return extracted_result
                except json.JSONDecodeError as regex_error:
                    logger.error(f"Failed to parse extracted JSON: {regex_error}")

            # Final fallback
            logger.error(
                "All JSON parsing attempts failed. Returning fallback error response."
            )
            return {
                "summary": "分析失敗，請稍後再試",
                "alerts": ["無法解析 AI 回應"],
                "suggestions": ["請檢查輸入內容"],
            }


# Create singleton instance
gemini_service = GeminiService()
