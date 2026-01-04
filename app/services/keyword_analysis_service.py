"""
Keyword Analysis Service - AI-powered transcript keyword extraction
Extracted from app/api/sessions.py analyze_session_keywords endpoint (320 lines)

Multi-tenant support:
- career: 職涯諮詢分析
- island_parents: 親子教養分析
"""
import json
import logging
import math  # For ceiling rounding
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor  # For counselor credit updates
from app.models.credit_log import CreditLog  # For dual-write pattern
from app.models.session import Session
from app.models.session_analysis_log import SessionAnalysisLog
from app.models.session_usage import SessionUsage
from app.prompts import PromptRegistry
from app.schemas.session import CounselingMode
from app.services.gemini_service import GeminiService
from app.services.openai_service import OpenAIService
from app.services.rag_retriever import RAGRetriever

logger = logging.getLogger(__name__)


async def _select_expert_suggestions(
    transcript: str,
    safety_level: str,
    num_suggestions: int = 2,
    gemini_service: GeminiService = None,
) -> List[str]:
    """
    從 200 句專家建議中使用 AI 挑選最適合的建議

    Args:
        transcript: 對話逐字稿
        safety_level: 安全等級 (green/yellow/red)
        num_suggestions: 要挑選的建議數量（固定為 1 條）
        gemini_service: Gemini API service

    Returns:
        List of selected suggestions (1 sentence, max 200 chars)
    """
    # Import suggestions from config
    from app.config.parenting_suggestions import (
        GREEN_SUGGESTIONS,
        RED_SUGGESTIONS,
        YELLOW_SUGGESTIONS,
    )

    # Select suggestion pool based on safety level
    if safety_level == "green":
        pool = GREEN_SUGGESTIONS
    elif safety_level == "yellow":
        pool = YELLOW_SUGGESTIONS
    else:  # red
        pool = RED_SUGGESTIONS

    # Build prompt for AI to select suggestions
    suggestions_list = "\n".join([f"  - {s}" for s in pool])

    prompt = f"""從以下專家建議中選擇 {num_suggestions} 句最符合當前對話的建議：

【當前對話】
{transcript}

【專家建議句庫】
{suggestions_list}

請選擇 {num_suggestions} 句最適合的建議。
規則：
1. 必須從上述建議中逐字選擇，不要改寫
2. 選擇最符合當前情境的建議
3. **每句建議必須在 200 字以內**（優先選擇簡短的建議）
4. 輸出 JSON 格式：{{"suggestions": ["句子1", "句子2"]}}

CRITICAL: 所有回應必須使用繁體中文（zh-TW），不可使用簡體中文。
"""

    try:
        # Call Gemini to select suggestions
        response = await gemini_service.generate_text(
            prompt, temperature=0.3, response_format={"type": "json_object"}
        )

        # Parse JSON response
        import json

        # Extract text from response object if needed
        if hasattr(response, "text"):
            response_text = response.text
        else:
            response_text = str(response)

        # Parse JSON
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
            suggestions = result.get("suggestions", [])

            # CRITICAL: Enforce 200-character limit to prevent UI overflow
            max_chars = 200
            truncated_suggestions = []
            for sug in suggestions:
                if len(sug) > max_chars:
                    # Truncate and add ellipsis
                    truncated = sug[: max_chars - 3] + "..."
                    logger.warning(
                        f"Suggestion truncated from {len(sug)} to {max_chars} chars: "
                        f"'{sug[:50]}...'"
                    )
                    truncated_suggestions.append(truncated)
                else:
                    truncated_suggestions.append(sug)

            return truncated_suggestions
        else:
            # Fallback: return random suggestions
            import random

            return random.sample(pool, min(num_suggestions, len(pool)))

    except Exception as e:
        logger.warning(f"Failed to select expert suggestions: {e}")
        # Fallback: return first N suggestions from pool
        return pool[:num_suggestions]


class KeywordAnalysisService:
    """Service for AI-powered keyword analysis of session transcripts"""

    # Sliding window configuration (aligned with realtime.py)
    SAFETY_WINDOW_SPEAKER_TURNS = 10  # Number of recent speaker turns to evaluate
    ANNOTATED_WINDOW_TURNS = 5  # Highlighted turns for AI focus

    def __init__(self, db: DBSession):
        self.db = db
        self.gemini_service = GeminiService()
        self.openai_service = OpenAIService()
        self.rag_retriever = RAGRetriever(self.openai_service)

    # Use PromptRegistry for tenant alias (now centralized)
    # PromptRegistry.TENANT_ALIAS handles: island -> island_parents, etc.

    # RAG category mapping for tenants
    TENANT_RAG_CATEGORIES = {
        "career": "career",
        "island": "parenting",  # island uses parenting RAG
        "island_parents": "parenting",
    }

    async def analyze_keywords_simplified(
        self,
        transcript_segment: str,
        full_transcript: Optional[str] = None,
        mode: str = "practice",
        tenant_id: str = "island_parents",
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

        Returns:
            Dict with:
            - safety_level: green/yellow/red
            - display_text: Short status description
            - quick_suggestion: Selected expert suggestion
        """
        import time

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
            import random

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

            # Single Gemini call
            ai_response = await self.gemini_service.generate_text(
                prompt, temperature=0.3, response_format={"type": "json_object"}
            )

            # Parse response
            result = self._parse_ai_response(ai_response)

            # Ensure required fields
            result.setdefault("safety_level", "green")
            result.setdefault("display_text", "分析完成")
            result.setdefault("quick_suggestion", "")

            # Wrap quick_suggestion in list for compatibility
            result["quick_suggestions"] = (
                [result["quick_suggestion"]] if result.get("quick_suggestion") else []
            )

            # Add metadata
            duration_ms = int((time.time() - start_time) * 1000)
            result["_metadata"] = {
                "mode": mode,
                "duration_ms": duration_ms,
                "prompt_type": "deep_simplified",
                "rag_used": False,
            }

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
        import time
        import uuid

        start_time = time.time()
        analysis_start_time = datetime.now(timezone.utc)

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
                try:
                    rag_category = self.TENANT_RAG_CATEGORIES.get(resolved_tenant)
                    if rag_category:
                        rag_results = await self.rag_retriever.search(
                            query=transcript_segment[:200],
                            top_k=7,  # Increased from 3 for richer context
                            threshold=0.35,  # Lowered from 0.7 for better retrieval
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

                        # Build RAG context string to include in prompt
                        if rag_documents:
                            rag_context = "\n\n## 參考知識庫\n" + "\n\n".join(
                                [
                                    f"【{doc['title']}】\n{doc['content']}"
                                    for doc in rag_documents[:7]
                                ]
                            )
                except Exception as e:
                    logger.warning(
                        f"RAG retrieval failed for tenant {analysis_type}: {e}"
                    )
                    # Continue without RAG documents

            # STEP 2: Get tenant-specific prompt using PromptRegistry
            mode_enum = CounselingMode(mode) if mode else CounselingMode.practice

            # PromptRegistry handles mode and fallback automatically
            prompt_template = PromptRegistry.get_prompt(
                resolved_tenant,
                "deep",  # Deep analysis prompt type
                mode=mode_enum.value,
            )

            # STEP 3: Build prompt WITH RAG context
            prompt = prompt_template.format(
                context=context + rag_context,  # Include RAG context here!
                full_transcript=full_transcript or transcript_segment,
                transcript_segment=transcript_segment[:500],
            )

            # STEP 4: Call Gemini AI with complete prompt (including RAG)
            ai_response = await self.gemini_service.generate_text(
                prompt, temperature=0.3, response_format={"type": "json_object"}
            )

            # STEP 5: Parse AI response
            result_data = self._parse_ai_response(ai_response)

            # STEP 5.5: Generate 200-sentence expert suggestions (ONLY for island_parents)
            if resolved_tenant == "island_parents":
                safety_level = result_data.get("safety_level", "green")
                num_suggestions = 1  # Always 1 suggestion (both emergency and practice)

                quick_suggestions = await _select_expert_suggestions(
                    transcript=transcript_segment,
                    safety_level=safety_level,
                    num_suggestions=num_suggestions,
                    gemini_service=self.gemini_service,
                )

                # Add quick_suggestions to result
                result_data["quick_suggestions"] = quick_suggestions

                # If emergency mode, remove detailed scripts (not needed)
                if mode_enum == CounselingMode.emergency:
                    result_data["detailed_scripts"] = []
                    result_data["theoretical_frameworks"] = []

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

                # Estimate cost (Gemini 3 Flash pricing: $0.50/1M input, $3/1M output)
                input_cost = Decimal(prompt_tokens) * Decimal("0.00000050")
                output_cost = Decimal(completion_tokens) * Decimal("0.000003")
                estimated_cost = input_cost + output_cost

            # Calculate timing
            end_time = datetime.now(timezone.utc)
            duration_ms = int((time.time() - start_time) * 1000)

            # Extract LLM raw response
            llm_raw_response = (
                ai_response.text if hasattr(ai_response, "text") else str(ai_response)
            )

            # Add RAG documents and complete metadata to result
            result_data["rag_documents"] = rag_documents
            result_data["_metadata"] = {
                # Request metadata
                "request_id": str(uuid.uuid4()),
                "mode": mode_enum.value,  # counseling mode: emergency or practice
                # Input data
                "time_range": None,  # Not applicable for realtime
                "speakers": None,  # Not applicable for realtime
                # Prompts
                "system_prompt": None,  # Could extract from template if needed
                "user_prompt": prompt,  # The actual prompt sent to Gemini
                "prompt_template": f"{analysis_type}_{mode_enum.value}_v1"
                if resolved_tenant == "island_parents"
                else f"{analysis_type}_v1",
                # RAG information
                "rag_used": len(rag_documents) > 0,
                "rag_query": transcript_segment[:200],
                "rag_documents": rag_documents,
                "rag_sources": rag_sources,
                "rag_top_k": 7,
                "rag_similarity_threshold": 0.35,
                "rag_search_time_ms": None,  # Not tracked separately yet
                # Model metadata
                "provider": "gemini",
                "model_name": "gemini-3-flash-preview",
                "model_version": "3.0",
                # Timing breakdown
                "start_time": analysis_start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_ms": duration_ms,
                "api_response_time_ms": duration_ms,  # Same as duration for now
                "llm_call_time_ms": None,  # Not tracked separately yet
                # Token usage
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
                # LLM response
                "llm_raw_response": llm_raw_response,
                "analysis_reasoning": result_data.get(
                    "counselor_insights"
                ),  # For career tenant
                "matched_suggestions": quick_suggestions
                if resolved_tenant == "island_parents"
                else [],
                # Cache metadata
                "use_cache": False,  # Not using cache yet
                "cache_hit": None,
                "cache_key": None,
                "gemini_cache_ttl": None,
                # Technical metrics
                "transcript_length": len(transcript_segment),
                "duration_seconds": None,  # Not applicable for realtime
            }

            return result_data

        except Exception as e:
            logger.error(f"Keyword analysis failed for tenant {analysis_type}: {e}")
            # Return fallback result based on tenant
            return self._get_tenant_fallback_result(analysis_type)

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

        Args:
            session: Session model
            client: Client model
            case: Case model
            transcript_segment: Recent transcript text (e.g., last 60 seconds)
            counselor_id: Counselor UUID
            tenant_id: Tenant identifier (career, island_parents)

        Returns:
            Dict with tenant-specific analysis results + metadata for persistence
        """
        import time
        import uuid

        start_time = time.time()
        analysis_start_time = datetime.now(timezone.utc)

        # Resolve tenant alias using PromptRegistry
        resolved_tenant = PromptRegistry.TENANT_ALIAS.get(tenant_id, tenant_id)

        try:
            # Build context
            context_str = self._build_context(session, client, case)

            # Get full transcript from session
            full_transcript = session.transcript_text or "（尚無完整逐字稿）"

            # STEP 1: Retrieve RAG documents FIRST (before Gemini call)
            rag_documents = []
            rag_sources = []
            rag_context = ""
            try:
                rag_category = self.TENANT_RAG_CATEGORIES.get(resolved_tenant)
                if rag_category:
                    rag_results = await self.rag_retriever.search(
                        query=transcript_segment[:200],
                        top_k=3,
                        threshold=0.7,
                        db=self.db,
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

                    # Build RAG context string to include in prompt
                    if rag_documents:
                        rag_context = "\n\n## 參考知識庫\n" + "\n\n".join(
                            [
                                f"【{doc['title']}】\n{doc['content']}"
                                for doc in rag_documents[:3]
                            ]
                        )
            except Exception as e:
                logger.warning(f"RAG retrieval failed for tenant {tenant_id}: {e}")
                # Continue without RAG documents

            # STEP 2: Get tenant-specific prompt using PromptRegistry
            # PromptRegistry handles mode and fallback automatically
            prompt_template = PromptRegistry.get_prompt(
                resolved_tenant,
                "deep",  # Deep analysis prompt type
                mode=mode.value,
            )

            # STEP 3: Build prompt WITH RAG context
            prompt = prompt_template.format(
                context=context_str + rag_context,  # Include RAG context here!
                full_transcript=full_transcript,
                transcript_segment=transcript_segment[:500],
            )

            # STEP 4: Call Gemini AI with complete prompt (including RAG)
            ai_response = await self.gemini_service.generate_text(
                prompt, temperature=0.3, response_format={"type": "json_object"}
            )

            # STEP 5: Parse AI response
            result_data = self._parse_ai_response(ai_response)

            # STEP 5.5: Generate 200-sentence expert suggestions (ONLY for island_parents)
            if resolved_tenant == "island_parents":
                safety_level = result_data.get("safety_level", "green")
                num_suggestions = 1  # Always 1 suggestion (both emergency and practice)

                quick_suggestions = await _select_expert_suggestions(
                    transcript=transcript_segment,
                    safety_level=safety_level,
                    num_suggestions=num_suggestions,
                    gemini_service=self.gemini_service,
                )

                # Add quick_suggestions to result
                result_data["quick_suggestions"] = quick_suggestions

                # If emergency mode, remove detailed scripts (not needed)
                if mode == CounselingMode.emergency:
                    result_data["detailed_scripts"] = []
                    result_data["theoretical_frameworks"] = []

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

                # Estimate cost (Gemini 3 Flash pricing: $0.50/1M input, $3/1M output)
                input_cost = Decimal(prompt_tokens) * Decimal("0.00000050")
                output_cost = Decimal(completion_tokens) * Decimal("0.000003")
                estimated_cost = input_cost + output_cost

            # Calculate timing
            end_time = datetime.now(timezone.utc)
            duration_ms = int((time.time() - start_time) * 1000)

            # Extract LLM raw response
            llm_raw_response = (
                ai_response.text if hasattr(ai_response, "text") else str(ai_response)
            )

            # Add RAG documents and complete metadata to result
            result_data["rag_documents"] = rag_documents
            result_data["_metadata"] = {
                # Request metadata
                "request_id": str(uuid.uuid4()),
                "mode": mode.value,  # counseling mode: emergency or practice
                # Input data
                "time_range": None,  # Not applicable for partial
                "speakers": None,  # Not applicable for partial
                # Prompts
                "system_prompt": None,  # Could extract from template if needed
                "user_prompt": prompt,  # The actual prompt sent to Gemini
                "prompt_template": f"{tenant_id}_{mode.value}_v1"
                if resolved_tenant == "island_parents"
                else f"{tenant_id}_partial_v1",
                # RAG information
                "rag_used": len(rag_documents) > 0,
                "rag_query": transcript_segment[:200],
                "rag_documents": rag_documents,
                "rag_sources": rag_sources,
                "rag_top_k": 3,
                "rag_similarity_threshold": 0.7,
                "rag_search_time_ms": None,  # Not tracked separately yet
                # Model metadata
                "provider": "gemini",
                "model_name": "gemini-3-flash-preview",
                "model_version": "3.0",
                # Timing breakdown
                "start_time": analysis_start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_ms": duration_ms,
                "api_response_time_ms": duration_ms,  # Same as duration for now
                "llm_call_time_ms": None,  # Not tracked separately yet
                # Token usage
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
                # LLM response
                "llm_raw_response": llm_raw_response,
                "analysis_reasoning": result_data.get(
                    "counselor_insights"
                ),  # For career tenant
                "matched_suggestions": [],  # Not applicable for partial
                # Cache metadata
                "use_cache": False,  # Not using cache yet
                "cache_hit": None,
                "cache_key": None,
                "gemini_cache_ttl": None,
                # Technical metrics
                "transcript_length": len(transcript_segment),
                "duration_seconds": None,  # Not applicable for partial
            }

            return result_data

        except Exception as e:
            logger.error(f"Partial analysis failed for tenant {tenant_id}: {e}")
            # Return fallback result based on tenant
            return self._get_tenant_fallback_result(tenant_id)

    def _parse_iso_datetime(self, iso_string: str) -> datetime:
        """Parse ISO datetime string to datetime object"""
        from datetime import datetime

        if isinstance(iso_string, str):
            return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return iso_string

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
        """
        Save SessionAnalysisLog and update SessionUsage (cumulative ledger).
        Should be called as background task after analyze_partial.

        SessionUsage is a cumulative ledger that tracks:
        - analysis_count: Total number of analyses performed
        - total_tokens: Sum of all tokens used across analyses
        - credits_deducted: Total credits consumed
        - start_time: First analysis timestamp
        - end_time: Latest analysis timestamp

        Args:
            session_id: Session UUID
            counselor_id: Counselor UUID
            tenant_id: Tenant identifier
            transcript_segment: Transcript segment
            result_data: Analysis results (includes _metadata)
            rag_documents: RAG documents used
            rag_sources: RAG source references
            token_usage_data: Token usage info (prompt_tokens, completion_tokens, etc.)
        """
        import uuid

        try:
            # Extract metadata
            metadata = result_data.get("_metadata", {})

            # Parse ISO datetime strings back to datetime objects
            start_time = metadata.get("start_time")
            if start_time and isinstance(start_time, str):
                start_time = self._parse_iso_datetime(start_time)

            end_time = metadata.get("end_time")
            if end_time and isinstance(end_time, str):
                end_time = self._parse_iso_datetime(end_time)

            # Create SessionAnalysisLog with complete GBQ-aligned fields
            analysis_log = SessionAnalysisLog(
                session_id=session_id,
                counselor_id=counselor_id,
                tenant_id=tenant_id,
                # Analysis metadata
                analysis_type="partial_analysis",
                transcript=transcript_segment,
                analysis_result=result_data,
                # Safety assessment
                safety_level=result_data.get("safety_level"),
                severity=str(result_data.get("severity"))
                if result_data.get("severity")
                else None,
                display_text=result_data.get("display_text"),
                action_suggestion=result_data.get("action_suggestion"),
                # Request metadata
                request_id=metadata.get("request_id", str(uuid.uuid4())),
                mode=metadata.get("mode", "analyze_partial"),
                # Input data
                time_range=metadata.get("time_range"),
                speakers=metadata.get("speakers"),
                # Prompts
                system_prompt=metadata.get("system_prompt"),
                user_prompt=metadata.get("user_prompt"),
                prompt_template=metadata.get("prompt_template"),
                # RAG information
                rag_documents=rag_documents,
                rag_sources=rag_sources,
                rag_used=metadata.get("rag_used", False),
                rag_query=metadata.get("rag_query"),
                rag_top_k=metadata.get("rag_top_k"),
                rag_similarity_threshold=metadata.get("rag_similarity_threshold"),
                rag_search_time_ms=metadata.get("rag_search_time_ms"),
                # Model metadata
                provider=metadata.get("provider", "gemini"),
                model_name=metadata.get("model_name", "gemini-3-flash-preview"),
                model_version=metadata.get("model_version", "3.0"),
                # Timing breakdown
                start_time=start_time,
                end_time=end_time,
                duration_ms=metadata.get("duration_ms"),
                api_response_time_ms=metadata.get("api_response_time_ms"),
                llm_call_time_ms=metadata.get("llm_call_time_ms"),
                # Technical metrics
                transcript_length=metadata.get(
                    "transcript_length", len(transcript_segment)
                ),
                duration_seconds=metadata.get("duration_seconds"),
                # Token usage
                token_usage=metadata.get("token_usage", token_usage_data),
                prompt_tokens=token_usage_data.get("prompt_tokens", 0),
                completion_tokens=token_usage_data.get("completion_tokens", 0),
                total_tokens=token_usage_data.get("total_tokens", 0),
                cached_tokens=metadata.get("cached_tokens", 0),
                # Cost
                estimated_cost_usd=Decimal(
                    str(token_usage_data.get("estimated_cost_usd", 0))
                ),
                # LLM response
                llm_raw_response=metadata.get("llm_raw_response"),
                analysis_reasoning=metadata.get("analysis_reasoning"),
                matched_suggestions=metadata.get("matched_suggestions"),
                # Cache metadata
                use_cache=metadata.get("use_cache"),
                cache_hit=metadata.get("cache_hit"),
                cache_key=metadata.get("cache_key"),
                gemini_cache_ttl=metadata.get("gemini_cache_ttl"),
                # Timestamp
                analyzed_at=end_time or datetime.now(timezone.utc),
            )
            self.db.add(analysis_log)

            # Get or create SessionUsage (cumulative ledger pattern)
            session_usage = (
                self.db.query(SessionUsage)
                .filter(
                    SessionUsage.session_id == session_id,
                    SessionUsage.tenant_id == tenant_id,
                )
                .first()
            )

            # Extract token usage
            prompt_tokens = token_usage_data.get("prompt_tokens", 0)
            completion_tokens = token_usage_data.get("completion_tokens", 0)
            total_tokens = token_usage_data.get("total_tokens", 0)
            estimated_cost = Decimal(str(token_usage_data.get("estimated_cost_usd", 0)))

            current_time = datetime.now(timezone.utc)

            # ============================================================
            # INCREMENTAL BILLING WITH CEILING ROUNDING (1 credit = 1 minute)
            # ============================================================

            # Get counselor for credit deduction
            counselor = (
                self.db.query(Counselor).filter(Counselor.id == counselor_id).first()
            )

            if not counselor:
                logger.error(
                    f"Counselor {counselor_id} not found, cannot deduct credits"
                )
                self.db.commit()  # Still save analysis log
                return

            if session_usage:
                # UPDATE existing SessionUsage (subsequent analysis)
                # Calculate current duration and apply ceiling rounding
                if session_usage.start_time:
                    duration_seconds = int(
                        (current_time - session_usage.start_time).total_seconds()
                    )
                    current_minutes = math.ceil(duration_seconds / 60)
                    already_billed = session_usage.last_billed_minutes or 0
                    new_minutes = current_minutes - already_billed

                    logger.info(
                        f"Billing calculation: duration={duration_seconds}s, "
                        f"current_minutes={current_minutes}, already_billed={already_billed}, "
                        f"new_minutes={new_minutes}"
                    )

                    if new_minutes > 0:
                        # Deduct credits (1 credit = 1 minute)
                        credits_to_deduct = float(new_minutes)

                        # 1. Update Counselor (decrement available_credits)
                        counselor.available_credits -= credits_to_deduct

                        # 2. Update SessionUsage (cache)
                        session_usage.credits_deducted = (
                            session_usage.credits_deducted or Decimal("0.0")
                        ) + Decimal(str(credits_to_deduct))
                        session_usage.last_billed_minutes = current_minutes

                        # 3. Write CreditLog (authoritative source)
                        credit_log = CreditLog(
                            counselor_id=counselor_id,
                            resource_type="session",
                            resource_id=str(session_id),
                            credits_delta=-credits_to_deduct,  # Negative for usage
                            transaction_type="usage",
                            raw_data={
                                "feature": "session_analysis",
                                "duration_seconds": duration_seconds,
                                "current_minutes": current_minutes,
                                "incremental_minutes": new_minutes,
                                "analysis_type": "partial_analysis",
                                "tenant_id": tenant_id,
                            },
                            rate_snapshot={
                                "unit": "minute",
                                "rate": 1.0,
                                "rounding": "ceil",
                            },
                            calculation_details={
                                "duration_seconds": duration_seconds,
                                "current_minutes": current_minutes,
                                "already_billed_minutes": already_billed,
                                "new_minutes": new_minutes,
                                "credits_deducted": credits_to_deduct,
                            },
                        )
                        self.db.add(credit_log)

                        logger.info(
                            f"Deducted {credits_to_deduct} credits for session {session_id}: "
                            f"counselor.available_credits={counselor.available_credits}"
                        )
                    else:
                        logger.info(
                            f"No new minutes to bill for session {session_id} "
                            f"(current={current_minutes}, already_billed={already_billed})"
                        )

                # Update cumulative metrics (existing logic)
                session_usage.analysis_count = (session_usage.analysis_count or 0) + 1
                session_usage.total_prompt_tokens = (
                    session_usage.total_prompt_tokens or 0
                ) + prompt_tokens
                session_usage.total_completion_tokens = (
                    session_usage.total_completion_tokens or 0
                ) + completion_tokens
                session_usage.total_tokens = (
                    session_usage.total_tokens or 0
                ) + total_tokens
                session_usage.estimated_cost_usd = (
                    session_usage.estimated_cost_usd or Decimal("0.0")
                ) + estimated_cost
                session_usage.end_time = current_time
                session_usage.duration_seconds = (
                    duration_seconds if session_usage.start_time else 0
                )

                logger.info(
                    f"Updated SessionUsage for session {session_id}: "
                    f"analysis_count={session_usage.analysis_count}, "
                    f"total_tokens={session_usage.total_tokens}, "
                    f"credits_deducted={session_usage.credits_deducted}"
                )
            else:
                # CREATE new SessionUsage (first analysis)
                # First analysis at time T → charge ceil(T/60) minutes
                duration_seconds = 0  # First analysis starts at 0
                current_minutes = 1  # Minimum charge is 1 minute (0:01-1:00 = 1 min)
                credits_to_deduct = 1.0  # 1 credit for first minute

                # 1. Update Counselor
                counselor.available_credits -= credits_to_deduct

                # 2. Create SessionUsage (cache)
                session_usage = SessionUsage(
                    session_id=session_id,
                    counselor_id=counselor_id,
                    tenant_id=tenant_id,
                    usage_type="partial_analysis",
                    status="in_progress",
                    start_time=current_time,
                    end_time=current_time,
                    duration_seconds=duration_seconds,
                    analysis_count=1,
                    total_prompt_tokens=prompt_tokens,
                    total_completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_usd=estimated_cost,
                    pricing_rule={"unit": "minute", "rate": 1.0, "rounding": "ceil"},
                    credits_deducted=Decimal(str(credits_to_deduct)),
                    last_billed_minutes=current_minutes,
                )
                self.db.add(session_usage)

                # 3. Write CreditLog (authoritative)
                credit_log = CreditLog(
                    counselor_id=counselor_id,
                    resource_type="session",
                    resource_id=str(session_id),
                    credits_delta=-credits_to_deduct,
                    transaction_type="usage",
                    raw_data={
                        "feature": "session_analysis",
                        "duration_seconds": duration_seconds,
                        "current_minutes": current_minutes,
                        "incremental_minutes": current_minutes,
                        "analysis_type": "partial_analysis",
                        "tenant_id": tenant_id,
                    },
                    rate_snapshot={
                        "unit": "minute",
                        "rate": 1.0,
                        "rounding": "ceil",
                    },
                    calculation_details={
                        "duration_seconds": duration_seconds,
                        "current_minutes": current_minutes,
                        "already_billed_minutes": 0,
                        "new_minutes": current_minutes,
                        "credits_deducted": credits_to_deduct,
                    },
                )
                self.db.add(credit_log)

                logger.info(
                    f"Created SessionUsage for session {session_id}: "
                    f"total_tokens={total_tokens}, "
                    f"credits_deducted={credits_to_deduct}, "
                    f"last_billed_minutes={current_minutes}"
                )

            # Commit all changes
            self.db.commit()
            logger.info(
                f"Saved analysis log and updated usage for session {session_id}"
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save analysis log: {e}", exc_info=True)

    def _get_tenant_fallback_result(self, tenant_id: str) -> Dict:
        """Get tenant-specific fallback result when AI analysis fails"""
        # Resolve tenant alias using PromptRegistry
        resolved_tenant = PromptRegistry.TENANT_ALIAS.get(tenant_id, tenant_id)

        # Common metadata for fallback (no tokens used since AI call failed)
        fallback_metadata = {
            "token_usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
        }

        if resolved_tenant == "island_parents":
            return {
                "safety_level": "green",
                "severity": 1,
                "display_text": "正在分析親子對話...",
                "action_suggestion": "持續觀察溝通狀況",
                "suggested_interval_seconds": 20,
                "keywords": ["分析中"],
                "categories": ["一般"],
                "quick_suggestions": [],  # Empty for fallback
                "rag_documents": [],
                "_metadata": fallback_metadata,
            }
        else:  # career (default)
            return {
                "keywords": ["探索中", "諮詢進行"],
                "categories": ["一般諮詢"],
                "confidence": 0.5,
                "counselor_insights": "持續觀察案主狀態。",
                "safety_level": "green",
                "severity": 1,
                "display_text": "分析中",
                "action_suggestion": "持續關注案主需求",
                "rag_documents": [],
                "_metadata": fallback_metadata,
            }

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
        # Extract text from response object if needed
        if hasattr(ai_response, "text"):
            response_text = ai_response.text
        elif isinstance(ai_response, str):
            response_text = ai_response
        else:
            # Unknown type, try to use it as-is
            return ai_response

        # Parse JSON from text
        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            else:
                # Quick fallback
                return self._get_default_result()
        except json.JSONDecodeError:
            return self._get_default_result()

    def _get_default_result(self) -> Dict:
        """Get default keyword analysis result"""
        return {
            "keywords": ["探索中", "情緒", "發展"],
            "categories": ["一般諮詢"],
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
            found_keywords = ["探索中", "諮詢進行"]
            categories = {"一般諮詢"}

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
