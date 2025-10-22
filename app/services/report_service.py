"""Report Generation Service - 整合 RAG Agent 生成個案報告"""

import logging
from typing import Dict, List, Optional

import httpx
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class ReportGenerationService:
    """個案報告生成服務 - 整合 RAG Agent"""

    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.chat_model = settings.OPENAI_CHAT_MODEL or "gpt-4o-mini"

    async def generate_report_from_transcript(
        self,
        transcript: str,
        agent_id: Optional[int] = None,
        num_participants: int = 2,
    ) -> Dict:
        """
        從逐字稿生成個案報告

        流程:
        1. 解析逐字稿基本資訊
        2. 調用 RAG Agent 檢索相關理論
        3. 整合檢索結果，GPT-4 生成結構化報告

        Args:
            transcript: 會談逐字稿
            agent_id: 使用的 RAG Agent ID（可選）
            num_participants: 會談人數（預設2人）

        Returns:
            {
                "content_json": {...},  # 結構化報告內容
                "citations_json": [...],  # 理論引用
                "agent_id": int,
                "metadata": {...}
            }
        """

        # Step 1: 解析逐字稿基本資訊
        parsed_info = await self._parse_transcript_info(transcript)

        # Step 2: 調用 RAG Agent 檢索相關理論
        main_concerns = parsed_info.get("main_concerns", [])
        search_query = " ".join(main_concerns[:3])  # 取前3個關鍵議題

        citations = await self._retrieve_theories(search_query, agent_id)

        # Step 3: 生成結構化報告
        report_content = await self._generate_structured_report(
            transcript=transcript,
            parsed_info=parsed_info,
            citations=citations,
            num_participants=num_participants,
        )

        # Step 4: 提取關鍵對話片段
        dialogue_excerpts = await self._extract_key_dialogues(
            transcript, num_participants
        )

        return {
            "content_json": {
                "client_info": parsed_info.get("client_info", {}),
                "session_summary": parsed_info.get("session_summary", {}),
                "main_concerns": main_concerns,
                "counseling_goals": parsed_info.get("counseling_goals", []),
                "techniques": parsed_info.get("counselor_techniques", []),
                "conceptualization": report_content,
                "dialogue_excerpts": dialogue_excerpts,
            },
            "citations_json": citations,
            "agent_id": agent_id,
            "metadata": {
                "model": self.chat_model,
                "num_citations": len(citations),
                "num_dialogues": len(dialogue_excerpts),
            },
        }

    async def _parse_transcript_info(self, transcript: str) -> Dict:
        """解析逐字稿基本資訊"""

        parse_prompt = f"""請分析以下職涯諮詢逐字稿，提取關鍵資訊：

逐字稿：
{transcript}

請以 JSON 格式回答（只要 JSON，不要其他文字）：
{{
  "client_info": {{
    "name": "案主化名",
    "gender": "性別",
    "age": "年齡（若未提及則填'未提及'）",
    "occupation": "部門/職業或學校科系",
    "education": "學歷（若未提及則填'未提及'）",
    "location": "現居地（若未提及則填'未提及'）",
    "economic_status": "經濟狀況描述（若未提及則填'未提及'）",
    "family_relations": "家庭關係描述"
  }},
  "main_concerns": ["主訴問題1", "主訴問題2"],
  "counseling_goals": ["晤談目標1", "晤談目標2"],
  "counselor_techniques": ["使用的諮詢技巧1", "技巧2"],
  "session_summary": {{
    "content": "晤談內容概述",
    "self_evaluation": "諮詢師對本次晤談的自我評估"
  }}
}}
"""

        response = await self.openai_client.chat.completions.create(
            model=self.chat_model,
            messages=[{"role": "user", "content": parse_prompt}],
            temperature=0.3,
        )

        import json
        import re

        response_text = response.choices[0].message.content

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                return {}

    async def _retrieve_theories(
        self, query: str, agent_id: Optional[int] = None
    ) -> List[Dict]:
        """調用 RAG Agent API 檢索理論"""

        try:
            # 內部調用 RAG Chat API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.APP_URL}/api/rag/chat",
                    json={
                        "question": query,
                        "agent_id": agent_id,
                        "top_k": 5,
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("citations", [])
                else:
                    return []

        except Exception as e:
            logger.error(f"RAG retrieval error: {e}", exc_info=True)
            return []

    async def _generate_structured_report(
        self,
        transcript: str,
        parsed_info: Dict,
        citations: List[Dict],
        num_participants: int,
    ) -> str:
        """生成結構化報告內容"""

        client_info = parsed_info.get("client_info", {})
        main_concerns = parsed_info.get("main_concerns", [])
        counseling_goals = parsed_info.get("counseling_goals", [])
        techniques = parsed_info.get("counselor_techniques", [])
        session_summary = parsed_info.get("session_summary", {})

        # 構建引用文獻
        context_parts = [f"[{i+1}] {c['text']}" for i, c in enumerate(citations)]
        context = "\n\n".join(context_parts)

        report_prompt = f"""你是一位專業的職涯諮詢督導。請根據以下資訊生成個案報告：

**案主基本資料：**
- 姓名（化名）：{client_info.get('name', '未提供')}
- 性別：{client_info.get('gender', '未提及')}
- 年齡：{client_info.get('age', '未提及')}
- 部門/職業（學校科系）：{client_info.get('occupation', '未提及')}
- 學歷：{client_info.get('education', '未提及')}
- 現居地：{client_info.get('location', '未提及')}
- 經濟狀況：{client_info.get('economic_status', '未提及')}
- 家庭關係：{client_info.get('family_relations', '未提及')}

**晤談內容概述：**
{session_summary.get('content', '')}

**主訴問題：**
{', '.join(main_concerns)}

**晤談目標：**
{', '.join(counseling_goals)}

**使用的諮詢技巧：**
{', '.join(techniques)}

**相關理論參考：**
{context}

請生成結構化的個案報告，包含以下部分：

【主訴問題】
個案說的，此次想要討論的議題

【成因分析】
諮詢師您認為，個案為何會有這些主訴問題，請結合引用的理論 [1], [2] 等進行分析

【晤談目標（移動主訴）】
諮詢師對個案諮詢目標的假設，須與個案確認

【介入策略】
諮詢師判斷會需要帶個案做的事，結合理論說明

【目前成效評估】
上述目標和策略達成的狀況如何，目前打算如何修正

重要提醒：
1. 請使用專業、客觀、具同理心的語氣
2. 適當引用理論文獻 [1], [2] 等
3. 不要使用 markdown 格式（如 ##, ###, **, - 等符號）
4. 使用【標題】的格式來區分段落
5. 內容直接書寫，不要用項目符號
"""

        response = await self.openai_client.chat.completions.create(
            model=self.chat_model,
            messages=[{"role": "user", "content": report_prompt}],
            temperature=0.6,
        )

        return response.choices[0].message.content

    async def _extract_key_dialogues(
        self, transcript: str, num_participants: int
    ) -> List[Dict]:
        """提取關鍵對話片段"""

        speaker_instruction = (
            '- speaker 使用 "speaker1"（通常為諮詢師）和 "speaker2"（通常為個案）'
            if num_participants == 2
            else f"- speaker 使用 {', '.join([f'speaker{i+1}' for i in range(num_participants)])}"
        )

        excerpt_prompt = f"""請從以下逐字稿中，挑選 5-10 句最能體現個案樣貌和諮詢重點的關鍵對話。

逐字稿：
{transcript}

會談人數：{num_participants} 人

請以 JSON 格式回答（只要 JSON，不要其他文字）：
{{
  "dialogues": [
    {{"speaker": "speaker1", "order": 1, "text": "對話內容"}},
    {{"speaker": "speaker2", "order": 2, "text": "對話內容"}}
  ]
}}

注意：
{speaker_instruction}
- order 是對話順序編號
- 挑選能展現個案核心議題、情緒狀態、或關鍵轉變的對話
"""

        response = await self.openai_client.chat.completions.create(
            model=self.chat_model,
            messages=[{"role": "user", "content": excerpt_prompt}],
            temperature=0.3,
        )

        import json
        import re

        response_text = response.choices[0].message.content

        try:
            data = json.loads(response_text)
            return data.get("dialogues", [])
        except json.JSONDecodeError:
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data.get("dialogues", [])
            else:
                return []


# Service instance
report_service = ReportGenerationService()
