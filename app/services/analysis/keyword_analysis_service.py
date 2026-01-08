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
import uuid
from datetime import datetime, timezone
from decimal import Decimal
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
from app.services.analysis.session_billing_service import SessionBillingService
from app.services.external.gemini_service import GeminiService
from app.services.external.openai_service import OpenAIService
from app.services.rag.rag_retriever import RAGRetriever

logger = logging.getLogger(__name__)


class KeywordAnalysisService:
    """Service for AI-powered keyword analysis of session transcripts"""

    # Sliding window configuration (aligned with realtime.py)
    SAFETY_WINDOW_SPEAKER_TURNS = 10  # Number of recent speaker turns to evaluate
    ANNOTATED_WINDOW_TURNS = 5  # Highlighted turns for AI focus

    # RAG category mapping for tenants
    TENANT_RAG_CATEGORIES = {
        "career": "career",
        "island": "parenting",  # island uses parenting RAG
        "island_parents": "parenting",
    }

    def __init__(self, db: DBSession):
        self.db = db
        self.gemini_service = GeminiService()
        self.openai_service = OpenAIService()
        self.rag_retriever = RAGRetriever(self.openai_service)
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

        Combines safety level detection and expert suggestion selection into
        a single Gemini call, reducing latency from ~40s to ~15s.

        Args:
            transcript_segment: Recent transcript text (last 60s - focus area)
            full_transcript: Complete transcript (background context)
            mode: "practice" or "emergency"
            tenant_id: Tenant identifier
            scenario_context: Parent's concern/scenario description

        Returns:
            Dict with:
            - safety_level: green/yellow/red
            - display_text: Short status description
            - quick_suggestion: Selected expert suggestion
        """
        import random

        from app.config.parenting_suggestions import (
            GREEN_SUGGESTIONS,
            RED_SUGGESTIONS,
            YELLOW_SUGGESTIONS,
        )

        start_time = time.time()

        try:
            # Get simplified prompt template
            prompt_template = PromptRegistry.get_prompt(
                tenant_id, "deep_simplified", mode=mode
            )

            # Build prompt with embedded suggestions (sample 10 from each for shorter prompt)
            green_sample = random.sample(
                GREEN_SUGGESTIONS, min(10, len(GREEN_SUGGESTIONS))
            )
            yellow_sample = random.sample(
                YELLOW_SUGGESTIONS, min(10, len(YELLOW_SUGGESTIONS))
            )
            red_sample = random.sample(RED_SUGGESTIONS, min(10, len(RED_SUGGESTIONS)))

            # Use full_transcript as fallback if not provided
            if full_transcript is None:
                full_transcript = transcript_segment

            prompt = prompt_template.format(
                transcript_segment=transcript_segment[:500],
                full_transcript=full_transcript,
                green_suggestions="\n".join(f"- {s}" for s in green_sample),
                yellow_suggestions="\n".join(f"- {s}" for s in yellow_sample),
                red_suggestions="\n".join(f"- {s}" for s in red_sample),
            )

            # Prepend scenario context if provided
            if scenario_context:
                prompt = f"{scenario_context}\n\n{prompt}"

            # Single Gemini call
            ai_response = await self.gemini_service.generate_text(
                prompt,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            # Extract text and usage metadata from Gemini response
            text = (
                ai_response.text if hasattr(ai_response, "text") else str(ai_response)
            )
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(ai_response, "usage_metadata"):
                usage = ai_response.usage_metadata
                prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
                completion_tokens = getattr(usage, "candidates_token_count", 0) or 0

            # Parse response
            result = parse_ai_response(text)

            # Ensure required fields
            result.setdefault("safety_level", "green")
            result.setdefault("display_text", "分析完成")
            result.setdefault("quick_suggestion", "")

            # Validate display_text (should be within 20 chars per prompt)
            display_text = result.get("display_text", "")
            max_display_chars = 20
            min_display_chars = 4  # fallback "分析完成" is 4 chars

            if len(display_text) < min_display_chars:
                logger.warning(
                    f"display_text too short ({len(display_text)} chars): '{display_text}', "
                    f"using fallback"
                )
                result["display_text"] = "分析完成"
            elif len(display_text) > max_display_chars:
                logger.warning(
                    f"display_text over {max_display_chars} chars: "
                    f"{len(display_text)} chars - '{display_text[:30]}...'"
                )

            # Validate quick_suggestion (from 200 expert suggestions: 5-17 chars)
            quick_suggestion = result.get("quick_suggestion", "")
            max_suggestion_chars = 20  # longest expert suggestion is 17 chars
            min_suggestion_chars = 5  # shortest expert suggestion is 5 chars

            if quick_suggestion:
                if len(quick_suggestion) < min_suggestion_chars:
                    logger.warning(
                        f"quick_suggestion too short ({len(quick_suggestion)} chars): "
                        f"'{quick_suggestion}', clearing it"
                    )
                    quick_suggestion = ""
                elif len(quick_suggestion) > max_suggestion_chars:
                    logger.warning(
                        f"quick_suggestion over {max_suggestion_chars} chars: "
                        f"{len(quick_suggestion)} chars - '{quick_suggestion[:30]}...'"
                    )
                    # Don't truncate mid-sentence, just log warning

            # Wrap quick_suggestion in list for compatibility
            result["quick_suggestions"] = [quick_suggestion] if quick_suggestion else []

            # Add metadata with REAL token usage
            duration_ms = int((time.time() - start_time) * 1000)
            result["_metadata"] = {
                "mode": mode,
                "duration_ms": duration_ms,
                "prompt_type": "deep_simplified",
                "rag_used": False,
            }
            result["prompt_tokens"] = prompt_tokens
            result["completion_tokens"] = completion_tokens
            result["total_tokens"] = prompt_tokens + completion_tokens

            logger.info(
                f"Simplified analysis completed in {duration_ms}ms: "
                f"safety_level={result['safety_level']}"
            )

            return result

        except Exception as e:
            logger.error(f"Simplified analysis failed: {e}")
            return {
                "safety_level": "green",
                "display_text": "分析中...",
                "quick_suggestions": [],
                "_metadata": {"error": str(e)},
            }

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
                rag_documents, rag_sources, rag_context = await self._retrieve_rag(
                    transcript_segment, resolved_tenant, db_session
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
            result_data["_metadata"] = self._build_metadata(
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
            rag_documents, rag_sources, rag_context = await self._retrieve_rag(
                transcript_segment, resolved_tenant, self.db, top_k=3, threshold=0.7
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
            result_data["_metadata"] = self._build_metadata(
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

    async def _retrieve_rag(
        self,
        transcript_segment: str,
        resolved_tenant: str,
        db_session: DBSession,
        top_k: int = 7,
        threshold: float = 0.35,
    ) -> tuple:
        """Retrieve RAG documents for analysis"""
        rag_documents = []
        rag_sources = []
        rag_context = ""

        try:
            rag_category = self.TENANT_RAG_CATEGORIES.get(resolved_tenant)
            if rag_category:
                rag_results = await self.rag_retriever.search(
                    query=transcript_segment[:200],
                    top_k=top_k,
                    threshold=threshold,
                    db=db_session,
                    category=rag_category,
                )
                rag_documents = [
                    {
                        "doc_id": None,
                        "title": r["document"],
                        "content": r["text"],
                        "relevance_score": r["score"],
                        "chunk_id": None,
                    }
                    for r in rag_results
                ]
                rag_sources = [r["document"] for r in rag_results]

                if rag_documents:
                    rag_context = "\n\n## 參考知識庫\n" + "\n\n".join(
                        [
                            f"【{doc['title']}】\n{doc['content']}"
                            for doc in rag_documents[:top_k]
                        ]
                    )
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

        return rag_documents, rag_sources, rag_context

    def _build_metadata(
        self,
        ai_response,
        analysis_type: str,
        mode_enum: CounselingMode,
        resolved_tenant: str,
        prompt: str,
        transcript_segment: str,
        rag_documents: List[dict],
        rag_sources: List[str],
        analysis_start_time: datetime,
        start_time: float,
        quick_suggestions: List[str],
        result_data: Dict,
    ) -> Dict:
        """Build metadata dict for analysis result"""
        # Get token usage from Gemini
        token_usage = getattr(ai_response, "usage_metadata", None)
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        estimated_cost = Decimal("0.0")

        if token_usage:
            prompt_tokens = getattr(token_usage, "prompt_token_count", 0)
            completion_tokens = getattr(token_usage, "candidates_token_count", 0)
            total_tokens = getattr(token_usage, "total_token_count", 0)

            # Estimate cost (Gemini 3 Flash pricing)
            input_cost = Decimal(prompt_tokens) * Decimal("0.00000050")
            output_cost = Decimal(completion_tokens) * Decimal("0.000003")
            estimated_cost = input_cost + output_cost

        end_time = datetime.now(timezone.utc)
        duration_ms = int((time.time() - start_time) * 1000)

        llm_raw_response = (
            ai_response.text if hasattr(ai_response, "text") else str(ai_response)
        )

        return {
            "request_id": str(uuid.uuid4()),
            "mode": mode_enum.value,
            "time_range": None,
            "speakers": None,
            "system_prompt": None,
            "user_prompt": prompt,
            "prompt_template": f"{analysis_type}_{mode_enum.value}_v1"
            if resolved_tenant == "island_parents"
            else f"{analysis_type}_v1",
            "rag_used": len(rag_documents) > 0,
            "rag_query": transcript_segment[:200],
            "rag_documents": rag_documents,
            "rag_sources": rag_sources,
            "rag_top_k": 7,
            "rag_similarity_threshold": 0.35,
            "rag_search_time_ms": None,
            "provider": "gemini",
            "model_name": "gemini-3-flash-preview",
            "model_version": "3.0",
            "start_time": analysis_start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_ms": duration_ms,
            "api_response_time_ms": duration_ms,
            "llm_call_time_ms": None,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cached_tokens": 0,
            "estimated_cost_usd": float(estimated_cost),
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
            },
            "llm_raw_response": llm_raw_response,
            "analysis_reasoning": result_data.get("counselor_insights"),
            "matched_suggestions": quick_suggestions,
            "use_cache": False,
            "cache_hit": None,
            "cache_key": None,
            "gemini_cache_ttl": None,
            "transcript_length": len(transcript_segment),
            "duration_seconds": None,
        }

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
