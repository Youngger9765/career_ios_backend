# AI Validation - Quick Reference Card

## Import

```python
from app.services.utils.ai_validation import (
    apply_fallback_if_invalid,
    validate_ai_output_length,
    validate_finish_reason,
)
```

## Common Patterns

### Pattern 1: Simple Validation with Fallback

**Use when**: AI generates a single field that needs min/max validation

```python
message = apply_fallback_if_invalid(
    text=ai_response,
    min_chars=7,
    max_chars=15,
    fallback="預設訊息",
    field_name="message"
)
```

### Pattern 2: Validation Only (No Fallback)

**Use when**: You want to apply your own fallback logic

```python
validated = validate_ai_output_length(
    text=ai_response,
    min_chars=5,
    max_chars=20,
    field_name="field_name"
)

if validated is None:
    # Custom fallback logic
    result["field"] = "自訂預設值"
else:
    result["field"] = validated
```

### Pattern 3: Check Finish Reason (Detect Truncation)

**Use when**: You need to know if AI was truncated

```python
response = await gemini_service.generate_text(prompt, max_tokens=500)

if not validate_finish_reason(response, provider="gemini"):
    logger.warning("AI response was truncated!")
    # Use fallback or retry with higher max_tokens

text = response.text
```

### Pattern 4: Full Validation Pipeline

**Use when**: You want to validate AND check truncation

```python
response = await gemini_service.generate_text(prompt, max_tokens=500)

# Check if AI completed normally
finish_ok = validate_finish_reason(response, provider="gemini")

if not finish_ok:
    # Truncated - use fallback immediately
    text = "預設訊息"
else:
    # Validate length
    text = apply_fallback_if_invalid(
        text=response.text,
        min_chars=7,
        max_chars=15,
        fallback="預設訊息",
        field_name="message"
    )
```

## Field-Specific Examples

### Quick Feedback (7-15 chars)

```python
message = apply_fallback_if_invalid(
    text=ai_response,
    min_chars=7,
    max_chars=15,
    fallback=["繼續保持", "你做得很好", "語氣很溫和"],  # Random choice
    field_name="quick_feedback"
)
```

### Emotion Hint (5-17 chars)

```python
hint = apply_fallback_if_invalid(
    text=ai_response,
    min_chars=5,
    max_chars=17,
    fallback="試著用平和語氣溝通",
    field_name="emotion_hint"
)
```

### Display Text (4-20 chars)

```python
validated = validate_ai_output_length(
    text=display_text,
    min_chars=4,
    max_chars=20,
    field_name="display_text"
)
result["display_text"] = validated if validated else "分析完成"
```

### Report Encouragement (4-15 chars)

```python
validated = validate_ai_output_length(
    text=encouragement,
    min_chars=4,
    max_chars=15,
    field_name="encouragement"
)
result["encouragement"] = validated if validated else "你正在進步中"
```

## Best Practices Checklist

- [ ] Set `max_tokens >= 500` for Chinese text
- [ ] Always validate AI output before using it
- [ ] Use `validate_finish_reason()` to detect truncation
- [ ] Never hard truncate with `[:n]` - use validation instead
- [ ] Define clear fallback values per field type
- [ ] Use descriptive `field_name` for better logs
- [ ] Test AI output multiple times (variability check)

## Common Mistakes

### ❌ Hard Truncation
```python
text = ai_response[:15]  # Cuts mid-sentence!
```

### ✅ Proper Validation
```python
text = apply_fallback_if_invalid(
    text=ai_response,
    min_chars=5,
    max_chars=15,
    fallback="預設值",
    field_name="text"
)
```

---

### ❌ Too Small max_tokens
```python
response = await llm.generate(max_tokens=50)  # Too small for Chinese!
```

### ✅ Adequate max_tokens
```python
response = await llm.generate(max_tokens=500)  # Sufficient
```

---

### ❌ No Validation
```python
return {"message": ai_response}  # What if it's empty or truncated?
```

### ✅ With Validation
```python
message = apply_fallback_if_invalid(
    text=ai_response,
    min_chars=7,
    max_chars=15,
    fallback="預設訊息",
    field_name="message"
)
return {"message": message}
```

## Testing Your Validation

```python
# Test with multiple responses to check variability
for i in range(5):
    response = await service.generate_feedback(...)
    assert len(response["message"]) >= 7
    assert len(response["message"]) <= 15
    print(f"Test {i+1}: {response['message']} ({len(response['message'])} chars)")
```

## Need Help?

- **README**: `app/services/utils/README.md` - Full documentation
- **Tests**: `tests/unit/test_ai_validation.py` - Usage examples
- **Skill Guide**: `.claude/skills/ai-output-validation/SKILL.md` - Patterns
