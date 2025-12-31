"""
Quick Feedback Service - 輕量 AI 回饋服務

使用輕量級 Gemini Flash prompt 生成快速鼓勵訊息。
比 Rule-Based 更靈活，但需要 AI 呼叫（1-2 秒延遲）。
"""

import datetime
import logging
import time
from typing import Dict

from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


# 輕量 Prompt（< 100 tokens 輸出）
QUICK_FEEDBACK_PROMPT = """你是親子教養即時督導。

【當前對話】
{transcript}

請用 1 句話（20 字內）給家長即時鼓勵或提醒。

規則：
- 簡短、具體、正向
- 如果看到危險語言（威脅、暴力）→ 提醒冷靜
- 如果看到好的互動 → 肯定鼓勵
- 如果看到提問 → 鼓勵引導

只輸出一句話，不要額外說明。"""


class QuickFeedbackService:
    """輕量 AI 快速回饋服務"""

    def __init__(self):
        self.gemini_service = GeminiService()

    async def get_quick_feedback(self, recent_transcript: str) -> Dict[str, str]:
        """
        使用輕量 AI 生成快速回饋

        Args:
            recent_transcript: 最近 10 秒的逐字稿

        Returns:
            {
                "message": "AI 生成的鼓勵訊息",
                "type": "ai_generated",
                "timestamp": "當前時間",
                "latency_ms": 延遲時間
            }
        """
        start_time = time.time()

        try:
            # 建立 prompt
            prompt = QUICK_FEEDBACK_PROMPT.format(transcript=recent_transcript)

            # 呼叫 Gemini Flash（最快模型）
            response = await self.gemini_service.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=100,  # 限制輸出長度，加快速度
            )

            # 清理回應（去除多餘空白、引號）
            message = response.text.strip().strip("\"'")

            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "message": message,
                "type": "ai_generated",
                "timestamp": datetime.datetime.now().isoformat(),
                "latency_ms": latency_ms,
            }

        except Exception as e:
            logger.error(f"Quick feedback generation failed: {str(e)}")

            # Fallback to simple message
            return {
                "message": "繼續保持，你做得很好",
                "type": "fallback",
                "timestamp": datetime.datetime.now().isoformat(),
                "latency_ms": int((time.time() - start_time) * 1000),
                "error": str(e),
            }


# 創建全局實例
quick_feedback_service = QuickFeedbackService()
