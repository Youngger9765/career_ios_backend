"""
AI Output Validation Utilities

Centralized validation helpers for AI-generated text to prevent truncation,
ensure output quality, and provide graceful degradation.

Based on lessons learned from 2026-01-08 truncation bugs in:
- Quick Feedback (max_tokens too small)
- Report (hard truncation mid-sentence)
- Deep Analyze (missing validation)
"""
import logging
import random
from typing import Any, List, Optional, Union

logger = logging.getLogger(__name__)


def validate_ai_output_length(
    text: str,
    min_chars: int,
    max_chars: int,
    field_name: str = "output",
) -> Optional[str]:
    """
    Validate AI output length is within acceptable range.

    Args:
        text: AI-generated text to validate
        min_chars: Minimum acceptable character count
        max_chars: Maximum acceptable character count
        field_name: Name of field being validated (for logging)

    Returns:
        The original text if valid, None if too short.
        Returns original text even if too long (with warning log).

    Examples:
        >>> validate_ai_output_length("你做得很好", min_chars=5, max_chars=15, field_name="hint")
        "你做得很好"

        >>> validate_ai_output_length("短", min_chars=5, max_chars=15, field_name="hint")
        None  # Too short, returns None
    """
    text_length = len(text)

    # Check if too short
    if text_length < min_chars:
        logger.warning(
            f"{field_name} too short ({text_length} chars): '{text}', "
            f"expected at least {min_chars} chars"
        )
        return None

    # Check if too long (log warning but don't truncate)
    if text_length > max_chars:
        logger.warning(
            f"{field_name} over {max_chars} chars: "
            f"{text_length} chars - '{text[:30]}...'"
        )
        # Return original text - don't hard truncate mid-sentence

    return text


def validate_finish_reason(
    response: Any,
    provider: str = "gemini",
) -> bool:
    """
    Check if AI response completed normally (not truncated).

    Args:
        response: AI provider response object (Gemini or OpenAI format)
        provider: AI provider name ("gemini" or "openai")

    Returns:
        True if response completed normally, False if truncated/interrupted

    Examples:
        # Gemini response
        >>> response.candidates[0].finish_reason = 1  # STOP
        >>> validate_finish_reason(response, "gemini")
        True

        # Truncated response
        >>> response.candidates[0].finish_reason = 2  # MAX_TOKENS
        >>> validate_finish_reason(response, "gemini")
        False  # Logs warning
    """
    if provider == "gemini":
        return _validate_gemini_finish_reason(response)
    elif provider == "openai":
        return _validate_openai_finish_reason(response)
    else:
        # Unknown provider - assume success (defensive)
        logger.debug(f"Unknown provider '{provider}' - skipping finish_reason check")
        return True


def _validate_gemini_finish_reason(response: Any) -> bool:
    """
    Validate Gemini response finish_reason.

    Gemini finish_reason values:
    - 1: STOP (normal completion)
    - 2: MAX_TOKENS (truncated due to max_tokens limit)
    - 3: SAFETY (blocked by safety filters)
    - 4: RECITATION (blocked due to recitation)
    - 5: OTHER

    Returns:
        True if STOP, False otherwise
    """
    if not hasattr(response, "candidates") or not response.candidates:
        logger.warning("Gemini response has no candidates - possible error")
        return False

    candidate = response.candidates[0]

    if not hasattr(candidate, "finish_reason"):
        # No finish_reason attribute - assume success
        return True

    finish_reason = candidate.finish_reason

    if finish_reason == 1:  # STOP - normal completion
        logger.debug("Gemini response completed normally (STOP)")
        return True

    # Log warning for non-STOP finish reasons
    reason_names = {
        2: "MAX_TOKENS (truncated)",
        3: "SAFETY (blocked)",
        4: "RECITATION (blocked)",
        5: "OTHER",
    }
    reason_name = reason_names.get(finish_reason, f"UNKNOWN ({finish_reason})")

    logger.warning(
        f"Gemini response may be incomplete. Finish reason: {reason_name}"
    )
    return False


def _validate_openai_finish_reason(response: Any) -> bool:
    """
    Validate OpenAI response finish_reason.

    OpenAI finish_reason values:
    - "stop": normal completion
    - "length": truncated due to max_tokens
    - "content_filter": blocked by content filter
    - "function_call": stopped for function call

    Returns:
        True if "stop", False otherwise
    """
    if not hasattr(response, "choices") or not response.choices:
        logger.warning("OpenAI response has no choices - possible error")
        return False

    choice = response.choices[0]

    if not hasattr(choice, "finish_reason"):
        # No finish_reason attribute - assume success
        return True

    finish_reason = choice.finish_reason

    if finish_reason == "stop":
        logger.debug("OpenAI response completed normally (stop)")
        return True

    # Log warning for non-stop finish reasons
    logger.warning(
        f"OpenAI response may be incomplete. Finish reason: {finish_reason}"
    )
    return False


def apply_fallback_if_invalid(
    text: Optional[str],
    min_chars: int,
    max_chars: int,
    fallback: Union[str, List[str]],
    field_name: str = "output",
) -> str:
    """
    Validate AI output and apply fallback if invalid.

    Combines validation and fallback logic in one function.
    If text is too short or None, returns fallback.
    If text is too long, returns original text (with warning).

    Args:
        text: AI-generated text to validate
        min_chars: Minimum acceptable character count
        max_chars: Maximum acceptable character count
        fallback: Fallback value (string or list of strings)
        field_name: Name of field being validated (for logging)

    Returns:
        Validated text or fallback value

    Examples:
        >>> apply_fallback_if_invalid(
        ...     "你做得很好",
        ...     min_chars=5,
        ...     max_chars=15,
        ...     fallback="繼續保持",
        ...     field_name="hint"
        ... )
        "你做得很好"

        >>> apply_fallback_if_invalid(
        ...     "短",
        ...     min_chars=5,
        ...     max_chars=15,
        ...     fallback=["繼續保持", "很棒"],
        ...     field_name="hint"
        ... )
        "繼續保持"  # Random choice from fallback list
    """
    # Handle None text
    if text is None:
        logger.warning(f"{field_name} is None, using fallback")
        return _get_fallback_value(fallback)

    # Validate length
    validated_text = validate_ai_output_length(
        text=text,
        min_chars=min_chars,
        max_chars=max_chars,
        field_name=field_name,
    )

    # If validation failed (too short), use fallback
    if validated_text is None:
        logger.warning(f"{field_name} validation failed, using fallback")
        return _get_fallback_value(fallback)

    # Return validated text (could be over max_chars, but not truncated)
    return validated_text


def _get_fallback_value(fallback: Union[str, List[str]]) -> str:
    """
    Get fallback value from string or list.

    Args:
        fallback: Single string or list of strings

    Returns:
        Fallback string (random choice if list)
    """
    if isinstance(fallback, list):
        return random.choice(fallback)
    return fallback
