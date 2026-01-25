"""
AI response validation utilities for keyword analysis.

Validates AI output fields (display_text, quick_suggestion) against length constraints.
"""

import logging
from typing import Dict

from app.services.utils.ai_validation import validate_ai_output_length

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Validates AI response fields for keyword analysis"""

    @staticmethod
    def validate_display_text(result: Dict) -> str:
        """
        Validate and sanitize display_text field.

        Args:
            result: AI response dict

        Returns:
            Validated display_text (fallback to "分析完成" if invalid)
        """
        display_text = result.get("display_text", "")
        validated_display_text = validate_ai_output_length(
            text=display_text,
            min_chars=4,  # fallback "分析完成" is 4 chars
            max_chars=20,
            field_name="display_text",
        )
        if validated_display_text is None:
            return "分析完成"
        return validated_display_text

    @staticmethod
    def validate_quick_suggestion(result: Dict) -> str:
        """
        Validate and sanitize quick_suggestion field.

        Args:
            result: AI response dict

        Returns:
            Validated quick_suggestion (empty string if invalid)
        """
        quick_suggestion = result.get("quick_suggestion", "")
        if not quick_suggestion:
            return ""

        validated_suggestion = validate_ai_output_length(
            text=quick_suggestion,
            min_chars=5,  # shortest expert suggestion is 5 chars
            max_chars=20,  # longest expert suggestion is 17 chars
            field_name="quick_suggestion",
        )
        if validated_suggestion is None:
            return ""
        return validated_suggestion

    @staticmethod
    def ensure_required_fields(result: Dict) -> None:
        """
        Ensure required fields exist in result dict (in-place modification).

        Args:
            result: AI response dict to validate
        """
        result.setdefault("safety_level", "green")
        result.setdefault("display_text", "分析完成")
        result.setdefault("quick_suggestion", "")
