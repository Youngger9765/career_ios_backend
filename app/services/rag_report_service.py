"""Service layer for RAG-powered report generation"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dialogue_extractor import DialogueExtractor
from app.services.gemini_service import gemini_service
from app.services.openai_service import OpenAIService
from app.services.rag_retriever import RAGRetriever
from app.services.transcript_parser import TranscriptParser


# Report schemas for structured output
class EnhancedReportSchema(BaseModel):
    """10段式增強報告結構"""

    section_2_main_issue: str = Field(description="二、主訴問題 - 個案陳述與諮詢師觀察")
    section_3_development: str = Field(
        description="三、問題發展脈絡 - 出現時間、持續頻率、影響程度"
    )
    section_4_help_seeking: str = Field(
        description="四、求助動機與期待 - 引發因素、期待目標"
    )
    section_5_multilevel_analysis: str = Field(
        description="五、多層次因素分析 - 個人、人際、環境、發展因素（必須引用理論[1][2]）"
    )
    section_6_strengths: str = Field(
        description="六、個案優勢與資源 - 心理優勢、社會資源"
    )
    section_7_professional_judgment: str = Field(
        description="七、諮詢師的專業判斷 - 問題假設、理論依據（必須引用理論[3][4]）"
    )
    section_8_goals_strategies: str = Field(
        description="八、諮商目標與介入策略 - SMART目標、介入技術（必須引用理論[5][6]）"
    )
    section_9_expected_outcomes: str = Field(
        description="九、預期成效與評估 - 短期指標、長期指標、可能調整"
    )
    section_10_self_reflection: str = Field(
        description="十、諮詢師自我反思 - 本次晤談優點和可改進處"
    )


class LegacyReportSchema(BaseModel):
    """5段式舊版報告結構"""

    main_issue: str = Field(description="主訴問題 - 個案說的，此次想要討論的議題")
    cause_analysis: str = Field(
        description="成因分析 - 諮詢師認為個案為何會有這些主訴問題，結合引用的理論[1][2]分析"
    )
    counseling_goal: str = Field(
        description="晤談目標（移動主訴）- 諮詢師對個案諮詢目標的假設"
    )
    intervention: str = Field(
        description="介入策略 - 諮詢師判斷會需要帶個案做的事，結合理論說明"
    )
    effectiveness: str = Field(description="目前成效評估 - 上述目標和策略達成的狀況")


class RAGReportService:
    """Service for RAG-powered report generation"""

    def __init__(
        self,
        openai_service: OpenAIService,
        db: AsyncSession,
        rag_system: str = "gemini",
    ):
        self.openai_service = openai_service
        self.db = db
        self.rag_system = rag_system

    async def parse_transcript(self, transcript: str) -> Dict[str, Any]:
        """Parse transcript to extract structured information

        Args:
            transcript: Raw transcript text

        Returns:
            Parsed data dictionary with client info, concerns, goals, etc.
        """
        parser = TranscriptParser(self.openai_service)
        parsed_result = await parser.parse(transcript)

        return {
            "client_name": parsed_result["client_info"]["name"],
            "gender": parsed_result["client_info"]["gender"],
            "age": parsed_result["client_info"]["age"],
            "occupation": parsed_result["client_info"]["occupation"],
            "education": parsed_result["client_info"]["education"],
            "location": parsed_result["client_info"]["location"],
            "economic_status": parsed_result["client_info"]["economic_status"],
            "family_relations": parsed_result["client_info"]["family_relations"],
            "other_info": parsed_result["client_info"]["other_info"],
            "main_concerns": parsed_result["main_concerns"],
            "counseling_goals": parsed_result["counseling_goals"],
            "counselor_techniques": parsed_result["counselor_techniques"],
            "session_content": parsed_result["session_content"],
            "counselor_self_evaluation": parsed_result["counselor_self_evaluation"],
        }

    async def search_theories(
        self,
        main_concerns: List[str],
        techniques: List[str],
        top_k: int,
        similarity_threshold: float,
    ) -> List[Dict[str, Any]]:
        """Search for relevant theories using RAG

        Args:
            main_concerns: List of main concerns from transcript
            techniques: List of counseling techniques used
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score

        Returns:
            List of theory dictionaries with text, document, and score
        """
        search_terms = main_concerns[:3] + techniques[:2]
        search_query = " ".join(search_terms) if search_terms else "職涯諮詢 生涯發展"

        retriever = RAGRetriever(self.openai_service)
        theories = await retriever.search(
            query=search_query,
            top_k=top_k,
            threshold=similarity_threshold,
            db=self.db,
        )

        return theories

    def build_rag_instruction(self, num_theories: int) -> str:
        """Build RAG instruction for theory citation

        Args:
            num_theories: Number of theories available for citation

        Returns:
            RAG instruction string
        """
        return f"""
⚠️⚠️⚠️ 重要：理論引用規則 ⚠️⚠️⚠️

你【必須】使用以下 RAG 檢索到的 {num_theories} 個理論文獻，【不可】使用你自己記憶中的理論！

引用時：
1. 必須從 [1] 到 [{num_theories}] 中選擇
2. 必須提取文獻來源或內容中的理論名稱（例如：Super 生涯發展理論、Holland 類型論、認知行為理論）
3. 引用格式：「根據 [理論名稱] [數字]，...」
4. 如果文獻中沒有明確理論名稱，則引用「來源文獻名稱 [數字]」

範例：
✅ 正確：「根據 Super 生涯發展理論 [1]，案主處於探索期...」（如果 [1] 的內容或來源提到 Super）
✅ 正確：「依據職涯諮詢精選文章 [3]，...」（如果不知道具體理論名稱，用文獻名）
❌ 錯誤：引用 RAG 未提供的理論（例如 Freud、Maslow 等，如果它們不在下列文獻中）
❌ 錯誤：「根據理論 [1]」（沒有說明理論名稱）
"""

    def build_theory_context(self, theories: List[Dict[str, Any]]) -> str:
        """Build formatted theory context for prompt

        Args:
            theories: List of theory dictionaries

        Returns:
            Formatted context string
        """
        context_parts = []
        for i, theory in enumerate(theories):
            doc_title = theory.get("document", "未知文獻")
            theory_text = theory["text"]
            score = theory["score"]

            context_parts.append(
                f"[{i+1}] **來源文獻：{doc_title}**\n"
                f"   相似度分數：{score:.2f}\n"
                f"   內容：{theory_text}"
            )

        return "\n\n".join(context_parts)

    def build_legacy_prompt(
        self,
        parsed_data: Dict[str, Any],
        context: str,
        rag_instruction: str,
    ) -> str:
        """Build legacy 5-section report prompt

        Args:
            parsed_data: Parsed transcript data
            context: Theory context string
            rag_instruction: RAG citation instruction

        Returns:
            Legacy report prompt
        """
        main_concerns = parsed_data.get("main_concerns", [])
        techniques = parsed_data.get("counselor_techniques", [])

        return f"""{rag_instruction}

你是一位專業的職涯諮詢督導。請根據以下資訊生成個案報告：

**案主基本資料：**
- 姓名（化名）：{parsed_data.get('client_name', '未提供')}
- 性別：{parsed_data.get('gender', '未提及')}
- 年齡：{parsed_data.get('age', '未提及')}
- 部門/職業（學校科系）：{parsed_data.get('occupation', '未提及')}
- 學歷：{parsed_data.get('education', '未提及')}
- 現居地：{parsed_data.get('location', '未提及')}
- 經濟狀況：{parsed_data.get('economic_status', '未提及')}
- 家庭關係：{parsed_data.get('family_relations', '未提及')}
- 其他重要資訊：{', '.join(parsed_data.get('other_info', []))}

**晤談內容概述：**
{parsed_data.get('session_content', '')}

**主訴問題：**
{', '.join(main_concerns)}

**晤談目標：**
{', '.join(parsed_data.get('counseling_goals', []))}

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
1. ⚠️ 每個段落必須有實質內容，每段至少寫5-8句完整的段落文字，絕對不可只寫「-」、「無」、「待評估」或留空
2. 每個段落都要深入分析，提供具體的觀察、推論和建議
3. 請使用專業、客觀、具同理心的語氣
4. 適當引用理論文獻 [1], [2] 等
5. 不要使用 markdown 格式（如 ##, ###, **, - 等符號）
6. 使用【標題】的格式來區分段落
7. 內容直接書寫成段落，不要用項目符號或短句
"""

    def build_enhanced_prompt(
        self,
        parsed_data: Dict[str, Any],
        context: str,
        rag_instruction: str,
    ) -> str:
        """Build enhanced 10-section report prompt

        Args:
            parsed_data: Parsed transcript data
            context: Theory context string
            rag_instruction: RAG citation instruction

        Returns:
            Enhanced report prompt with rationale examples
        """
        main_concerns = parsed_data.get("main_concerns", [])
        techniques = parsed_data.get("counselor_techniques", [])

        prompt = f"""{rag_instruction}

你是職涯諮詢督導，協助新手諮詢師撰寫個案概念化報告。

你的優勢：快速從大量文獻中找到最適合此個案的理論和策略。

【案主資料】
- 姓名（化名）：{parsed_data.get('client_name', '未提供')}
- 性別：{parsed_data.get('gender', '未提及')}
- 年齡：{parsed_data.get('age', '未提及')}
- 部門/職業：{parsed_data.get('occupation', '未提及')}
- 學歷：{parsed_data.get('education', '未提及')}
- 現居地：{parsed_data.get('location', '未提及')}
- 經濟狀況：{parsed_data.get('economic_status', '未提及')}
- 家庭關係：{parsed_data.get('family_relations', '未提及')}

【晤談摘要】
{parsed_data.get('session_content', '')}

【主訴】{', '.join(main_concerns)}
【目標】{', '.join(parsed_data.get('counseling_goals', []))}
【技巧】{', '.join(techniques)}

【相關理論文獻】（請在適當段落引用 [1], [2]）
{context}

⚠️ 重要：請嚴格按照以下結構生成個案報告，段落【二】到【十】都必須完整包含！

【一、案主基本資料】
根據逐字稿提取的資訊整理如下（若逐字稿未提及則省略該項）：
- 姓名（化名）：{parsed_data.get('client_name', '未提供')}
{f"- 性別：{parsed_data.get('gender')}" if parsed_data.get('gender') != '未提及' else ""}
{f"- 年齡：{parsed_data.get('age')}" if parsed_data.get('age') != '未提及' else ""}
{f"- 部門/職業：{parsed_data.get('occupation')}" if parsed_data.get('occupation') != '未提及' else ""}
{f"- 學歷：{parsed_data.get('education')}" if parsed_data.get('education') != '未提及' else ""}
{f"- 現居地：{parsed_data.get('location')}" if parsed_data.get('location') != '未提及' else ""}
{f"- 經濟狀況：{parsed_data.get('economic_status')}" if parsed_data.get('economic_status') != '未提及' else ""}
{f"- 家庭關係：{parsed_data.get('family_relations')}" if parsed_data.get('family_relations') != '未提及' else ""}

註：本段僅呈現逐字稿中提及的資訊。若資訊不完整，不影響後續專業分析的品質。

【二、主訴問題】
- 個案陳述：（個案原話中的困擾）
- 諮詢師觀察：（你在晤談中觀察到的議題）

【三、問題發展脈絡】
- 出現時間：（何時開始）
- 持續頻率：（多久發生一次）
- 影響程度：（對生活/工作的影響）

【四、求助動機與期待】
- 引發因素：（為何此時求助）
- 期待目標：（希望改善什麼）

【五、多層次因素分析】⭐ 核心段落（必須引用理論 [1][2]）
分析以下層次，並引用理論：
- 個人因素：（年齡/生涯階段、性格、能力）
- 人際因素：（家庭、社會支持）
- 環境因素：（職場/學校、經濟）
- 發展因素：（生涯成熟度、早期經驗）

⚠️ 引用格式要求：必須包含「理論名稱 + [數字]」，例如：
✅ 正確：「根據 Super 生涯發展理論 [1]，案主處於探索期...」
✅ 正確：「從社會認知職業理論 (SCCT) [2] 的觀點來看...」
❌ 錯誤：「根據理論 [1]」（缺少理論名稱）
❌ 錯誤：「根據文獻」（沒有數字引用）

【六、個案優勢與資源】
- 心理優勢：（情緒調適、動機）
- 社會資源：（支持系統）

【七、諮詢師的專業判斷】⭐ 核心段落（必須引用理論 [3][4]）
- 問題假設：（為何有這些困擾）
- 理論依據：（用什麼理論支持判斷）引用 [3][4]
- 理論取向：（採用的觀點）

⚠️ 引用格式要求：必須包含「理論名稱 + [數字]」，例如：
✅ 正確：「基於認知行為理論 [3]，我認為問題源於...」
✅ 正確：「從 Holland 類型論 [4] 的角度來看...」
❌ 錯誤：「根據理論 [3]」（缺少理論名稱）

【八、諮商目標與介入策略】⭐ 核心段落（必須引用 [5][6]）
- 諮商目標：（SMART 格式，具體可衡量）
- 介入技術：（使用的方法）引用 [5][6]
- 技術理由：（為何這技術適合此個案）
- 介入步驟：（執行順序）

⚠️ 引用格式要求：必須包含「理論名稱 + [數字]」，例如：
✅ 正確：「選擇敘事治療技術 [5]，因為此方法能幫助案主重新建構生涯故事...」
✅ 正確：「根據焦點解決短期治療 (SFBT) [6]，設定具體可達成的目標...」
❌ 錯誤：「理論 [5] 指出...」（缺少理論名稱）

【九、預期成效與評估】
- 短期指標：（3 個月內如何判斷進步）
- 長期指標：（6-12 個月目標）
- 可能調整：（什麼情況需改變策略）

【十、諮詢師自我反思】
{parsed_data.get('counselor_self_evaluation', '請反思本次晤談優點和可改進處')}

格式要求：
1. 必須包含上述所有段落，用【】標題
2. 第五、七、八段落必須引用理論，格式為「理論名稱 [數字]」
3. 每個引用必須完整說明理論名稱，例如「Super 生涯發展理論 [1]」而非「理論 [1]」
4. 引用時要說明為何此理論適用於個案
5. 不用 markdown（##, **, -）
6. 每段至少 3-5 句，內容充實且具體
7. 必須考慮多層次因素：生理、心理、社會、文化
"""

        # Add rationale examples for enhanced version
        from app.utils.prompt_enhancer import add_rationale_examples

        return add_rationale_examples(prompt)

    async def generate_report_content(
        self, prompt: str, temperature: float = 0.6
    ) -> str:
        """Generate report content using LLM

        Args:
            prompt: Full report generation prompt
            temperature: LLM temperature parameter

        Returns:
            Generated report content
        """
        if self.rag_system == "gemini":
            return await gemini_service.chat_completion(prompt, temperature=temperature)
        else:
            return await self.openai_service.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=8000,
            )

    async def extract_dialogues(
        self, transcript: str, num_participants: int
    ) -> List[Dict[str, str]]:
        """Extract key dialogue excerpts from transcript

        Args:
            transcript: Raw transcript text
            num_participants: Number of participants in session

        Returns:
            List of dialogue dictionaries
        """
        service = self.openai_service if self.rag_system != "gemini" else gemini_service
        extractor = DialogueExtractor(service)
        return await extractor.extract(transcript, num_participants)

    def build_report_dict(
        self,
        parsed_data: Dict[str, Any],
        report_content: str,
        theories: List[Dict[str, Any]],
        dialogues: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Build final report dictionary

        Args:
            parsed_data: Parsed transcript data
            report_content: Generated report content
            theories: Retrieved theories
            dialogues: Extracted dialogue excerpts

        Returns:
            Complete report dictionary
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
            "session_summary": {
                "content": parsed_data.get("session_content", ""),
                "self_evaluation": parsed_data.get("counselor_self_evaluation", ""),
            },
            "conceptualization": report_content,
            "main_concerns": parsed_data.get("main_concerns", []),
            "counseling_goals": parsed_data.get("counseling_goals", []),
            "techniques": parsed_data.get("counselor_techniques", []),
            "theories": theories,
            "dialogue_excerpts": dialogues,
        }

    async def generate_quality_summary(
        self, report: Dict[str, Any], report_text: str, use_legacy: bool
    ) -> Optional[Dict[str, Any]]:
        """Generate quality assessment summary for report

        Args:
            report: Complete report dictionary
            report_text: Generated report text
            use_legacy: Whether using legacy format

        Returns:
            Quality summary dictionary or None
        """
        from app.utils.report_quality import generate_quality_summary_with_llm

        return await generate_quality_summary_with_llm(
            report=report,
            report_text=report_text,
            theories=report["theories"],
            use_legacy=use_legacy,
            openai_client=self.openai_service.client,
        )
