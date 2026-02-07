"""
Metadata building utilities for keyword analysis.

Handles construction of analysis metadata including token usage, timing, and RAG info.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List

from app.schemas.session import CounselingMode

logger = logging.getLogger(__name__)


class MetadataBuilder:
    """Builds metadata dictionaries for analysis results"""

    @staticmethod
    def build_metadata(
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
        """
        Build comprehensive metadata dict for analysis result.

        Args:
            ai_response: AI service response object
            analysis_type: Original tenant type
            mode_enum: Counseling mode
            resolved_tenant: Resolved tenant identifier
            prompt: Full prompt sent to AI
            transcript_segment: Transcript text analyzed
            rag_documents: Retrieved RAG documents
            rag_sources: RAG source names
            analysis_start_time: Analysis start timestamp
            start_time: Start time (time.time())
            quick_suggestions: Selected expert suggestions
            result_data: Parsed AI response data

        Returns:
            Metadata dictionary
        """
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

            # Estimate cost (Gemini Flash 3 pricing)
            # Input: $0.50 per 1M tokens, Output: $3.00 per 1M tokens
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
            "model_name": "gemini-1.5-flash-latest",  # Correct model name for deep analysis
            "model_version": "1.5",
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

    @staticmethod
    def build_simplified_metadata(
        mode: str,
        duration_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Dict:
        """
        Build simplified metadata for quick analysis.

        Args:
            mode: Analysis mode
            duration_ms: Duration in milliseconds
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Simplified metadata dictionary
        """
        # Calculate Gemini Flash 3 cost
        # Input: $0.50 per 1M tokens, Output: $3.00 per 1M tokens
        input_cost = (prompt_tokens / 1_000_000) * 0.50
        output_cost = (completion_tokens / 1_000_000) * 3.00
        estimated_cost_usd = input_cost + output_cost

        return {
            "mode": mode,
            "duration_ms": duration_ms,
            "prompt_type": "deep_simplified",
            "rag_used": False,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "estimated_cost_usd": estimated_cost_usd,
            "model_name": "gemini-1.5-flash-latest",  # Correct model for deep analysis
            "provider": "gemini",
        }
