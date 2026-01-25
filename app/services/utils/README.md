# AI Validation Utilities

Centralized validation helpers for AI-generated text to ensure output quality and prevent common issues like truncation.

## Overview

This module provides reusable validation functions that have been extracted from scattered validation logic across multiple services. Based on lessons learned from 2026-01-08 truncation bugs.

## Core Functions

### `validate_ai_output_length()`

Validates AI output is within acceptable character length range.

**Usage:**
```python
from app.services.utils.ai_validation import validate_ai_output_length

text = "你做得很好"
validated = validate_ai_output_length(
    text=text,
    min_chars=5,
    max_chars=15,
    field_name="hint"
)

if validated is None:
    # Text was too short, use fallback
    text = "繼續保持"
else:
    text = validated
```

**Behavior:**
- Returns `None` if text is too short (below min_chars)
- Returns original text if within range
- Returns original text with warning log if too long (does NOT truncate)

### `validate_finish_reason()`

Checks if AI response completed normally (not truncated due to max_tokens or safety filters).

**Usage:**
```python
from app.services.utils.ai_validation import validate_finish_reason

response = await gemini_service.generate_text(prompt, max_tokens=500)

if not validate_finish_reason(response, provider="gemini"):
    logger.warning("Response was truncated - consider increasing max_tokens")
    # Apply fallback or retry logic
```

**Supported Providers:**
- `"gemini"`: Checks Gemini finish_reason values (1=STOP is OK, 2=MAX_TOKENS is truncated)
- `"openai"`: Checks OpenAI finish_reason values ("stop" is OK, "length" is truncated)

### `apply_fallback_if_invalid()`

Combines validation and fallback logic in one convenient function.

**Usage:**
```python
from app.services.utils.ai_validation import apply_fallback_if_invalid

# With single fallback
message = apply_fallback_if_invalid(
    text=ai_response,
    min_chars=7,
    max_chars=15,
    fallback="繼續保持，你做得很好",
    field_name="quick_feedback"
)

# With list of fallbacks (random choice)
message = apply_fallback_if_invalid(
    text=ai_response,
    min_chars=7,
    max_chars=15,
    fallback=["繼續保持", "你做得很好", "語氣很溫和"],
    field_name="quick_feedback"
)
```

**Behavior:**
- Returns original text if valid
- Returns fallback if text is too short or None
- Returns original text (with warning) if too long

## Migration Guide

### Before (Scattered Validation)

```python
# emotion_service.py
if len(hint) > 17:
    logger.warning(f"Hint too long ({len(hint)} chars), truncating: {hint}")
    hint = hint[:17]  # ❌ Hard truncation mid-sentence

# quick_feedback_service.py
if len(message) < min_chars:
    logger.warning(f"Response too short ({len(message)} chars): '{message}', using fallback")
    import random
    message = random.choice(FALLBACK_MESSAGES)

if len(message) > self.MAX_CHARS:
    logger.warning(f"Message over {self.MAX_CHARS} chars: {len(message)} chars")

# keyword_analysis_service.py
if len(display_text) < min_display_chars:
    logger.warning(f"display_text too short ({len(display_text)} chars): '{display_text}', using fallback")
    result["display_text"] = "分析完成"
elif len(display_text) > max_display_chars:
    logger.warning(f"display_text over {max_display_chars} chars: {len(display_text)} chars - '{display_text[:30]}...'")
```

### After (Centralized Validation)

```python
from app.services.utils.ai_validation import (
    apply_fallback_if_invalid,
    validate_ai_output_length,
    validate_finish_reason,
)

# emotion_service.py
hint = apply_fallback_if_invalid(
    text=hint,
    min_chars=5,
    max_chars=17,
    fallback="試著用平和語氣溝通",
    field_name="emotion_hint",
)

# quick_feedback_service.py
message = apply_fallback_if_invalid(
    text=message,
    min_chars=7,
    max_chars=15,
    fallback=FALLBACK_MESSAGES,  # List of fallbacks
    field_name="quick_feedback_message",
)

# keyword_analysis_service.py
validated = validate_ai_output_length(
    text=display_text,
    min_chars=4,
    max_chars=20,
    field_name="display_text",
)
if validated is None:
    result["display_text"] = "分析完成"
else:
    result["display_text"] = validated
```

## Best Practices

### 1. Always Set Adequate max_tokens

```python
# ❌ Bad: max_tokens too small
response = await gemini_service.generate_text(prompt, max_tokens=50)

# ✅ Good: Sufficient tokens to prevent truncation
response = await gemini_service.generate_text(prompt, max_tokens=500)
```

**Rule of thumb:** For Chinese text, use at least 500 max_tokens (each character is ~1-3 tokens).

### 2. Check finish_reason for Truncation

```python
# ✅ Good: Validate completion before using response
response = await gemini_service.generate_text(prompt, max_tokens=500)

if not validate_finish_reason(response, provider="gemini"):
    # Response was truncated - handle gracefully
    logger.warning("AI response truncated, using fallback")
    text = FALLBACK_VALUE
else:
    text = response.text
```

### 3. Never Hard Truncate Mid-Sentence

```python
# ❌ Bad: Hard truncation cuts sentences
text = ai_response[:15]

# ✅ Good: Log warning but keep original
validated = validate_ai_output_length(text, min_chars=5, max_chars=15, field_name="text")
# Returns original text with warning if too long
```

### 4. Use Prompt Engineering for Length Control

```python
# ✅ Better: Let AI respect length constraints
prompt = """
請用 15 字以內回應...

【回饋規則】
1. ⚠️ 必須 7-15 字（硬性限制！）
2. 正向鼓勵為主
"""

response = await gemini_service.generate_text(prompt, max_tokens=500)
text = apply_fallback_if_invalid(text=response.text, min_chars=7, max_chars=15, fallback="繼續保持")
```

## Field Validation Reference

Current AI fields in the project and their validation requirements:

| Service | Field | Min Chars | Max Chars | Fallback | Source |
|---------|-------|-----------|-----------|----------|--------|
| Quick Feedback | message | 7 | 15 | FALLBACK_MESSAGES | Prompt requirement |
| Emotion Analysis | hint | 5 | 17 | "試著用平和語氣溝通" | Prompt requirement |
| Deep Analyze | display_text | 4 | 20 | "分析完成" | Prompt requirement |
| Deep Analyze | quick_suggestion | 5 | 20 | "" (clear) | Expert suggestions: 5-17 chars |
| Report | encouragement | 4 | 15 | "你正在進步中" | Prompt requirement |

## Testing

Unit tests are located at: `tests/unit/test_ai_validation.py`

Run tests:
```bash
poetry run pytest tests/unit/test_ai_validation.py -v
```

## Related Documentation

- **Skill Guide**: `.claude/skills/ai-output-validation/SKILL.md`
- **Lessons Learned**: 2026-01-08 truncation bugs (Quick Feedback, Report, Deep Analyze)

## Version History

- **v1.0** (2026-01-26): Initial implementation
  - Extracted validation logic from multiple services
  - Added comprehensive unit tests
  - Refactored 4 services to use centralized helpers
