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

        prompt = f"""你是專業諮詢督導，分析即時諮詢對話。你的角色是站在案主與諮詢師之間，提供溫暖、同理且具體可行的專業建議。

【角色定義】CRITICAL - 必須嚴格遵守：
- "counselor" = 諮詢師/輔導師（專業助人者，提供協助的一方）
- "client" = 案主/個案/家長（求助者，有困擾需要協助的一方）
- 所有問題、困擾、症狀都是「案主/個案」面臨的，不是諮詢師的問題
- 分析焦點：案主的狀況、需求、風險
- 建議對象：給諮詢師的專業建議（如何協助案主）

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

3. **具體、可執行的建議**
   - 每個建議都必須包含明確的步驟或具體行動
   - 提供實際可用的對話範例
   - 避免抽象概念（如「建立良好溝通」），改用具體做法（如「晚餐後花 10 分鐘...」）

【輸出格式與範例】

對話內容：
{speaker_context}
{rag_context}

請提供以下 JSON 格式回應（不要 markdown code block）：

{{
  "summary": "客觀描述案主處境，不帶批判。例如：『案主（家長）正面臨孩子青春期的溝通挑戰，在管教過程中感到挫折與無力。』",

  "alerts": [
    "💡 理解與同理：先同理案主的感受。例如：『理解到案主在多次嘗試溝通無效後，感到非常挫折，這是很正常的反應。』",
    "⚠️ 需要關注的部分：溫和指出需要調整的地方。例如：『可以留意當情緒升高時，暫時離開現場冷靜可能會有幫助。』",
    "⚠️ 風險評估：如有自傷、自殺風險或暴力傾向，明確標示並建議轉介"
  ],

  "suggestions": [
    "💡 具體行動建議（含對話範例）：『建議諮詢師引導案主建立情緒冷靜機制。具體步驟：(1) 當感到快要發脾氣時，先深呼吸三次 (2) 告訴孩子：「媽媽現在需要冷靜一下，我們等一下再談好嗎？」(3) 到另一個房間或戶外走走 5-10 分鐘 (4) 冷靜後再回來溝通。』",
    "💡 引用專業知識（若有 RAG）：『可參考正向教養的「情緒急救箱」概念，協助案主建立自己的情緒調節工具包...』",
    "💡 後續追蹤：『下次會談時，可詢問案主這週有沒有遇到類似情境，以及使用冷靜策略的效果如何。』"
  ]
}}

【具體語氣範例對照】

❌ 太直接/批判：
「諮詢師表達出對孩子使用身體暴力的衝動，這對孩子可能造成身心傷害」

✅ 溫和同理：
「理解到在教養壓力下，父母有時會感到情緒失控是很正常的。這個時刻，我們可以先照顧自己的情緒，再來處理孩子的行為。建議可以試試看：當感到快要動手時，先暫停並深呼吸，告訴孩子『媽媽現在很生氣，我需要冷靜一下』，然後離開現場 5-10 分鐘。」

❌ 太抽象：
「建議改善親子溝通」

✅ 具體可行：
「建議每天晚餐後固定 15 分鐘『聊天時光』：(1) 關掉電視和手機 (2) 問孩子：『今天學校有什麼有趣的事？』或『今天心情怎麼樣？』(3) 專心聆聽，不急著給建議 (4) 用『我聽到你說...是這樣嗎？』來確認理解。」

{
    "⚠️ 自殺風險警示：如果發現自殺相關關鍵字（自殺、想死、活著沒意義等），請在 alerts 第一項明確標示『🚨 自殺風險警示』並建議立即評估與轉介。" if has_suicide_risk else ""
}

請嚴格遵守上述原則，以溫暖、專業、具體的方式提供督導建議。
"""

        response = await self.generate_text(
            prompt=prompt,
            temperature=0.3,
            max_tokens=8000,  # Increased from 2000 to prevent JSON truncation
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
