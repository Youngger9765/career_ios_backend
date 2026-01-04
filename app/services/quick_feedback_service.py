"""
Quick Feedback Service - 輕量 AI 回饋服務

使用輕量級 Gemini Flash prompt 生成快速鼓勵訊息。
比 Rule-Based 更靈活，但需要 AI 呼叫（1-2 秒延遲）。
"""

import datetime
import logging
import time
from typing import Dict, Optional

from app.prompts import PromptRegistry
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class QuickFeedbackService:
    """輕量 AI 快速回饋服務"""

    def __init__(self):
        self.gemini_service = GeminiService()

    async def get_quick_feedback(
        self,
        recent_transcript: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        使用輕量 AI 生成快速回饋

        Args:
            recent_transcript: 最近 10 秒的逐字稿
            tenant_id: 租戶 ID（用於選擇對應的 prompt）

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
            # 從 PromptRegistry 取得對應的 prompt
            prompt_template = PromptRegistry.get_prompt(
                tenant_id or "island_parents",
                "quick",
            )
            prompt = prompt_template.format(transcript_segment=recent_transcript)

            # 呼叫 Gemini Flash（最快模型）
            # Strategy: Set high max_tokens as safety ceiling
            # - max_output_tokens (Vertex AI) only counts OUTPUT, not input
            # - Actual length controlled by prompt: "請用 1 句話（20 字內）"
            # - 1000 tokens prevents truncation while giving budget for formatting
            response = await self.gemini_service.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=1000,  # 足夠的輸出空間，由 prompt 指示控制實際長度
            )

            # 清理回應（去除多餘空白、引號、換行符號）
            message = response.text.strip().strip("\"'")
            # Remove any line breaks to ensure single line
            message = message.replace("\n", "").replace("\r", "")

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
