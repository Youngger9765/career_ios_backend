"""
Keyword Analysis Service - AI-powered transcript keyword extraction
Extracted from app/api/sessions.py analyze_session_keywords endpoint (320 lines)

Multi-tenant support:
- career: 職涯諮詢分析
- island_parents: 親子教養分析

Refactored: Delegates to specialized services for better modularity.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from app.models.case import Case
from app.models.client import Client
from app.models.session import Session
from app.prompts import PromptRegistry
from app.schemas.session import CounselingMode

# Import from refactored modules
from app.services.analysis.analysis_helpers import (
    build_context,
    build_prompt,
    fallback_rule_based_analysis,
    get_default_result,
    get_tenant_fallback_result,
    parse_ai_response,
    save_analysis_log_to_session,
)
from app.services.analysis.expert_suggestion_service import select_expert_suggestions
from app.services.analysis.keyword_analysis.metadata import MetadataBuilder
from app.services.analysis.keyword_analysis.prompts import RAGPromptBuilder
from app.services.analysis.keyword_analysis.simplified_analyzer import (
    SimplifiedAnalyzer,
)
from app.services.analysis.session_billing_service import SessionBillingService
from app.services.external.gemini_service import GeminiService
from app.services.external.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class KeywordAnalysisService:
    """Service for AI-powered keyword analysis of session transcripts"""

    # Sliding window configuration (aligned with realtime.py)
    SAFETY_WINDOW_SPEAKER_TURNS = 10  # Number of recent speaker turns to evaluate
    ANNOTATED_WINDOW_TURNS = 5  # Highlighted turns for AI focus

    def __init__(self, db: DBSession):
        self.db = db
        self.gemini_service = GeminiService()
        self.openai_service = OpenAIService()
        self.rag_prompt_builder = RAGPromptBuilder(self.openai_service)
        self.simplified_analyzer = SimplifiedAnalyzer(self.gemini_service)
        self.billing_service = SessionBillingService(db)

    async def analyze_keywords_simplified(
        self,
        transcript_segment: str,
        full_transcript: Optional[str] = None,
        mode: str = "practice",
        tenant_id: str = "island_parents",
        scenario_context: Optional[str] = None,
    ) -> Dict:
        """
        Simplified keyword analysis - 1 Gemini call (optimized).

        Delegates to SimplifiedAnalyzer for implementation.
        """
        return await self.simplified_analyzer.analyze_simplified(
            transcript_segment=transcript_segment,
            full_transcript=full_transcript,
            mode=mode,
            tenant_id=tenant_id,
            scenario_context=scenario_context,
        )

    async def analyze_keywords(
        self,
        session_id: str = None,
        transcript_segment: str = "",
        full_transcript: str = "",
        context: str = "",
        analysis_type: str = "island_parents",
        mode: str = "practice",
        db: DBSession = None,
        use_rag: bool = False,
    ) -> Dict:
        """
        Unified keyword analysis for realtime and session-based analysis.

        This method is the SINGLE SOURCE OF TRUTH for keyword analysis,
        replacing hardcoded prompts in realtime.py.

        Args:
            session_id: Session ID (None for realtime usage)
            transcript_segment: Recent transcript text (e.g., last 60 seconds)
            full_transcript: Full conversation history (for context)
            context: Additional context string
            analysis_type: Tenant type (career, island_parents)
            mode: Analysis mode (emergency, practice) - only for island_parents
            db: Database session (optional, for RAG retrieval)
            use_rag: Whether to use RAG knowledge retrieval (default: False)

        Returns:
            Dict with analysis results:
            - safety_level: green/yellow/red
            - severity: 1-3
            - quick_suggestions: List[str] (from 200 expert sentences)
            - detailed_scripts: List[dict] (8 schools, only in practice mode)
            - theoretical_frameworks: List[dict] (8 schools, only in practice mode)
            - display_text: str
            - action_suggestion: str
            - rag_documents: List[dict]
            - _metadata: Dict (for persistence)
        """
        analysis_start_time = datetime.now(timezone.utc)
        start_time = time.time()

        # Resolve tenant alias using PromptRegistry
        resolved_tenant = PromptRegistry.TENANT_ALIAS.get(analysis_type, analysis_type)

        try:
            # Use provided db or fallback to instance db
            db_session = db or self.db

            # STEP 1: Retrieve RAG documents (only if use_rag=True)
            rag_documents = []
            rag_sources = []
            rag_context = ""
            if use_rag:
                rag_documents, rag_sources, rag_context = (
                    await self.rag_prompt_builder.retrieve_rag_context(
                        transcript_segment, resolved_tenant, db_session
                    )
                )

            # STEP 2: Get tenant-specific prompt using PromptRegistry
            mode_enum = CounselingMode(mode) if mode else CounselingMode.practice
            prompt_template = PromptRegistry.get_prompt(
                resolved_tenant,
                "deep",
                mode=mode_enum.value,
            )

            # STEP 3: Build prompt WITH RAG context
            prompt = prompt_template.format(
                context=context + rag_context,
                full_transcript=full_transcript or transcript_segment,
                transcript_segment=transcript_segment[:500],
            )

            # STEP 4: Call Gemini AI with complete prompt (including RAG)
            ai_response = await self.gemini_service.generate_text(
                prompt, temperature=0.3, response_format={"type": "json_object"}
            )

            # STEP 5: Parse AI response
            result_data = parse_ai_response(ai_response)

            # STEP 5.5: Generate expert suggestions (ONLY for island_parents)
            if resolved_tenant == "island_parents":
                safety_level = result_data.get("safety_level", "green")
                quick_suggestions = await select_expert_suggestions(
                    transcript=transcript_segment,
                    safety_level=safety_level,
                    num_suggestions=1,
                    gemini_service=self.gemini_service,
                )
                result_data["quick_suggestions"] = quick_suggestions

                # If emergency mode, remove detailed scripts
                if mode_enum == CounselingMode.emergency:
                    result_data["detailed_scripts"] = []
                    result_data["theoretical_frameworks"] = []

            # Build metadata
            result_data["rag_documents"] = rag_documents
            result_data["_metadata"] = MetadataBuilder.build_metadata(
                ai_response=ai_response,
                analysis_type=analysis_type,
                mode_enum=mode_enum,
                resolved_tenant=resolved_tenant,
                prompt=prompt,
                transcript_segment=transcript_segment,
                rag_documents=rag_documents,
                rag_sources=rag_sources,
                analysis_start_time=analysis_start_time,
                start_time=start_time,
                quick_suggestions=result_data.get("quick_suggestions", []),
                result_data=result_data,
            )

            return result_data

        except Exception as e:
            logger.error(f"Keyword analysis failed for tenant {analysis_type}: {e}")
            return get_tenant_fallback_result(analysis_type)

    async def analyze_partial(
        self,
        session: Session,
        client: Client,
        case: Case,
        transcript_segment: str,
        counselor_id: UUID,
        tenant_id: str,
        mode: CounselingMode = CounselingMode.practice,
    ) -> Dict:
        """
        Multi-tenant partial analysis with RAG support.

        Returns analysis results WITHOUT saving to DB (for immediate response).
        Use save_analysis_log_and_usage() in background task to persist.
        """
        analysis_start_time = datetime.now(timezone.utc)
        start_time = time.time()

        # Resolve tenant alias using PromptRegistry
        resolved_tenant = PromptRegistry.TENANT_ALIAS.get(tenant_id, tenant_id)

        try:
            # Build context
            context_str = build_context(session, client, case)
            full_transcript = session.transcript_text or "（尚無完整逐字稿）"

            # STEP 1: Retrieve RAG documents
            rag_documents, rag_sources, rag_context = (
                await self.rag_prompt_builder.retrieve_rag_context(
                    transcript_segment, resolved_tenant, self.db, top_k=3, threshold=0.7
                )
            )

            # STEP 2: Get tenant-specific prompt
            prompt_template = PromptRegistry.get_prompt(
                resolved_tenant,
                "deep",
                mode=mode.value,
            )

            # STEP 3: Build prompt WITH RAG context
            prompt = prompt_template.format(
                context=context_str + rag_context,
                full_transcript=full_transcript,
                transcript_segment=transcript_segment[:500],
            )

            # STEP 4: Call Gemini AI
            ai_response = await self.gemini_service.generate_text(
                prompt, temperature=0.3, response_format={"type": "json_object"}
            )

            # STEP 5: Parse AI response
            result_data = parse_ai_response(ai_response)

            # STEP 5.5: Generate expert suggestions (ONLY for island_parents)
            if resolved_tenant == "island_parents":
                safety_level = result_data.get("safety_level", "green")
                quick_suggestions = await select_expert_suggestions(
                    transcript=transcript_segment,
                    safety_level=safety_level,
                    num_suggestions=1,
                    gemini_service=self.gemini_service,
                )
                result_data["quick_suggestions"] = quick_suggestions

                if mode == CounselingMode.emergency:
                    result_data["detailed_scripts"] = []
                    result_data["theoretical_frameworks"] = []

            # Build metadata
            result_data["rag_documents"] = rag_documents
            result_data["_metadata"] = MetadataBuilder.build_metadata(
                ai_response=ai_response,
                analysis_type=tenant_id,
                mode_enum=mode,
                resolved_tenant=resolved_tenant,
                prompt=prompt,
                transcript_segment=transcript_segment,
                rag_documents=rag_documents,
                rag_sources=rag_sources,
                analysis_start_time=analysis_start_time,
                start_time=start_time,
                quick_suggestions=result_data.get("quick_suggestions", []),
                result_data=result_data,
            )

            return result_data

        except Exception as e:
            logger.error(f"Partial analysis failed for tenant {tenant_id}: {e}")
            return get_tenant_fallback_result(tenant_id)

    def save_analysis_log_and_usage(
        self,
        session_id: UUID,
        counselor_id: UUID,
        tenant_id: str,
        transcript_segment: str,
        result_data: Dict,
        rag_documents: List[dict],
        rag_sources: List[str],
        token_usage_data: Dict,
    ) -> None:
        """Delegate to billing service"""
        self.billing_service.save_analysis_log_and_usage(
            session_id=session_id,
            counselor_id=counselor_id,
            tenant_id=tenant_id,
            transcript_segment=transcript_segment,
            result_data=result_data,
            rag_documents=rag_documents,
            rag_sources=rag_sources,
            token_usage_data=token_usage_data,
        )

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
            context_str = build_context(session, client, case)
            prompt = build_prompt(context_str, transcript_segment)

            ai_response = await self.gemini_service.generate_text(
                prompt, temperature=0.3, response_format={"type": "json_object"}
            )

            result_data = parse_ai_response(ai_response)

            save_analysis_log_to_session(
                self.db, session, transcript_segment, result_data, counselor_id
            )

            return result_data

        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            return fallback_rule_based_analysis(
                self.db, session, transcript_segment, counselor_id
            )

    # Backward compatibility aliases
    def _build_context(self, session: Session, client: Client, case: Case) -> str:
        return build_context(session, client, case)

    def _build_prompt(self, context: str, transcript_segment: str) -> str:
        return build_prompt(context, transcript_segment)

    def _parse_ai_response(self, ai_response) -> Dict:
        return parse_ai_response(ai_response)

    def _get_default_result(self) -> Dict:
        return get_default_result()

    def _get_tenant_fallback_result(self, tenant_id: str) -> Dict:
        return get_tenant_fallback_result(tenant_id)

    def _save_analysis_log(
        self,
        session: Session,
        transcript_segment: str,
        result_data: Dict,
        counselor_id: UUID,
        is_fallback: bool = False,
    ) -> None:
        save_analysis_log_to_session(
            self.db, session, transcript_segment, result_data, counselor_id, is_fallback
        )

    def _fallback_rule_based_analysis(
        self, session: Session, transcript: str, counselor_id: UUID
    ) -> Dict:
        return fallback_rule_based_analysis(self.db, session, transcript, counselor_id)
