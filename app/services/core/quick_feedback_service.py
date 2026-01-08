"""
Quick Feedback Service - 輕量 AI 回饋服務

使用輕量級 Gemini Flash prompt 生成快速鼓勵訊息。
強制 15 字以內，確保同心圓 UI 顯示良好。
"""

import datetime
import logging
import time
from typing import Dict, Optional

from app.services.external.gemini_service import GeminiService

logger = logging.getLogger(__name__)

# 15 字以內的 fallback 訊息
FALLBACK_MESSAGES = [
    "繼續保持，你做得很好",
    "你正在聽孩子說話",
    "語氣很溫和，很棒",
    "有在同理孩子的感受",
]


class QuickFeedbackService:
    """輕量 AI 快速回饋服務 - 強制 15 字以內"""

    MAX_CHARS = 15  # 最大字數限制

    def __init__(self):
        self.gemini_service = GeminiService()

    async def get_quick_feedback(
        self,
        recent_transcript: str,
        full_transcript: Optional[str] = None,
        tenant_id: Optional[str] = None,
        mode: Optional[str] = None,
        scenario_context: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        使用 AI 生成快速回饋（強制 15 字以內）

        Args:
            recent_transcript: 最近 15 秒的逐字稿
            full_transcript: 完整累積逐字稿
            tenant_id: 租戶 ID
            mode: 模式 ("practice" / "emergency")
            scenario_context: 家長煩惱情境描述

        Returns:
            {
                "message": "AI 生成的鼓勵訊息（15 字以內）",
                "type": "ai_generated",
                "timestamp": "當前時間",
                "latency_ms": 延遲時間
            }
        """
        start_time = time.time()

        if full_transcript is None:
            full_transcript = recent_transcript

        try:
            # Build prompt with strict 15-char limit
            message, prompt_tokens, completion_tokens = await self._generate_feedback(
                recent_transcript, full_transcript, mode, scenario_context
            )

            # Enforce 15 char limit
            if len(message) > self.MAX_CHARS:
                message = message[: self.MAX_CHARS]
                logger.warning(f"Truncated message to {self.MAX_CHARS} chars")

            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "message": message,
                "type": "ai_generated",
                "timestamp": datetime.datetime.now().isoformat(),
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }

        except Exception as e:
            logger.error(f"Quick feedback generation failed: {str(e)}")

            # Fallback
            import random

            return {
                "message": random.choice(FALLBACK_MESSAGES),
                "type": "fallback",
                "timestamp": datetime.datetime.now().isoformat(),
                "latency_ms": int((time.time() - start_time) * 1000),
                "error": str(e),
            }

    async def _generate_feedback(
        self,
        recent_transcript: str,
        full_transcript: str,
        mode: Optional[str],
        scenario_context: Optional[str],
    ) -> tuple:
        """
        使用 Gemini 生成 15 字以內的回饋

        Returns:
            (message, prompt_tokens, completion_tokens)
        """
        # Mode context
        mode_context = ""
        if mode == "practice":
            mode_context = "【單人練習模式】只有家長在練習，評估說話技巧"
        else:
            mode_context = "【即時對話模式】真實親子互動，評估互動狀態"

        # Scenario context
        scenario_section = ""
        if scenario_context:
            scenario_section = f"情境：{scenario_context[:50]}\n"

        prompt = f"""你是親子溝通專家。請用一句話（15 字以內）給家長即時回饋。

{mode_context}
{scenario_section}
【最近對話】
{recent_transcript[:300]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【回饋規則】
1. ⚠️ 必須 15 字以內（這是硬性限制！）
2. 正向鼓勵為主
3. 具體指出做得好的地方
4. 繁體中文

【範例】（都是 15 字以內）
- 你正在聽，而不是急著回
- 語氣很溫和，繼續保持
- 有在接住孩子的情緒
- 你沒有急著給答案
- 讓孩子感覺被理解

請直接回覆一句話，不要加任何標點或格式。"""

        response = await self.gemini_service.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_tokens=50,  # 限制輸出
        )

        # Extract text
        text = response.text.strip().strip("\"'。，！")
        # Remove line breaks
        text = text.replace("\n", "").replace("\r", "")

        # Get token counts
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
            completion_tokens = getattr(usage, "candidates_token_count", 0) or 0

        return text, prompt_tokens, completion_tokens


# 創建全局實例
quick_feedback_service = QuickFeedbackService()
