"""
Simplified keyword analysis implementation.

Single-call analysis optimized for low latency (15s vs 40s).
"""

import logging
import random
import time
from typing import Dict, Optional

from app.config.parenting_suggestions import (
    GREEN_SUGGESTIONS,
    RED_SUGGESTIONS,
    YELLOW_SUGGESTIONS,
)
from app.prompts import PromptRegistry
from app.services.analysis.analysis_helpers import parse_ai_response
from app.services.analysis.keyword_analysis.metadata import MetadataBuilder
from app.services.analysis.keyword_analysis.validators import ResponseValidator
from app.services.external.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class SimplifiedAnalyzer:
    """Handles simplified keyword analysis for real-time scenarios"""

    def __init__(self, gemini_service: GeminiService):
        self.gemini_service = gemini_service

    async def analyze_simplified(
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

            # Ensure required fields and validate
            ResponseValidator.ensure_required_fields(result)
            result["display_text"] = ResponseValidator.validate_display_text(result)
            quick_suggestion = ResponseValidator.validate_quick_suggestion(result)

            # Wrap quick_suggestion in list for compatibility
            result["quick_suggestions"] = [quick_suggestion] if quick_suggestion else []

            # Add metadata with REAL token usage
            duration_ms = int((time.time() - start_time) * 1000)
            result["_metadata"] = MetadataBuilder.build_simplified_metadata(
                mode=mode,
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
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
