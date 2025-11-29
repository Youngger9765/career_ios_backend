"""
Keyword Analysis Service - AI-powered transcript keyword extraction
Extracted from app/api/sessions.py analyze_session_keywords endpoint (320 lines)
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from app.models.case import Case
from app.models.client import Client
from app.models.session import Session
from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class KeywordAnalysisService:
    """Service for AI-powered keyword analysis of session transcripts"""

    def __init__(self, db: DBSession):
        self.db = db
        self.gemini_service = GeminiService()

    async def analyze_transcript_keywords(
        self,
        session: Session,
        client: Client,
        case: Case,
        transcript_segment: str,
        counselor_id: UUID,
    ) -> Dict:
        """
        Analyze transcript segment for keywords using AI with session context.

        Returns: dict with keys: keywords, categories, confidence, counselor_insights
        """
        try:
            # Build AI prompt context
            context_str = self._build_context(session, client, case)

            # Build optimized prompt for fast response
            prompt = self._build_prompt(context_str, transcript_segment)

            # Call Gemini AI
            ai_response = await self.gemini_service.generate_text(
                prompt, temperature=0.3, response_format={"type": "json_object"}
            )

            # Parse AI response
            result_data = self._parse_ai_response(ai_response)

            # Save analysis log to session
            self._save_analysis_log(
                session, transcript_segment, result_data, counselor_id
            )

            return result_data

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            # Fallback to rule-based analysis
            return self._fallback_rule_based_analysis(
                session, transcript_segment, counselor_id
            )

    def _build_context(self, session: Session, client: Client, case: Case) -> str:
        """Build context string from session, case, and client information"""
        context_parts = []

        # Add client information
        client_info = f"案主資訊: {client.name}"
        if client.current_status:
            client_info += f", 當前狀況: {client.current_status}"
        if client.notes:
            client_info += f", 備註: {client.notes}"
        context_parts.append(client_info)

        # Add case information
        case_info = f"案例目標: {case.goals or '未設定'}"
        if case.problem_description:
            case_info += f", 問題敘述: {case.problem_description}"
        context_parts.append(case_info)

        # Add session information
        session_info = f"會談次數: 第 {session.session_number} 次"
        if session.notes:
            session_info += f", 會談備註: {session.notes}"
        context_parts.append(session_info)

        return "\n".join(context_parts)

    def _build_prompt(self, context: str, transcript_segment: str) -> str:
        """Build AI prompt for keyword extraction"""
        return f"""快速分析以下逐字稿，提取關鍵詞和洞見。

背景：
{context}

逐字稿：
{transcript_segment[:500]}

JSON回應（精簡）：
{{
    "keywords": ["詞1", "詞2", "詞3", "詞4", "詞5"],
    "categories": ["類別1", "類別2", "類別3"],
    "confidence": 0.85,
    "counselor_insights": "簡短洞見（50字內）"
}}"""

    def _parse_ai_response(self, ai_response) -> Dict:
        """Parse AI response to extract keywords data"""
        if isinstance(ai_response, str):
            try:
                json_start = ai_response.find("{")
                json_end = ai_response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = ai_response[json_start:json_end]
                    return json.loads(json_str)
                else:
                    # Quick fallback
                    return self._get_default_result()
            except json.JSONDecodeError:
                return self._get_default_result()
        else:
            return ai_response

    def _get_default_result(self) -> Dict:
        """Get default keyword analysis result"""
        return {
            "keywords": ["探索中", "情緒", "發展"],
            "categories": ["一般諮商"],
            "confidence": 0.5,
            "counselor_insights": "持續觀察案主狀態。",
        }

    def _save_analysis_log(
        self,
        session: Session,
        transcript_segment: str,
        result_data: Dict,
        counselor_id: UUID,
        is_fallback: bool = False,
    ) -> None:
        """Save analysis log to session"""
        from sqlalchemy.orm.attributes import flag_modified

        analysis_log_entry = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "transcript_segment": transcript_segment[:200],
            "keywords": result_data.get("keywords", [])[:10],
            "categories": result_data.get("categories", [])[:5],
            "confidence": result_data.get("confidence", 0.5),
            "counselor_insights": result_data.get("counselor_insights", "")[:200],
            "counselor_id": str(counselor_id),
        }

        if is_fallback:
            analysis_log_entry["fallback"] = True

        if session.analysis_logs is None:
            session.analysis_logs = []

        session.analysis_logs.append(analysis_log_entry)
        flag_modified(session, "analysis_logs")

        self.db.commit()
        self.db.refresh(session)

    def _fallback_rule_based_analysis(
        self, session: Session, transcript: str, counselor_id: UUID
    ) -> Dict:
        """Fallback rule-based keyword extraction when AI fails"""
        # Common counseling keywords
        emotion_keywords = [
            "焦慮",
            "壓力",
            "緊張",
            "難過",
            "開心",
            "害怕",
            "生氣",
            "沮喪",
            "無助",
            "迷惘",
            "困擾",
            "擔心",
            "自卑",
        ]
        work_keywords = [
            "工作",
            "主管",
            "同事",
            "公司",
            "職涯",
            "轉職",
            "離職",
            "上班",
            "加班",
            "業績",
            "升遷",
        ]
        relationship_keywords = [
            "家人",
            "父母",
            "伴侶",
            "朋友",
            "關係",
            "溝通",
            "衝突",
            "相處",
            "家庭",
        ]
        development_keywords = [
            "目標",
            "方向",
            "成就",
            "發展",
            "規劃",
            "未來",
            "改變",
            "學習",
            "成長",
        ]

        # Extract keywords found in transcript
        found_keywords = []
        categories = set()

        for word in emotion_keywords:
            if word in transcript:
                found_keywords.append(word)
                categories.add("情緒管理")

        for word in work_keywords:
            if word in transcript:
                found_keywords.append(word)
                categories.add("職涯發展")

        for word in relationship_keywords:
            if word in transcript:
                found_keywords.append(word)
                categories.add("人際關係")

        for word in development_keywords:
            if word in transcript:
                found_keywords.append(word)
                categories.add("自我探索")

        # Default if no keywords found
        if not found_keywords:
            found_keywords = ["探索中", "諮商進行"]
            categories = {"一般諮商"}

        # Generate insights based on keywords
        insights = self._generate_simple_insights(found_keywords, relationship_keywords)

        result = {
            "keywords": found_keywords[:10],
            "categories": list(categories)[:5],
            "confidence": 0.6,
            "counselor_insights": insights,
        }

        # Save fallback analysis log
        self._save_analysis_log(
            session, transcript, result, counselor_id, is_fallback=True
        )

        return result

    def _generate_simple_insights(
        self, found_keywords: List[str], relationship_keywords: List[str]
    ) -> str:
        """Generate simple insights from found keywords"""
        if "焦慮" in found_keywords or "壓力" in found_keywords:
            return "案主表達情緒困擾，建議關注壓力來源及因應策略。"
        elif "工作" in found_keywords or "職涯" in found_keywords:
            return "案主提及職涯議題，可探索工作價值觀與發展方向。"
        elif any(k in found_keywords for k in relationship_keywords):
            return "案主談及人際關係，建議探索互動模式與溝通方式。"
        else:
            keywords_str = ", ".join(found_keywords[:3])
            return f"案主提及 {keywords_str}，持續關注案主需求。"
