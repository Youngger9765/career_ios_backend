"""
Unit tests for AI output validation helpers

Tests the centralized validation utilities for AI-generated text.
"""
import logging
from unittest.mock import Mock

import pytest

from app.services.utils.ai_validation import (
    apply_fallback_if_invalid,
    validate_ai_output_length,
    validate_finish_reason,
)


class TestValidateAiOutputLength:
    """Tests for validate_ai_output_length function"""

    def test_valid_output_within_range(self):
        """Should return text unchanged when within min/max range"""
        text = "這是一個測試訊息"  # 8 chars
        result = validate_ai_output_length(
            text=text,
            min_chars=5,
            max_chars=20,
            field_name="test_field"
        )
        assert result == text

    def test_too_short_returns_none(self):
        """Should return None when text is too short"""
        text = "短"  # 1 char
        result = validate_ai_output_length(
            text=text,
            min_chars=5,
            max_chars=20,
            field_name="test_field"
        )
        assert result is None

    def test_too_long_returns_text_with_warning(self, caplog):
        """Should return text and log warning when too long"""
        text = "這是一個非常長的測試訊息超過了限制"  # 17 chars
        with caplog.at_level(logging.WARNING):
            result = validate_ai_output_length(
                text=text,
                min_chars=5,
                max_chars=15,
                field_name="test_field"
            )
        assert result == text
        assert "test_field over 15 chars" in caplog.text
        assert "17 chars" in caplog.text

    def test_empty_string_too_short(self):
        """Should return None for empty string"""
        result = validate_ai_output_length(
            text="",
            min_chars=5,
            max_chars=20,
            field_name="test_field"
        )
        assert result is None

    def test_exact_min_boundary(self):
        """Should accept text exactly at min_chars"""
        text = "五字訊息完"  # 5 chars
        result = validate_ai_output_length(
            text=text,
            min_chars=5,
            max_chars=20,
            field_name="test_field"
        )
        assert result == text

    def test_exact_max_boundary(self):
        """Should accept text exactly at max_chars"""
        text = "十五字的測試訊息剛好完整"  # 12 chars
        result = validate_ai_output_length(
            text=text,
            min_chars=5,
            max_chars=12,
            field_name="test_field"
        )
        assert result == text

    def test_whitespace_only_too_short(self):
        """Should return None for whitespace-only text"""
        text = "   "  # 3 spaces
        result = validate_ai_output_length(
            text=text.strip(),  # Service should strip first
            min_chars=5,
            max_chars=20,
            field_name="test_field"
        )
        assert result is None

    def test_logs_warning_for_too_short(self, caplog):
        """Should log warning when text is too short"""
        text = "短"  # 1 char
        with caplog.at_level(logging.WARNING):
            validate_ai_output_length(
                text=text,
                min_chars=5,
                max_chars=20,
                field_name="test_field"
            )
        assert "test_field too short" in caplog.text
        assert "1 chars" in caplog.text


class TestValidateFinishReason:
    """Tests for validate_finish_reason function"""

    def test_normal_completion_gemini(self):
        """Should return True for Gemini STOP finish reason"""
        mock_response = Mock()
        mock_response.candidates = [Mock(finish_reason=1)]  # 1 = STOP

        result = validate_finish_reason(mock_response, "gemini")
        assert result is True

    def test_max_tokens_gemini_logs_warning(self, caplog):
        """Should log warning for Gemini MAX_TOKENS finish reason"""
        mock_response = Mock()
        mock_response.candidates = [Mock(finish_reason=2)]  # 2 = MAX_TOKENS

        with caplog.at_level(logging.WARNING):
            result = validate_finish_reason(mock_response, "gemini")

        assert result is False
        assert "truncated" in caplog.text.lower()
        assert "MAX_TOKENS" in caplog.text or "2" in caplog.text

    def test_safety_stop_gemini_logs_warning(self, caplog):
        """Should log warning for Gemini SAFETY finish reason"""
        mock_response = Mock()
        mock_response.candidates = [Mock(finish_reason=3)]  # 3 = SAFETY

        with caplog.at_level(logging.WARNING):
            result = validate_finish_reason(mock_response, "gemini")

        assert result is False
        assert "SAFETY" in caplog.text or "3" in caplog.text

    def test_no_candidates_returns_false(self, caplog):
        """Should return False when response has no candidates"""
        mock_response = Mock()
        mock_response.candidates = []

        with caplog.at_level(logging.WARNING):
            result = validate_finish_reason(mock_response, "gemini")

        assert result is False
        assert "no candidates" in caplog.text.lower()

    def test_no_finish_reason_attribute_returns_true(self):
        """Should return True (assume success) when no finish_reason attribute"""
        mock_response = Mock()
        mock_response.candidates = [Mock(spec=[])]  # No finish_reason attribute

        result = validate_finish_reason(mock_response, "gemini")
        assert result is True

    def test_openai_stop_finish_reason(self):
        """Should return True for OpenAI 'stop' finish reason"""
        mock_response = Mock()
        mock_response.choices = [Mock(finish_reason="stop")]

        result = validate_finish_reason(mock_response, "openai")
        assert result is True

    def test_openai_length_finish_reason_logs_warning(self, caplog):
        """Should log warning for OpenAI 'length' finish reason"""
        mock_response = Mock()
        mock_response.choices = [Mock(finish_reason="length")]

        with caplog.at_level(logging.WARNING):
            result = validate_finish_reason(mock_response, "openai")

        assert result is False
        assert "truncated" in caplog.text.lower() or "length" in caplog.text.lower()

    def test_unknown_provider_returns_true(self):
        """Should return True for unknown provider (defensive)"""
        mock_response = Mock()

        result = validate_finish_reason(mock_response, "unknown_provider")
        assert result is True


class TestApplyFallbackIfInvalid:
    """Tests for apply_fallback_if_invalid function"""

    def test_valid_text_returns_unchanged(self):
        """Should return original text when valid"""
        text = "有效的訊息內容"
        result = apply_fallback_if_invalid(
            text=text,
            min_chars=5,
            max_chars=20,
            fallback="備用訊息",
            field_name="test_field"
        )
        assert result == text

    def test_too_short_returns_fallback(self):
        """Should return fallback when text is too short"""
        text = "短"
        fallback = "備用訊息內容"
        result = apply_fallback_if_invalid(
            text=text,
            min_chars=5,
            max_chars=20,
            fallback=fallback,
            field_name="test_field"
        )
        assert result == fallback

    def test_empty_string_returns_fallback(self):
        """Should return fallback for empty string"""
        text = ""
        fallback = "備用訊息內容"
        result = apply_fallback_if_invalid(
            text=text,
            min_chars=5,
            max_chars=20,
            fallback=fallback,
            field_name="test_field"
        )
        assert result == fallback

    def test_too_long_returns_original_with_warning(self, caplog):
        """Should return original text when too long (with warning)"""
        text = "這是一個非常長的測試訊息超過了最大限制"
        with caplog.at_level(logging.WARNING):
            result = apply_fallback_if_invalid(
                text=text,
                min_chars=5,
                max_chars=15,
                fallback="備用訊息",
                field_name="test_field"
            )
        assert result == text  # Returns original, not fallback
        assert "over 15 chars" in caplog.text

    def test_list_fallback_uses_first_item(self):
        """Should use first item from list fallback"""
        text = "短"
        fallback_list = ["第一個備用", "第二個備用", "第三個備用"]
        result = apply_fallback_if_invalid(
            text=text,
            min_chars=5,
            max_chars=20,
            fallback=fallback_list,
            field_name="test_field"
        )
        assert result in fallback_list  # Could be any item (random choice)

    def test_none_text_returns_fallback(self):
        """Should return fallback when text is None"""
        fallback = "備用訊息內容"
        result = apply_fallback_if_invalid(
            text=None,
            min_chars=5,
            max_chars=20,
            fallback=fallback,
            field_name="test_field"
        )
        assert result == fallback

    def test_logs_fallback_usage(self, caplog):
        """Should log when fallback is used"""
        text = "短"
        with caplog.at_level(logging.WARNING):
            apply_fallback_if_invalid(
                text=text,
                min_chars=5,
                max_chars=20,
                fallback="備用訊息",
                field_name="test_field"
            )
        assert "using fallback" in caplog.text.lower()
