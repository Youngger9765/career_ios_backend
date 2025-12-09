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
{speaker_context}
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

        response = await self.generate_text(
            prompt=prompt,
            temperature=0.7,  # Increased from 0.3 for more empathetic, human-like responses
            max_tokens=4000,  # Increased from 2500 - previous value caused JSON truncation (finish_reason=2)
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

            logger.info(
                f"Successfully parsed Gemini response. Summary length: {len(result.get('summary', ''))}, "
                f"Alerts: {len(result.get('alerts', []))}, Suggestions: {len(result.get('suggestions', []))}"
            )

            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Response text length: {len(response)}")
            logger.error(f"Response text (first 500 chars): {response[:500]}")
            logger.error(f"Response text (last 500 chars): {response[-500:]}")

            # Check if response was truncated by examining finish_reason
            # Note: The response here is already text, but we can check if it's incomplete
            if len(response) >= 7900:  # Near max_tokens limit
                logger.warning(
                    f"Response length ({len(response)}) is near max_tokens (8000). "
                    "Response may have been truncated. Consider increasing max_tokens."
                )

            # Fallback: try to extract JSON from text
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
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


# Create singleton instance
gemini_service = GeminiService()
