"""
TranscriptParser Service - 解析逐字稿提取關鍵資訊

Extracted from app/api/rag_report.py to follow SRP (Single Responsibility Principle)
"""

import json
import re
from typing import Dict

from app.services.openai_service import OpenAIService


class TranscriptParser:
    """解析逐字稿，提取關鍵資訊"""

    def __init__(self, openai_service: OpenAIService):
        self.openai_service = openai_service

    async def parse(self, transcript: str) -> Dict:
        """
        Parse transcript and extract key information using LLM

        Args:
            transcript: Counseling session transcript

        Returns:
            {
                "client_info": {
                    "name": str,
                    "gender": str,
                    "age": str,
                    "occupation": str,
                    "education": str,
                    "location": str,
                    "economic_status": str,
                    "family_relations": str,
                    "other_info": List[str]
                },
                "main_concerns": List[str],
                "counseling_goals": List[str],
                "counselor_techniques": List[str],
                "session_content": str,
                "counselor_self_evaluation": str
            }
        """
        parse_prompt = self._build_parse_prompt(transcript)

        # Call LLM to parse transcript
        response = await self.openai_service.chat_completion(
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0.3
        )

        # Parse JSON from response
        parsed_data = self._extract_json_from_response(response)

        # Transform to standardized format
        return self._transform_to_standard_format(parsed_data)

    def _build_parse_prompt(self, transcript: str) -> str:
        """Build LLM prompt for parsing transcript"""
        return f"""請分析以下職涯諮詢逐字稿，提取關鍵資訊：

逐字稿：
{transcript}

請以 JSON 格式回答（只要 JSON，不要其他文字）：
{{
  "client_name": "案主化名",
  "gender": "性別",
  "age": "年齡（若未提及則填'未提及'）",
  "occupation": "部門/職業或學校科系",
  "education": "學歷（若未提及則填'未提及'）",
  "location": "現居地（若未提及則填'未提及'）",
  "economic_status": "經濟狀況描述（若未提及則填'未提及'）",
  "family_relations": "家庭關係描述",
  "other_info": ["其他重要資訊1", "其他重要資訊2"],
  "main_concerns": ["主訴問題1", "主訴問題2"],
  "counseling_goals": ["晤談目標1", "晤談目標2"],
  "counselor_techniques": ["使用的諮詢技巧1", "技巧2"],
  "session_content": "晤談內容概述",
  "counselor_self_evaluation": "諮詢師對本次晤談的自我評估"
}}
"""

    def _extract_json_from_response(self, response: str) -> Dict:
        """
        Extract JSON from LLM response (handles extra text or malformed JSON)

        Args:
            response: Raw LLM response (may contain JSON)

        Returns:
            Parsed JSON dict, or default dict if parsing fails
        """
        try:
            # Try direct JSON parsing first
            return json.loads(response)
        except json.JSONDecodeError:
            # If fails, try to extract JSON from surrounding text
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    pass

            # Fallback to default structure
            return self._get_default_parsed_data()

    def _get_default_parsed_data(self) -> Dict:
        """Return default structure when parsing fails"""
        return {
            "client_name": "未提供",
            "gender": "未提及",
            "age": "未提及",
            "occupation": "未提及",
            "education": "未提及",
            "location": "未提及",
            "economic_status": "未提及",
            "family_relations": "未提及",
            "other_info": [],
            "main_concerns": [],
            "counseling_goals": [],
            "counselor_techniques": [],
            "session_content": "無法解析",
            "counselor_self_evaluation": "無法解析",
        }

    def _transform_to_standard_format(self, parsed_data: Dict) -> Dict:
        """
        Transform LLM response to standardized format

        Separates client_info from other fields for better structure
        """
        return {
            "client_info": {
                "name": parsed_data.get("client_name", "未提供"),
                "gender": parsed_data.get("gender", "未提及"),
                "age": parsed_data.get("age", "未提及"),
                "occupation": parsed_data.get("occupation", "未提及"),
                "education": parsed_data.get("education", "未提及"),
                "location": parsed_data.get("location", "未提及"),
                "economic_status": parsed_data.get("economic_status", "未提及"),
                "family_relations": parsed_data.get("family_relations", "未提及"),
                "other_info": parsed_data.get("other_info", []),
            },
            "main_concerns": parsed_data.get("main_concerns", []),
            "counseling_goals": parsed_data.get("counseling_goals", []),
            "counselor_techniques": parsed_data.get("counselor_techniques", []),
            "session_content": parsed_data.get("session_content", ""),
            "counselor_self_evaluation": parsed_data.get("counselor_self_evaluation", ""),
        }
