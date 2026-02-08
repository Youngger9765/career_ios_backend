"""
Session Billing Service - Handles analysis logging and credit deduction

Extracted from keyword_analysis_service.py for better modularity.
Implements incremental billing with ceiling rounding (1 credit = 1 minute).
"""

import logging
import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List
from uuid import UUID

from sqlalchemy.orm import Session as DBSession

from app.models.counselor import Counselor
from app.models.credit_log import CreditLog
from app.models.session import Session
from app.models.session_analysis_log import SessionAnalysisLog
from app.models.session_usage import SessionUsage

logger = logging.getLogger(__name__)


class SessionBillingService:
    """Service for session billing and analysis logging"""

    def __init__(self, db: DBSession):
        self.db = db

    def _parse_iso_datetime(self, iso_string: str) -> datetime:
        """Parse ISO datetime string to datetime object"""
        if isinstance(iso_string, str):
            return datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return iso_string

    def _get_default_model_name(self, metadata: Dict) -> str:
        """
        Get default model name with warning when missing from metadata.

        This is a defensive fallback - model_name should always be provided.
        """
        logger.warning(
            "⚠️  model_name missing from _metadata! Using fallback. "
            "This indicates a bug in the analysis service. "
            f"Analysis type: {metadata.get('mode', 'unknown')}"
        )
        return "gemini-1.5-flash-latest"  # Safe default

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
                provider=token_usage_data.get("provider") or metadata.get("provider", "gemini"),
                model_name=token_usage_data.get("model_name")
                or metadata.get("model_name")
                or self._get_default_model_name(metadata),
                model_version=metadata.get("model_version", "1.5"),
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

            # Extract token usage and calculate costs
            prompt_tokens = token_usage_data.get("prompt_tokens", 0)
            completion_tokens = token_usage_data.get("completion_tokens", 0)
            total_tokens = token_usage_data.get("total_tokens", 0)

            # Gemini LLM cost (from token_usage_data)
            gemini_cost = Decimal(str(token_usage_data.get("estimated_cost_usd", 0)))

            # ElevenLabs Scribe v2 Realtime STT cost (using centralized pricing)
            from app.core.pricing import calculate_elevenlabs_cost

            session_record = (
                self.db.query(Session).filter(Session.id == session_id).first()
            )
            recordings = session_record.recordings if session_record else []
            duration_seconds = sum(
                r.get("duration_seconds", 0) for r in (recordings or [])
            )
            elevenlabs_cost = Decimal(str(calculate_elevenlabs_cost(duration_seconds)))

            # Total cost = Gemini + ElevenLabs
            estimated_cost = gemini_cost + elevenlabs_cost

            logger.info(
                f"Cost breakdown for session {session_id}: "
                f"Gemini=${float(gemini_cost):.6f}, "
                f"ElevenLabs=${float(elevenlabs_cost):.6f} ({duration_seconds}s), "
                f"Total=${float(estimated_cost):.6f}"
            )

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
                self._update_existing_usage(
                    session_usage=session_usage,
                    session_id=session_id,
                    counselor=counselor,
                    counselor_id=counselor_id,
                    tenant_id=tenant_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=estimated_cost,
                    current_time=current_time,
                )
            else:
                # CREATE new SessionUsage (first analysis)
                self._create_new_usage(
                    session_id=session_id,
                    counselor=counselor,
                    counselor_id=counselor_id,
                    tenant_id=tenant_id,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=estimated_cost,
                    current_time=current_time,
                )

            # Commit all changes
            self.db.commit()
            logger.info(
                f"Saved analysis log and updated usage for session {session_id}"
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save analysis log: {e}", exc_info=True)

    def _update_existing_usage(
        self,
        session_usage: SessionUsage,
        session_id: UUID,
        counselor: Counselor,
        counselor_id: UUID,
        tenant_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost: Decimal,
        current_time: datetime,
    ) -> None:
        """Update existing SessionUsage (subsequent analysis)"""
        # Calculate duration from RECORDING TIME (not elapsed time)
        # This ensures idle/pause time is NOT charged to user
        session_record = self.db.query(Session).filter(Session.id == session_id).first()

        # Sum up all recording segment durations
        recordings = session_record.recordings if session_record else []
        duration_seconds = sum(r.get("duration_seconds", 0) for r in (recordings or []))

        if duration_seconds > 0:
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

        # Update cumulative metrics
        session_usage.analysis_count = (session_usage.analysis_count or 0) + 1
        session_usage.total_prompt_tokens = (
            session_usage.total_prompt_tokens or 0
        ) + prompt_tokens
        session_usage.total_completion_tokens = (
            session_usage.total_completion_tokens or 0
        ) + completion_tokens
        session_usage.total_tokens = (session_usage.total_tokens or 0) + total_tokens
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

    def _create_new_usage(
        self,
        session_id: UUID,
        counselor: Counselor,
        counselor_id: UUID,
        tenant_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        estimated_cost: Decimal,
        current_time: datetime,
    ) -> None:
        """Create new SessionUsage (first analysis)"""
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
