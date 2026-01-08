"""
Quick Feedback Service - 輕量 AI 回饋服務

使用輕量級 Gemini Flash prompt 判斷安全等級，
然後從 200 句專家建議中選擇最適合的回饋。

改進：不再讓 AI 自由生成文字，而是從預設的 200 句短建議中選擇，
確保顯示在同心圓 UI 中的文字足夠簡短（平均 9 字）。
"""

import datetime
import json
import logging
import time
from typing import Dict, Optional

from app.config.parenting_suggestions import (
    GREEN_SUGGESTIONS,
    RED_SUGGESTIONS,
    YELLOW_SUGGESTIONS,
)
from app.services.external.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class QuickFeedbackService:
    """輕量 AI 快速回饋服務 - 使用 200 句專家建議"""

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
        使用 AI 判斷安全等級，然後從 200 句專家建議中選擇

        Args:
            recent_transcript: 最近 15 秒的逐字稿（重點分析對象）
            full_transcript: 完整累積逐字稿（背景脈絡）
            tenant_id: 租戶 ID
            mode: 模式 ("practice" 練習模式 / "emergency" 對談模式)
            scenario_context: 家長煩惱情境描述

        Returns:
            {
                "message": "從 200 句中選出的專家建議",
                "type": "expert_suggestion",
                "timestamp": "當前時間",
                "latency_ms": 延遲時間
            }
        """
        start_time = time.time()

        # Use full_transcript as fallback if not provided
        if full_transcript is None:
            full_transcript = recent_transcript

        try:
            # Step 1: 判斷安全等級 + 選擇建議（單一 Gemini 呼叫）
            (
                safety_level,
                message,
                prompt_tokens,
                completion_tokens,
            ) = await self._analyze_and_select(
                recent_transcript, full_transcript, mode, scenario_context
            )

            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "message": message,
                "type": "expert_suggestion",
                "timestamp": datetime.datetime.now().isoformat(),
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            }

        except Exception as e:
            logger.error(f"Quick feedback generation failed: {str(e)}")

            # Fallback to default green suggestion
            return {
                "message": GREEN_SUGGESTIONS[0],  # "讓孩子知道你站在他這邊"
                "type": "fallback",
                "timestamp": datetime.datetime.now().isoformat(),
                "latency_ms": int((time.time() - start_time) * 1000),
                "error": str(e),
            }

    async def _analyze_and_select(
        self,
        recent_transcript: str,
        full_transcript: str,
        mode: Optional[str],
        scenario_context: Optional[str],
    ) -> tuple:
        """
        單一 Gemini 呼叫：判斷安全等級 + 從 200 句中選擇建議

        Returns:
            (safety_level, selected_suggestion, prompt_tokens, completion_tokens)
        """
        # Build suggestion lists for prompt
        green_list = "\n".join([f"  - {s}" for s in GREEN_SUGGESTIONS])
        yellow_list = "\n".join([f"  - {s}" for s in YELLOW_SUGGESTIONS])
        red_list = "\n".join([f"  - {s}" for s in RED_SUGGESTIONS])

        # Mode-specific context
        mode_context = ""
        if mode == "practice":
            mode_context = """⚠️ 模式：Practice（單人練習）
- 只有家長一人在練習說話，沒有孩子在場
- 分析重點：評估「家長的說話技巧」"""
        else:
            mode_context = """⚠️ 模式：Emergency（即時介入）
- 真實親子對話現場
- 分析重點：評估「親子互動的狀態」"""

        # Scenario context
        scenario_section = ""
        if scenario_context:
            scenario_section = f"\n【家長煩惱情境】\n{scenario_context}\n"

        prompt = f"""你是親子溝通專家。請分析以下對話，判斷安全等級並選擇最適合的專家建議。

{mode_context}
{scenario_section}
【完整對話背景】
{full_transcript[:500]}

【最近 15 秒 - 重點分析】
{recent_transcript}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【任務】
1. 判斷安全等級（green/yellow/red）
2. 從對應的建議庫中選擇 1 句最適合的建議

【安全等級標準】
- green：溝通順暢、情緒穩定、互相尊重
- yellow：溝通不良、情緒緊張、忽略需求
- red：情緒崩潰、衝突升級、語言暴力

【建議句庫 - 請逐字選擇，不要改寫】

🟢 GREEN 建議：
{green_list}

🟡 YELLOW 建議：
{yellow_list}

🔴 RED 建議：
{red_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
請回傳 JSON 格式：
{{"safety_level": "green", "suggestion": "你正在聽，而不是急著回"}}

CRITICAL:
1. suggestion 必須從上述建議庫中逐字選擇，不要改寫或自創
2. 所有回應必須使用繁體中文（zh-TW）"""

        response = await self.gemini_service.generate_text(
            prompt=prompt,
            temperature=0.3,  # Lower temperature for more consistent selection
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        # Extract text and usage metadata
        text = response.text
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage_metadata"):
            usage = response.usage_metadata
            prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
            completion_tokens = getattr(usage, "candidates_token_count", 0) or 0

        # Parse JSON response
        try:
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(text[json_start:json_end])
                safety_level = result.get("safety_level", "green").lower()
                suggestion = result.get("suggestion", "")

                # Validate safety level
                if safety_level not in ["green", "yellow", "red"]:
                    safety_level = "green"

                # Validate suggestion is from our pool
                all_suggestions = (
                    GREEN_SUGGESTIONS + YELLOW_SUGGESTIONS + RED_SUGGESTIONS
                )
                if suggestion not in all_suggestions:
                    # AI generated something not in our list, pick a default
                    logger.warning(
                        f"AI generated suggestion not in pool: '{suggestion}', using default"
                    )
                    if safety_level == "green":
                        suggestion = GREEN_SUGGESTIONS[0]
                    elif safety_level == "yellow":
                        suggestion = YELLOW_SUGGESTIONS[0]
                    else:
                        suggestion = RED_SUGGESTIONS[0]

                return safety_level, suggestion, prompt_tokens, completion_tokens

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")

        # Fallback
        return "green", GREEN_SUGGESTIONS[0], prompt_tokens, completion_tokens


# 創建全局實例
quick_feedback_service = QuickFeedbackService()
