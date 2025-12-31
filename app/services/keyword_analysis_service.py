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
from typing import Dict, List
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from app.models.case import Case
from app.models.client import Client
from app.models.counselor import Counselor  # For counselor credit updates
from app.models.credit_log import CreditLog  # For dual-write pattern
from app.models.session import Session
from app.models.session_analysis_log import SessionAnalysisLog
from app.models.session_usage import SessionUsage
from app.schemas.realtime import CounselingMode
from app.services.gemini_service import GeminiService
from app.services.openai_service import OpenAIService
from app.services.rag_retriever import RAGRetriever

logger = logging.getLogger(__name__)


class KeywordAnalysisService:
    """Service for AI-powered keyword analysis of session transcripts"""

    def __init__(self, db: DBSession):
        self.db = db
        self.gemini_service = GeminiService()
        self.openai_service = OpenAIService()
        self.rag_retriever = RAGRetriever(self.openai_service)

    # Tenant-specific prompt templates
    TENANT_PROMPTS = {
        "career": """你是職涯諮詢專家，分析個案的職涯困惑和諮詢對話。

背景資訊：
{context}

完整對話逐字稿（供參考，理解背景脈絡）：
{full_transcript}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近逐字稿 - 主要分析對象】
（請根據此區塊進行關鍵字分析）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{transcript_segment}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

請分析並返回 JSON 格式：
{{
    "keywords": ["關鍵詞1", "關鍵詞2", ...],
    "categories": ["類別1", "類別2", ...],
    "confidence": 0.85,
    "counselor_insights": "給諮詢師的洞見（50字內）",
    "safety_level": "green|yellow|red",
    "severity": 1-3,
    "display_text": "個案當前狀況描述",
    "action_suggestion": "建議諮詢師採取的行動"
}}

注意：
- keywords: 職涯相關關鍵詞（焦慮、迷惘、轉職等）
- categories: 職涯類別（職涯探索、工作壓力、人際關係等）
- safety_level: green=穩定, yellow=需關注, red=危機
- severity: 1=輕微, 2=中等, 3=嚴重
- 分析重點：最近逐字稿，完整對話僅作為背景參考
""",
        "island_parents_emergency": """你是親子教養專家，提供即時危機提醒。這是事中提醒模式，需要快速判斷和簡潔建議。

背景資訊：
{context}

完整對話逐字稿（供參考）：
{full_transcript}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近對話 - 用於安全評估】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{transcript_segment}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

請分析並返回 JSON 格式：
{{
    "safety_level": "green|yellow|red",
    "severity": 1-3,
    "display_text": "簡短狀況描述（1句話）",
    "action_suggestion": "1-2句最關鍵建議",
    "suggested_interval_seconds": 15,
    "keywords": ["關鍵詞1", "關鍵詞2"],
    "categories": ["類別1"]
}}

紅黃綠燈判斷標準：
- 🔴 RED (嚴重): 情緒崩潰、失控、衝突升級、語言暴力
- 🟡 YELLOW (需調整): 溝通不良、情緒緊張、忽略感受
- 🟢 GREEN (良好): 溝通順暢、情緒穩定、互相尊重

⚠️ EMERGENCY MODE 要求：
- 聚焦當前最需要處理的問題
- 建議必須快速可執行
- 選擇 1-2 句最關鍵建議即可
- 避免冗長說明
""",
        "island_parents_practice": """你是親子教養專家，提供詳細教學指導。這是事前練習模式，可以提供更完整的分析和建議。

背景資訊：
{context}

完整對話逐字稿（供參考，理解背景脈絡）：
{full_transcript}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近對話 - 用於安全評估】
（請根據此區塊判斷當前安全等級）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{transcript_segment}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

請分析並返回 JSON 格式：
{{
    "safety_level": "green|yellow|red",
    "severity": 1-3,
    "display_text": "給家長的提示文字",
    "action_suggestion": "詳細建議（3-4句），包含 Bridge 技巧說明",
    "suggested_interval_seconds": 30,
    "keywords": ["關鍵詞1", "關鍵詞2", "關鍵詞3"],
    "categories": ["類別1", "類別2"]
}}

紅黃綠燈判斷標準：
- 🔴 RED (嚴重): 孩子情緒崩潰、家長失控、衝突升級、語言暴力
- 🟡 YELLOW (需調整): 溝通不良、情緒緊張、單向指責、忽略感受
- 🟢 GREEN (良好): 溝通順暢、情緒穩定、互相尊重、有效傾聽

⚠️ PRACTICE MODE 要求：
- 提供 3-4 句詳細建議
- 說明 Bridge 技巧和溝通策略
- 幫助家長理解孩子行為背後的需求
- 建議具體對話方式和調整方法

⚠️ CRITICAL: 安全等級評估請只根據「【最近對話 - 用於安全評估】」區塊判斷，
完整對話僅作為理解脈絡參考。如果最近對話已緩和，即使之前有危險內容，
也應評估為較低風險。

注意：
- display_text: 描述當前親子互動狀況，給家長具體的觀察提示
- action_suggestion: 具體可行的溝通調整建議，包含教學性內容
- severity: 1=輕微, 2=中等, 3=嚴重
""",
    }

    # RAG category mapping for tenants
    TENANT_RAG_CATEGORIES = {
        "career": "career",
        "island_parents": "parenting",
    }

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

        try:
            # Build context
            context_str = self._build_context(session, client, case)

            # Get full transcript from session
            full_transcript = session.transcript_text or "（尚無完整逐字稿）"

            # Get tenant-specific prompt template (with mode support for island_parents)
            if tenant_id == "island_parents":
                # island_parents tenant: select prompt based on mode
                prompt_key = f"island_parents_{mode.value}"
                prompt_template = self.TENANT_PROMPTS.get(
                    prompt_key, self.TENANT_PROMPTS["island_parents_practice"]
                )
            else:
                # Other tenants: use tenant_id directly (mode not applicable)
                prompt_template = self.TENANT_PROMPTS.get(
                    tenant_id, self.TENANT_PROMPTS["career"]
                )

            prompt = prompt_template.format(
                context=context_str,
                full_transcript=full_transcript,
                transcript_segment=transcript_segment[:500],
            )

            # Call Gemini AI
            ai_response = await self.gemini_service.generate_text(
                prompt, temperature=0.3, response_format={"type": "json_object"}
            )

            # Parse AI response
            result_data = self._parse_ai_response(ai_response)

            # Retrieve RAG documents (optional, based on tenant)
            rag_documents = []
            rag_sources = []
            try:
                rag_category = self.TENANT_RAG_CATEGORIES.get(tenant_id)
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
            except Exception as e:
                logger.warning(f"RAG retrieval failed for tenant {tenant_id}: {e}")
                # Continue without RAG documents

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
                if tenant_id == "island_parents"
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
        if tenant_id == "island_parents":
            return {
                "safety_level": "green",
                "severity": 1,
                "display_text": "正在分析親子對話...",
                "action_suggestion": "持續觀察溝通狀況",
                "suggested_interval_seconds": 20,
                "keywords": ["分析中"],
                "categories": ["一般"],
                "rag_documents": [],
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
