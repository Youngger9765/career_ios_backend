"""
Session Summary Service - 會談摘要生成服務

使用 LLM 從逐字稿生成簡潔的會談摘要（100字內）
用於歷程分析和快速瀏覽

預設使用 Gemini 2.5 Flash，可切換回 OpenAI
"""

import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


class SessionSummaryService:
    """會談摘要生成服務"""

    def __init__(self, provider: Optional[str] = None) -> None:
        """
        Initialize service with LLM provider

        Args:
            provider: "openai" or "gemini" (default: from settings.DEFAULT_LLM_PROVIDER)
        """
        self.provider = provider or settings.DEFAULT_LLM_PROVIDER

        # Initialize OpenAI client (always available as fallback)
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.openai_model = settings.OPENAI_CHAT_MODEL

        # Gemini is available via singleton
        self.gemini_service = gemini_service

    async def generate_summary(
        self,
        transcript: str,
        max_length: int = 100,
    ) -> Optional[str]:
        """
        從逐字稿生成會談摘要

        Args:
            transcript: 會談逐字稿
            max_length: 最大字數（預設 100 字）

        Returns:
            會談摘要文字，若失敗則返回 None

        Example:
            >>> summary = await service.generate_summary(transcript)
            >>> print(summary)
            "初談建立關係，確認諮詢目標與工作歷程。個案表現出疲憊與焦慮狀態，
            對主管衝突未顯意細談。顯示自信不足、逃避衝突傾向。"
        """
        try:
            # 截取前 3000 字避免超過 token 限制
            transcript_preview = (
                transcript[:3000] if len(transcript) > 3000 else transcript
            )

            prompt = self._build_summary_prompt(transcript_preview, max_length)

            # Use Gemini or OpenAI based on provider
            if self.provider == "gemini":
                summary = await self._generate_with_gemini(prompt)
            else:
                summary = await self._generate_with_openai(prompt)

            logger.info(f"Generated summary ({self.provider}): {len(summary)} chars")

            return summary

        except Exception as e:
            logger.error(f"Failed to generate summary with {self.provider}: {e}")
            # Fallback to OpenAI if Gemini fails
            if self.provider == "gemini":
                logger.info("Falling back to OpenAI...")
                try:
                    return await self._generate_with_openai(prompt)
                except Exception as e2:
                    logger.error(f"Fallback also failed: {e2}")
            return None

    async def _generate_with_openai(self, prompt: str) -> str:
        """Generate summary using OpenAI"""
        response = await self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是專業的諮商記錄助理，擅長從會談逐字稿中提煉核心要點，生成簡潔的會談摘要。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=200,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("OpenAI response content is None")
        return content.strip()

    async def _generate_with_gemini(self, prompt: str) -> str:
        """Generate summary using Gemini"""
        full_prompt = f"""你是專業的諮商記錄助理，擅長從會談逐字稿中提煉核心要點，生成簡潔的會談摘要。

{prompt}"""

        response = await self.gemini_service.chat_completion(
            prompt=full_prompt,
            temperature=0.3,
            max_tokens=200,
        )

        return response.strip()

    def _build_summary_prompt(self, transcript: str, max_length: int) -> str:
        """
        建立摘要生成 prompt

        Args:
            transcript: 逐字稿內容
            max_length: 最大字數

        Returns:
            完整的 prompt 文字
        """
        return f"""請從以下會談逐字稿中，生成一段簡潔的會談摘要（{max_length}字以內）。

【摘要要求】
1. 核心內容：本次會談的主要議題、活動（如：使用牌卡工具、探索職涯方向）
2. 個案狀態：情緒狀態、行為表現（如：焦慮、迴避、自信不足）
3. 關鍵發現：諮商師觀察到的重點（如：價值觀衝突、優勢特質）
4. 用詞專業：使用諮商專業用語，避免口語化
5. 字數限制：嚴格控制在 {max_length} 字以內

【逐字稿】
{transcript}

【輸出格式】
請直接輸出摘要文字，不要加任何標題或說明。範例：
"初談建立關係，確認諮詢目標與工作歷程。個案表現出疲憊與焦慮狀態，對主管衝突未顯意細談。顯示自信不足、逃避衝突傾向。"
"""

    async def batch_generate_summaries(
        self,
        sessions: list[tuple[str, str]],  # [(session_id, transcript), ...]
        max_length: int = 100,
    ) -> dict[str, Optional[str]]:
        """
        批次生成多個會談的摘要

        Args:
            sessions: 會談列表 [(session_id, transcript), ...]
            max_length: 最大字數

        Returns:
            {session_id: summary} 字典
        """
        results = {}

        for session_id, transcript in sessions:
            summary = await self.generate_summary(transcript, max_length)
            results[session_id] = summary
            logger.info(f"Generated summary for session {session_id}")

        return results


# 全局實例
session_summary_service = SessionSummaryService()
