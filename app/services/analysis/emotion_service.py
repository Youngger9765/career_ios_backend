"""
Emotion Analysis Service for Island Parents
Real-time emotion feedback on parent-child communication
"""
import asyncio
import logging
from typing import Tuple

from app.services.external.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class EmotionAnalysisService:
    """
    Service for analyzing parent-child communication emotion levels.

    Provides real-time feedback using Gemini Flash Lite Latest model
    with strict response time requirements (<3 seconds).
    """

    def __init__(self):
        # Use Gemini Flash Lite Latest for fast responses
        self.gemini_service = GeminiService(
            model_name="models/gemini-flash-lite-latest"
        )

    def _build_system_prompt(self) -> str:
        """Build system prompt for emotion analysis"""
        return """你是親子溝通專家，負責即時分析家長對話的情緒狀態。
請根據對話上下文和目標句子，評估情緒層級並提供簡短引導。

情緒層級定義：
1. 綠燈（良好）：語氣平和、具同理心、建設性溝通
2. 黃燈（警告）：語氣稍顯急躁、帶有責備但未失控
3. 紅燈（危險）：語氣激動、攻擊性強、可能傷害親子關係

回應格式（嚴格遵守）：
數字|引導語

規則：
- 數字必須是 1, 2, 或 3
- 引導語必須 ≤17 字（中文字符）
- 用 | 分隔數字和引導語
- 引導語要具體、可行、同理

範例：
3|試著同理孩子的挫折感
2|深呼吸，用平和語氣重述
1|很好的同理心表達"""

    def _build_user_prompt(self, context: str, target: str) -> str:
        """Build user prompt with context and target"""
        return f"""
對話上下文：
{context}

目標句子（需分析）：
{target}

請評估目標句子的情緒層級並提供引導語。"""

    def _parse_llm_response(self, response: str) -> Tuple[int, str]:
        """
        Parse LLM response in format: number|hint

        Args:
            response: LLM response string

        Returns:
            Tuple of (level, hint)

        Raises:
            ValueError: If response format is invalid
        """
        parts = response.strip().split("|")

        if len(parts) != 2:
            raise ValueError(
                f"Invalid format: expected 'number|text', got '{response}'"
            )

        # Parse level
        level_str, hint = parts
        try:
            level = int(level_str)
        except ValueError:
            raise ValueError(f"Invalid level: expected integer, got '{level_str}'")

        if level not in [1, 2, 3]:
            raise ValueError(f"Invalid level: expected 1/2/3, got {level}")

        # Validate hint length (17 chars max)
        if len(hint) > 17:
            logger.warning(f"Hint too long ({len(hint)} chars), truncating: {hint}")
            hint = hint[:17]

        return level, hint

    async def analyze_emotion(
        self, context: str, target: str, timeout: float = 2.5
    ) -> dict:
        """
        Analyze emotion level of target sentence in given context.

        Args:
            context: Conversation context
            target: Target sentence to analyze
            timeout: Timeout in seconds (default: 2.5s to allow 0.5s for processing)

        Returns:
            Dictionary with:
            - level: 1 (green), 2 (yellow), 3 (red)
            - hint: Guidance hint (≤17 chars)
            - token_usage: Token usage statistics

        Raises:
            asyncio.TimeoutError: If LLM call exceeds timeout
            ValueError: If response parsing fails
        """
        # Build prompts
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(context, target)

        # Combine system and user prompts
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        try:
            # Call Gemini with timeout
            response_text = await asyncio.wait_for(
                self.gemini_service.chat_completion(
                    prompt=full_prompt,
                    temperature=0,  # Ensure stable output
                    max_tokens=50,  # Just enough for "number|hint"
                ),
                timeout=timeout,
            )

            logger.info(f"Gemini response: {response_text}")

            # Parse response
            level, hint = self._parse_llm_response(response_text)

            # Get token usage from last call
            token_usage = self.gemini_service.get_last_token_usage()

            return {
                "level": level,
                "hint": hint,
                "token_usage": token_usage,
            }

        except asyncio.TimeoutError:
            logger.error(f"Emotion analysis timeout after {timeout}s")
            raise

        except ValueError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Fallback to yellow light with generic hint
            logger.warning("Using fallback: level=2, generic hint")
            return {
                "level": 2,
                "hint": "請試著用平和語氣溝通",
                "token_usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                },
            }

        except Exception as e:
            logger.error(f"Emotion analysis failed: {e}")
            raise
