"""
Expert Suggestion Service - AI-powered suggestion selection from expert pools

Extracted from keyword_analysis_service.py for better modularity.
"""

import json
import logging
import random
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.services.external.gemini_service import GeminiService

logger = logging.getLogger(__name__)


async def select_expert_suggestions(
    transcript: str,
    safety_level: str,
    num_suggestions: int = 2,
    gemini_service: "GeminiService" = None,
) -> List[str]:
    """
    從 200 句專家建議中使用 AI 挑選最適合的建議

    Args:
        transcript: 對話逐字稿
        safety_level: 安全等級 (green/yellow/red)
        num_suggestions: 要挑選的建議數量（固定為 1 條）
        gemini_service: Gemini API service

    Returns:
        List of selected suggestions (1 sentence, max 200 chars)
    """
    # Import suggestions from config
    from app.config.parenting_suggestions import (
        GREEN_SUGGESTIONS,
        RED_SUGGESTIONS,
        YELLOW_SUGGESTIONS,
    )

    # Select suggestion pool based on safety level
    if safety_level == "green":
        pool = GREEN_SUGGESTIONS
    elif safety_level == "yellow":
        pool = YELLOW_SUGGESTIONS
    else:  # red
        pool = RED_SUGGESTIONS

    # Build prompt for AI to select suggestions
    suggestions_list = "\n".join([f"  - {s}" for s in pool])

    prompt = f"""從以下專家建議中選擇 {num_suggestions} 句最符合當前對話的建議：

【當前對話】
{transcript}

【專家建議句庫】
{suggestions_list}

請選擇 {num_suggestions} 句最適合的建議。
規則：
1. 必須從上述建議中逐字選擇，不要改寫
2. 選擇最符合當前情境的建議
3. **每句建議必須在 200 字以內**（優先選擇簡短的建議）
4. 輸出 JSON 格式：{{"suggestions": ["句子1", "句子2"]}}

CRITICAL: 所有回應必須使用繁體中文（zh-TW），不可使用簡體中文。
"""

    try:
        # Call Gemini to select suggestions
        response = await gemini_service.generate_text(
            prompt, temperature=0.3, response_format={"type": "json_object"}
        )

        # Extract text from response object if needed
        if hasattr(response, "text"):
            response_text = response.text
        else:
            response_text = str(response)

        # Parse JSON
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
            suggestions = result.get("suggestions", [])

            # CRITICAL: Enforce 200-character limit to prevent UI overflow
            max_chars = 200
            truncated_suggestions = []
            for sug in suggestions:
                if len(sug) > max_chars:
                    # Truncate and add ellipsis
                    truncated = sug[: max_chars - 3] + "..."
                    logger.warning(
                        f"Suggestion truncated from {len(sug)} to {max_chars} chars: "
                        f"'{sug[:50]}...'"
                    )
                    truncated_suggestions.append(truncated)
                else:
                    truncated_suggestions.append(sug)

            return truncated_suggestions
        else:
            # Fallback: return random suggestions
            return random.sample(pool, min(num_suggestions, len(pool)))

    except Exception as e:
        logger.warning(f"Failed to select expert suggestions: {e}")
        # Fallback: return first N suggestions from pool
        return pool[:num_suggestions]


# Backward compatibility alias
_select_expert_suggestions = select_expert_suggestions
