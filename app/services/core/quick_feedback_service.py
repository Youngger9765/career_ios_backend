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
from app.services.external.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class QuickFeedbackService:
    """輕量 AI 快速回饋服務"""

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
        使用輕量 AI 生成快速回饋

        Args:
            recent_transcript: 最近 15 秒的逐字稿（重點分析對象）
            full_transcript: 完整累積逐字稿（背景脈絡）
            tenant_id: 租戶 ID（用於選擇對應的 prompt）
            mode: 模式 ("practice" 練習模式 / "emergency" 對談模式)
                  - practice: 家長獨自練習，沒有孩子在場
                  - emergency: 真實親子互動現場
            scenario_context: 家長煩惱情境描述（用於引導分析方向）

        Returns:
            {
                "message": "AI 生成的鼓勵訊息",
                "type": "ai_generated",
                "timestamp": "當前時間",
                "latency_ms": 延遲時間
            }
        """
        start_time = time.time()

        # Use full_transcript as fallback if not provided
        if full_transcript is None:
            full_transcript = recent_transcript

        try:
            # 從 PromptRegistry 取得對應的 prompt（支援 mode）
            prompt_template = PromptRegistry.get_prompt(
                tenant_id or "island_parents",
                "quick",
                mode=mode or "practice",  # Default to practice mode
            )

            # Prepend scenario context if provided
            scenario_prefix = ""
            if scenario_context:
                scenario_prefix = f"{scenario_context}\n\n"

            # Format with both transcripts
            prompt = prompt_template.format(
                transcript_segment=recent_transcript,
                full_transcript=full_transcript,
            )
            # Add scenario context at the beginning
            prompt = scenario_prefix + prompt

            # 呼叫 Gemini 3 Flash（最快模型）
            # Strategy: Set high max_tokens as safety ceiling
            # - max_output_tokens (Vertex AI) only counts OUTPUT, not input
            # - Actual length controlled by prompt: "請用 1 句話（20 字內）"
            # - 1000 tokens prevents truncation while giving budget for formatting
            response = await self.gemini_service.generate_text(
                prompt=prompt,
                temperature=0.7,
                max_tokens=1000,  # 足夠的輸出空間，由 prompt 指示控制實際長度
            )

            # Extract text and usage metadata from Gemini response
            text = response.text
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
                completion_tokens = getattr(usage, "candidates_token_count", 0) or 0

            # 清理回應（去除多餘空白、引號、換行符號）
            message = text.strip().strip("\"'")
            # Remove any line breaks to ensure single line
            message = message.replace("\n", "").replace("\r", "")

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
