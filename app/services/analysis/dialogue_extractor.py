"""
DialogueExtractor Service - 提取關鍵對話片段

Extracted from app/api/rag_report.py to follow SRP (Single Responsibility Principle)
"""

import json
import re
from typing import Dict, List

from app.services.external.gemini_service import GeminiService
from app.services.external.openai_service import OpenAIService


class DialogueExtractor:
    """提取關鍵對話片段 (5-10 句)"""

    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def extract(self, transcript: str, num_participants: int) -> List[Dict]:
        """
        Extract 5-10 key dialogue excerpts from transcript

        Args:
            transcript: Full counseling session transcript
            num_participants: Number of speakers (2 or 3)

        Returns:
            [
                {
                    "speaker": "speaker1",
                    "order": 1,
                    "text": "對話內容..."
                },
                ...
            ]
        """
        excerpt_prompt = self._build_excerpt_prompt(transcript, num_participants)

        # Call LLM to extract dialogues
        # Check if using GeminiService and use appropriate method
        if isinstance(self.openai_service, GeminiService):
            response = await self.openai_service.chat_completion_with_messages(
                messages=[{"role": "user", "content": excerpt_prompt}],
                temperature=0.3,  # Low temperature for consistency
            )
        else:
            response = await self.openai_service.chat_completion(
                messages=[{"role": "user", "content": excerpt_prompt}],
                temperature=0.3,  # Low temperature for consistency
            )

        # Parse JSON from response
        dialogues = self._extract_dialogues_from_response(response)

        return dialogues

    def _build_excerpt_prompt(self, transcript: str, num_participants: int) -> str:
        """Build LLM prompt for extracting key dialogues"""
        # Build speaker labels and examples based on num_participants
        if num_participants == 2:
            speaker_instruction = (
                '- speaker 使用 "speaker1"（通常為諮詢師）和 "speaker2"（通常為個案）'
            )
            speaker_example = """  "dialogues": [
    {{"speaker": "speaker1", "order": 1, "text": "諮詢師的話"}},
    {{"speaker": "speaker2", "order": 2, "text": "個案的話"}},
    {{"speaker": "speaker1", "order": 3, "text": "諮詢師的話"}}
  ]"""
        else:
            speaker_labels = ", ".join(
                [f'"speaker{i+1}"' for i in range(num_participants)]
            )
            speaker_instruction = (
                f"- speaker 使用 {speaker_labels}，根據逐字稿上下文判斷每位說話者"
            )
            speaker_example = """  "dialogues": [
    {{"speaker": "speaker1", "order": 1, "text": "說話內容"}},
    {{"speaker": "speaker2", "order": 2, "text": "說話內容"}},
    {{"speaker": "speaker1", "order": 3, "text": "說話內容"}}
  ]"""

        return f"""請從以下逐字稿中，挑選 5-10 句最能體現個案樣貌和諮詢重點的關鍵對話。

逐字稿：
{transcript}

會談人數：{num_participants} 人

請以 JSON 格式回答（只要 JSON，不要其他文字）：
{{
{speaker_example}
}}

注意：
{speaker_instruction}
- 請根據逐字稿的語境和內容，自動判斷每句話是誰說的
- order 是對話順序編號
- 挑選能展現個案核心議題、情緒狀態、或關鍵轉變的對話
- 如果逐字稿中有明確標示說話者（如 Co:、Cl:、諮詢師：、個案：等），請參考這些標示
"""

    def _extract_dialogues_from_response(self, response: str) -> List[Dict]:
        """
        Extract dialogues from LLM response (handles extra text or malformed JSON)

        Args:
            response: Raw LLM response

        Returns:
            List of dialogue dicts, or empty list if parsing fails
        """
        try:
            # Try direct JSON parsing first
            data = json.loads(response)
            return data.get("dialogues", [])
        except json.JSONDecodeError:
            # If fails, try to extract JSON from surrounding text
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                    return data.get("dialogues", [])
                except json.JSONDecodeError:
                    pass

            # Fallback to empty list
            return []
