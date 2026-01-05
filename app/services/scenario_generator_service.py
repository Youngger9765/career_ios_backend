"""
Scenario Generator Service - 情境自動生成服務

從逐字稿自動識別/生成 scenario 和 scenario_description
用於補充缺少情境資訊的 Session

預設使用 Gemini 2.5 Flash
"""

import logging
from typing import Optional, Tuple

from openai import AsyncOpenAI

from app.core.config import settings
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


class ScenarioGeneratorService:
    """情境生成服務 - 從逐字稿自動識別親子對話情境"""

    # Island Parents 預設情境選項
    SCENARIO_OPTIONS = [
        "homework",  # 功課/學習
        "grades",  # 成績
        "behavior",  # 行為問題
        "screen_time",  # 手機/3C使用
        "friends",  # 人際關係
        "emotions",  # 情緒問題
        "family",  # 家庭關係
        "custom",  # 自訂（無法分類時）
    ]

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

    async def generate_scenario(self, transcript: str) -> str:
        """
        從逐字稿識別情境類別

        Args:
            transcript: 會談逐字稿

        Returns:
            情境類別 key (e.g., "homework", "grades", "behavior")
        """
        try:
            transcript_preview = (
                transcript[:2000] if len(transcript) > 2000 else transcript
            )
            prompt = self._build_scenario_prompt(transcript_preview)

            if self.provider == "gemini":
                result = await self._generate_with_gemini(prompt)
            else:
                result = await self._generate_with_openai(prompt)

            # 驗證結果是否在選項中
            result = result.strip().lower()
            if result in self.SCENARIO_OPTIONS:
                logger.info(f"Generated scenario: {result}")
                return result

            logger.warning(f"Invalid scenario '{result}', using 'custom'")
            return "custom"

        except Exception as e:
            logger.error(f"Failed to generate scenario: {e}")
            return "custom"

    async def generate_scenario_description(self, transcript: str) -> str:
        """
        從逐字稿生成情境描述

        Args:
            transcript: 會談逐字稿

        Returns:
            情境描述文字（50字內）
        """
        try:
            transcript_preview = (
                transcript[:2000] if len(transcript) > 2000 else transcript
            )
            prompt = self._build_description_prompt(transcript_preview)

            if self.provider == "gemini":
                result = await self._generate_with_gemini(prompt)
            else:
                result = await self._generate_with_openai(prompt)

            result = result.strip()
            logger.info(f"Generated scenario_description: {result[:50]}...")
            return result

        except Exception as e:
            logger.error(f"Failed to generate scenario_description: {e}")
            return "親子對話"

    async def generate_both(self, transcript: str) -> Tuple[str, str]:
        """
        同時生成 scenario 和 scenario_description

        Args:
            transcript: 會談逐字稿

        Returns:
            (scenario, scenario_description) tuple
        """
        scenario = await self.generate_scenario(transcript)
        description = await self.generate_scenario_description(transcript)
        return scenario, description

    async def _generate_with_openai(self, prompt: str) -> str:
        """Generate using OpenAI"""
        response = await self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "你是親子對話分析專家，擅長從對話中識別親子互動的核心議題。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=100,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("OpenAI response content is None")
        return content.strip()

    async def _generate_with_gemini(self, prompt: str) -> str:
        """Generate using Gemini"""
        full_prompt = f"""你是親子對話分析專家，擅長從對話中識別親子互動的核心議題。

{prompt}"""

        response = await self.gemini_service.chat_completion(
            prompt=full_prompt,
            temperature=0.3,
            max_tokens=100,
        )

        return response.strip()

    def _build_scenario_prompt(self, transcript: str) -> str:
        """建立情境分類 prompt"""
        options_str = ", ".join(self.SCENARIO_OPTIONS)
        return f"""請從以下親子對話逐字稿中，識別主要的對話情境類別。

【可選類別】
- homework: 功課、學習、作業相關
- grades: 成績、考試、分數相關
- behavior: 行為問題、規矩、管教相關
- screen_time: 手機、電腦、3C使用相關
- friends: 人際關係、交友、同學相關
- emotions: 情緒問題、心情、壓力相關
- family: 家庭關係、兄弟姊妹、父母相關
- custom: 無法歸類到以上任何類別

【逐字稿】
{transcript}

【輸出要求】
請只輸出一個類別名稱（例如：homework），不要加任何解釋。
可選值：{options_str}"""

    def _build_description_prompt(self, transcript: str) -> str:
        """建立情境描述 prompt"""
        return f"""請從以下親子對話逐字稿中，用一句話（50字內）描述家長遇到的情境或煩惱。

【輸出要求】
1. 以家長視角描述（例如：「孩子回家後不願意寫功課」）
2. 簡潔具體，不超過 50 字
3. 直接輸出描述文字，不要加標題或說明

【逐字稿】
{transcript}

【範例輸出】
孩子每天放學後只想玩手機，叫他寫功課都不理我"""


# 全局實例
scenario_generator_service = ScenarioGeneratorService()
