"""Service layer for RAG-powered report generation"""

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dialogue_extractor import DialogueExtractor
from app.services.gemini_service import gemini_service
from app.services.openai_service import OpenAIService
from app.services.rag_retriever import RAGRetriever
from app.services.transcript_parser import TranscriptParser


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
