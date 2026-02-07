"""
Parents Report Service - Generates parent-child dialogue reports

Extracted from session_analysis.py for better modularity.
Handles RAG retrieval, prompt construction, and report generation.
"""

import json
import logging
import re
import time
from typing import TYPE_CHECKING, Dict, List, Tuple

from sqlalchemy.orm import Session as DBSession

from app.services.utils.ai_validation import validate_ai_output_length

if TYPE_CHECKING:
    from app.models.session import Session
    from app.schemas.session import ParentsReportReference

logger = logging.getLogger(__name__)


class ParentsReportService:
    """Service for generating parent-child dialogue reports"""

    def __init__(self, db: DBSession):
        self.db = db

    async def generate_report(
        self,
        session: "Session",
        transcript: str,
        use_rag: bool = True,
    ) -> Tuple[Dict, List["ParentsReportReference"], List[str], int, Dict]:
        """
        Generate a parent-child dialogue report.

        Args:
            session: Session model with scenario info
            transcript: Full transcript text
            use_rag: Whether to use RAG for theory references

        Returns:
            Tuple of (analysis_dict, rag_references, rag_sources, latency_ms, token_usage)
        """
        from app.services.external.gemini_service import GeminiService

        start_time = time.time()

        # RAG: Retrieve relevant parenting theories
        rag_context = ""
        rag_sources = []
        rag_references = []

        if use_rag:
            rag_context, rag_sources, rag_references = await self._retrieve_rag_context(
                session, transcript
            )

        # Build prompt with optional RAG context
        prompt = self._build_report_prompt(session, transcript, rag_context)

        # Call Gemini
        gemini_service = GeminiService()
        gemini_response = await gemini_service.chat_completion(
            prompt=prompt,
            temperature=0.7,
            return_metadata=True,
        )

        llm_raw_response = gemini_response["text"]

        # Parse response
        analysis = self._parse_report_response(llm_raw_response)

        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Report generated in {latency_ms}ms")

        # Extract usage metadata from Gemini response
        usage_metadata = gemini_response.get("usage_metadata", {})
        prompt_tokens = usage_metadata.get("prompt_token_count", 0) or 0
        completion_tokens = usage_metadata.get("candidates_token_count", 0) or 0
        total_tokens = usage_metadata.get("total_token_count", 0) or 0

        # Calculate Gemini Flash 1.5 cost using centralized pricing
        from app.core.pricing import (
            GEMINI_1_5_FLASH_REPORT_INPUT_USD_PER_1M_TOKENS,
            GEMINI_1_5_FLASH_REPORT_OUTPUT_USD_PER_1M_TOKENS,
            calculate_gemini_cost,
        )

        estimated_cost_usd = calculate_gemini_cost(
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            input_price_per_1m=GEMINI_1_5_FLASH_REPORT_INPUT_USD_PER_1M_TOKENS,
            output_price_per_1m=GEMINI_1_5_FLASH_REPORT_OUTPUT_USD_PER_1M_TOKENS,
        )

        # Build token usage data
        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "model_name": gemini_service.model_name,
            "provider": "gemini",
            "llm_raw_response": llm_raw_response,
        }

        return analysis, rag_references, rag_sources, latency_ms, token_usage

    async def _retrieve_rag_context(
        self,
        session: "Session",
        transcript: str,
    ) -> Tuple[str, List[str], List["ParentsReportReference"]]:
        """Retrieve RAG context for report generation"""
        from app.schemas.session import ParentsReportReference
        from app.services.external.openai_service import OpenAIService
        from app.services.rag.rag_retriever import RAGRetriever

        rag_context = ""
        rag_sources = []
        rag_references = []

        try:
            openai_service = OpenAIService()
            rag_retriever = RAGRetriever(openai_service)

            # Build a more effective search query
            scenario_info = session.scenario or ""
            scenario_desc = session.scenario_description or ""
            search_query = f"{scenario_info} {scenario_desc}\n{transcript[:800]}"
            logger.info(f"RAG search query (first 200 chars): {search_query[:200]}...")

            # Search for parenting-related theories
            rag_results = await rag_retriever.search(
                query=search_query,
                top_k=5,
                threshold=0.25,  # Lower threshold for better recall
                db=self.db,
                category="parenting",
            )

            if rag_results:
                rag_context = "\n\n【參考理論】\n"
                for i, theory in enumerate(rag_results, 1):
                    theory_text = theory.get("text", "")[:200]
                    theory_doc = theory.get("document", "")
                    theory_title = theory.get("title", theory_doc)
                    theory_category = theory.get("category", "教養理論")

                    rag_context += f"{i}. {theory_text}... (來源: {theory_doc})\n"
                    rag_sources.append(theory_doc)

                    # Build reference for response
                    rag_references.append(
                        ParentsReportReference(
                            title=theory_title,
                            content=theory_text,
                            source=theory_doc,
                            theory=theory_category,
                        )
                    )
                logger.info(f"RAG found {len(rag_results)} theories for report")
            else:
                logger.warning(
                    "RAG search returned no results - "
                    "check if parenting documents exist in vector DB"
                )
        except Exception as e:
            # RAG failure should not block report generation
            logger.warning(f"RAG search failed (continuing without RAG): {e}")

        return rag_context, rag_sources, rag_references

    def _build_report_prompt(
        self,
        session: "Session",
        transcript: str,
        rag_context: str,
    ) -> str:
        """Build the analysis prompt for report generation"""
        # Build RAG instruction if we have context
        rag_instruction = ""
        if rag_context:
            rag_instruction = """
【重要】請參考上述理論來支持你的分析和建議。在 analyze 和 suggestion 中可以引用相關理論。
"""

        # Calculate transcript duration hint
        transcript_length = len(transcript)
        duration_hint = (
            "短對話"
            if transcript_length < 500
            else "中等對話"
            if transcript_length < 2000
            else "長對話"
        )

        # Build scenario context for report
        scenario_section = ""
        if session.scenario or session.scenario_description:
            scenario_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【家長煩惱情境】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{session.scenario or ''}
{session.scenario_description or ''}

⚠️ 請圍繞上述家長的煩惱情境進行分析，提供針對性的建議。
"""

        return f"""你是專業的親子溝通分析師，精通 8 大教養流派（阿德勒正向教養、薩提爾、ABA行為分析、Dan Siegel 全腦教養、Gottman 情緒輔導、Ross Greene 協作問題解決、Dr. Becky Kennedy、社會意識教養），負責分析家長與孩子的對話，提供建設性的回饋。
{scenario_section}{rag_context}{rag_instruction}
【對話逐字稿】（{duration_hint}，共 {transcript_length} 字）
{transcript}

【分析要求】
請以中性、客觀、溫和的立場**深入分析**這次對話。
⚠️ 重要：請根據對話長度提供**相應深度的分析**：
- 短對話（< 500 字）：提供基本分析
- 中等對話（500-2000 字）：提供詳細分析，包含多個觀察點
- 長對話（> 2000 字）：提供完整、深入的分析，涵蓋對話中的各個關鍵時刻

請提供以下 4 個部分：

1. **鼓勵標題**（encouragement）
   - ⚠️ **必須 15 字以內**（這是硬性限制！）
   - 一句具體的正向觀察，指出家長做得好的地方
   - 不要用「很棒」「很好」等空泛詞彙
   - 例如：「你沒急著反駁」、「有給孩子說的空間」、「這次有在同理」、「你正在接住孩子」

2. **待解決的議題**（issue）
   - 指出這次對話中最需要改進的地方
   - 客觀描述，不批判
   - 如果對話較長，可以列出多個議題

3. **溝通內容分析**（analyze）
   - **深入分析**為何這樣的溝通方式可能有問題
   - 解釋背後的心理學或教養理論原理
   - 引用相關教養流派的觀點（如：薩提爾冰山理論、阿德勒歸屬感、Gottman 情緒輔導等）
   - 分析對話中的情緒動態、權力關係、溝通模式
   - ⚠️ 對於長對話，請提供完整、詳盡的分析（300-500 字）

4. **建議下次可以這樣說**（suggestion）
   - 提供具體、可直接使用的替代說法
   - 用「」標示建議的話語
   - 提供多個情境下的建議話術
   - 解釋為什麼這樣說更有效
   - ⚠️ 對於長對話，提供多種情境的建議（200-400 字）

【語氣要求】
- 溫和、同理、建設性
- 避免批判或讓家長感到被指責
- ⚠️ 語言風格：用生活化、口語化的方式表達，像一個有經驗的朋友在分享育兒心得
- ⚠️ 專業術語使用原則：
  - 適度保留簡單易懂的專業詞彙（如「同理」「界限」「情緒」「歸屬感」「價值感」），展現專業可信度
  - 避免過度學術化的表述（如「冰山理論」「情緒教練時刻」「黃金情緒教育時刻」「權力鬥爭循環」）
  - 不要直接引用專家名字（如 Gottman、阿德勒、薩提爾、Dan Siegel、Ross Greene、Dr. Becky Kennedy 等）
  - 改用「研究發現...」「專家建議...」「心理學研究顯示...」等中性表述
- ⚠️ 理論概念轉譯：
  - 「情緒教練」→「陪伴孩子面對情緒」
  - 「黃金時刻」→「很難得的時刻」「好機會」
  - 「冰山理論」→「表面行為背後的真正需求」「孩子真正想說的」
  - 「權力鬥爭」→「親子之間的拉扯」「對立」
  - 「和善而堅定」→「溫柔但堅定」「理解但不縱容」
- 展現專業深度，但用家長聽得懂的話
- 可以說理論觀點，但要用故事化、情境化的方式解釋

【輸出格式】
請以 JSON 格式回應：

{{
  "encouragement": "15 字以內的鼓勵標題",
  "issue": "待解決的議題（可以是多點，用換行分隔）",
  "analyze": "溝通內容深入分析（根據對話長度，提供 150-500 字的分析）",
  "suggestion": "建議下次可以這樣說（提供多個情境的具體話術，150-400 字）"
}}

請開始深入分析。"""

    MAX_ENCOURAGEMENT_CHARS = 15  # 鼓勵標題最大字數

    def _parse_report_response(self, llm_raw_response: str) -> Dict:
        """Parse LLM response to extract report data"""
        try:
            if "```json" in llm_raw_response:
                json_start = llm_raw_response.find("```json") + 7
                json_end = llm_raw_response.find("```", json_start)
                json_text = llm_raw_response[json_start:json_end].strip()
            elif "{" in llm_raw_response:
                json_start = llm_raw_response.find("{")
                json_end = llm_raw_response.rfind("}") + 1
                json_text = llm_raw_response[json_start:json_end]
            else:
                raise ValueError("No JSON found in response")

            json_text = re.sub(r",(\s*[}\]])", r"\1", json_text)
            result = json.loads(json_text)

            # Validate encouragement field using centralized helper
            if "encouragement" in result:
                encouragement = result["encouragement"]
                validated = validate_ai_output_length(
                    text=encouragement,
                    min_chars=4,  # Minimum meaningful encouragement
                    max_chars=self.MAX_ENCOURAGEMENT_CHARS,  # 15 chars
                    field_name="encouragement",
                )
                if validated is None:
                    # Too short - use a default
                    result["encouragement"] = "你正在進步中"  # 6 chars
                    logger.warning(
                        f"Encouragement too short, using default: {result['encouragement']}"
                    )
                else:
                    result["encouragement"] = validated

            return result

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse report response: {e}")
            raise ValueError(f"Failed to parse AI response: {e}")

    def save_report_record(
        self,
        session_id,
        client_id,
        counselor_id,
        tenant_id: str,
        analysis: Dict,
        rag_references: List["ParentsReportReference"],
        token_usage: Dict,
    ) -> None:
        """Create or update Report record in database"""
        from sqlalchemy import select

        from app.models.report import Report, ReportStatus

        try:
            existing_report = self.db.execute(
                select(Report).where(
                    Report.session_id == session_id,
                    Report.deleted_at.is_(None),
                )
            ).scalar_one_or_none()

            # Build content for Report
            report_content_json = {
                "encouragement": analysis.get("encouragement", ""),
                "issue": analysis.get("issue", ""),
                "analyze": analysis.get("analyze", ""),
                "suggestion": analysis.get("suggestion", ""),
                "references": [ref.model_dump() for ref in rag_references],
            }

            # Build markdown content
            report_content_markdown = f"""# 親子對話報告

## 🌟 鼓勵
{analysis.get("encouragement", "")}

## 💡 待解決的議題
{analysis.get("issue", "")}

## 📊 溝通內容分析
{analysis.get("analyze", "")}

## 💬 建議下次可以這樣說
{analysis.get("suggestion", "")}
"""

            if existing_report:
                # Update existing report
                existing_report.content_json = report_content_json
                existing_report.content_markdown = report_content_markdown
                existing_report.status = ReportStatus.DRAFT
                existing_report.prompt_tokens = token_usage.get("prompt_tokens", 0)
                existing_report.completion_tokens = token_usage.get(
                    "completion_tokens", 0
                )
                logger.info(f"Updated existing Report for session {session_id}")
            else:
                # Create new report
                new_report = Report(
                    session_id=session_id,
                    client_id=client_id,
                    created_by_id=counselor_id,
                    tenant_id=tenant_id,
                    status=ReportStatus.DRAFT,
                    mode="island_parents",
                    content_json=report_content_json,
                    content_markdown=report_content_markdown,
                    prompt_tokens=token_usage.get("prompt_tokens", 0),
                    completion_tokens=token_usage.get("completion_tokens", 0),
                )
                self.db.add(new_report)
                logger.info(f"Created new Report for session {session_id}")

            self.db.commit()
        except Exception as e:
            # Report creation failure should not block response
            logger.error(f"Failed to create/update Report record: {e}", exc_info=True)
            self.db.rollback()
