# Annotated Safety Window Implementation

## Overview

Implemented improved safety assessment approach that sends full transcript to AI for context awareness while annotating the last 5-10 speaker turns for focused safety assessment.

## Implementation Date
2025-12-26

## Problem Statement

**Previous Approach Issues:**
1. Full transcript sent to AI → AI might assess based on old dangerous content
2. Safety level stayed RED even after conversation improved
3. No clear distinction between historical context and current state

**New Approach:**
1. Send full transcript for context (complete conversation history)
2. Annotate last 5 speaker turns with visual markers
3. Instruct AI to assess safety ONLY based on annotated section
4. Backend sliding window (10 turns) serves as fallback validation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Full Conversation Transcript (sent to AI)                   │
│ ─────────────────────────────────────────────────────────── │
│ counselor: 你好，今天想聊什麼？                                 │
│ client: 我真的很想打死我兒子！ ← OLD DANGER (turn 2)         │
│ counselor: 我聽到你的憤怒了...                                │
│ client: 對不起，我不應該這樣說                                 │
│ ─────────────────────────────────────────────────────────── │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━         │
│ 【最近對話 - 用於安全評估】                                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━         │
│ counselor: 很好，我們繼續                                     │
│ client: 我知道要怎麼做了                                      │
│ counselor: 你很棒                                            │
│ client: 我會試試看的                                         │
│ counselor: 加油                                              │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━         │
└─────────────────────────────────────────────────────────────┘
           ↓
    AI Assessment:
    - Safety: GREEN (based on annotated section)
    - Suggestions: Use full context for depth
```

## Code Changes

### 1. Configuration Constants
**File**: `/Users/young/project/career_ios_backend/app/api/realtime.py`

```python
# Annotated window configuration for AI safety assessment
ANNOTATED_SAFETY_WINDOW_TURNS = 5  # Last 5-10 turns highlighted for AI safety evaluation
```

### 2. System Instruction Update
Added safety assessment rules to system instruction:

```python
【安全等級評估規則】CRITICAL - 必須嚴格遵守：
⚠️ **僅根據「【最近對話 - 用於安全評估】」區塊判斷安全等級**
   - 標註區塊顯示最近 5-10 個對話輪次
   - 不要因為完整逐字稿中出現過的危險詞就評估為高風險
   - 如果最近對話已經緩和、正向，即使之前有危險內容，也應評估為較低風險
   - 安全等級反映當前狀態，不是歷史狀態
```

### 3. Helper Function: `_build_annotated_transcript()`
Creates annotated transcript with visual markers:

```python
def _build_annotated_transcript(transcript: str, speakers: List[dict]) -> str:
    """Build annotated transcript with recent window highlighted for safety assessment."""

    # Build full transcript
    full_transcript = "\n".join([
        f"{seg.get('speaker', 'unknown')}: {seg.get('text', '')}"
        for seg in speakers
    ])

    # Extract recent window for annotation (last 5 turns)
    recent_speakers = (
        speakers[-ANNOTATED_SAFETY_WINDOW_TURNS:]
        if len(speakers) > ANNOTATED_SAFETY_WINDOW_TURNS
        else speakers
    )
    recent_transcript = "\n".join([
        f"{seg.get('speaker', 'unknown')}: {seg.get('text', '')}"
        for seg in recent_speakers
    ])

    # Construct annotated prompt with visual markers
    return f"""完整對話逐字稿（供參考，理解背景脈絡）：
{full_transcript}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近對話 - 用於安全評估】
（請根據此區塊判斷當前安全等級）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{recent_transcript}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ CRITICAL: 安全等級評估請只根據「【最近對話 - 用於安全評估】」區塊判斷，
完整對話僅作為理解脈絡參考。如果最近對話已緩和，即使之前有危險內容，
也應評估為較低風險。"""
```

### 4. Prompt Builder Updates
Updated `_build_practice_prompt()` to accept annotated transcript:

```python
def _build_practice_prompt(transcript: str, rag_context: str, annotated_transcript: str = "") -> str:
    # Use annotated transcript if provided, otherwise fall back to plain transcript
    dialogue_content = annotated_transcript if annotated_transcript else transcript

    prompt = f"""你是專業諮詢督導...

【對話內容】
{dialogue_content}
"""
```

### 5. Analysis Endpoint Integration
Updated `/analyze` endpoint to use annotated transcripts:

```python
# Build annotated transcript for safety assessment
annotated_transcript = _build_annotated_transcript(request.transcript, speakers_dict)
logger.info(f"Built annotated transcript with {len(speakers_dict)} total speakers, "
           f"last {min(ANNOTATED_SAFETY_WINDOW_TURNS, len(speakers_dict))} highlighted")

# Select prompt based on counseling mode
if request.mode == CounselingMode.emergency:
    custom_prompt = _build_emergency_prompt(annotated_transcript, rag_context)
else:
    custom_prompt = _build_practice_prompt(request.transcript, rag_context, annotated_transcript)
```

## Test Suite

Created comprehensive test suite: `/Users/young/project/career_ios_backend/tests/integration/test_annotated_safety_window.py`

### Test Categories

1. **Experiment 1: RED → GREEN Relaxation** (2 tests)
   - Verify AI assesses recent calm conversation as GREEN
   - Test with long conversation history

2. **Experiment 2: GREEN → RED Escalation** (2 tests)
   - Verify AI detects new danger in recent conversation
   - Test sudden escalation at boundary

3. **Experiment 3: Compare Approaches** (2 tests)
   - Accuracy with old danger present
   - Context awareness in suggestions

4. **Experiment 4: Boundary Cases** (3 tests)
   - Danger at exact window boundary
   - Danger just outside window
   - Very short conversations

5. **Experiment 5: AI Compliance Check** (2 tests)
   - Verify AI uses annotated section for safety
   - Verify suggestions use full context

6. **Configuration Tests** (3 tests)
   - Verify constants
   - Test helper functions
   - Test annotation with short conversations

**Total: 14 comprehensive tests**

### Running Tests

```bash
# Run all annotated window tests
poetry run pytest tests/integration/test_annotated_safety_window.py -v

# Run specific experiment
poetry run pytest tests/integration/test_annotated_safety_window.py::TestExperiment1RedToGreenRelaxation -v

# Run configuration tests only
poetry run pytest tests/integration/test_annotated_safety_window.py::TestAnnotatedWindowConfiguration -v
```

## Key Test Results

### Test 1: RED → GREEN Relaxation ✅
```
Scenario:
- Turn 2: "我真的很想打死我兒子！" (RED keyword)
- Turns 3-12: Calm, de-escalating conversation
- Last 5 turns: Completely calm

Result: Safety Level = GREEN
Summary: "案主在諮詢初期表達了極大的憤怒與挫折感，但在諮詢師的同理與接納下，
         情緒迅速緩和，並展現出積極面對和尋求解決方案的意願。"
```

### Test 2: AI Compliance Check ✅
```
Scenario:
- Turns 1-3: Multiple RED keywords ("打死", "恨死", "受不了")
- Turns 8-13: Completely calm conversation
- Last 5 turns: No danger keywords

Result: Safety Level = GREEN
Confirms: AI correctly follows annotation instruction
```

## Backend Validation

The existing `_assess_safety_level()` function continues to run as a **backend validation layer**:
- Uses 10-turn sliding window
- Provides double-layer safety check
- Can log discrepancies between AI and backend assessments

## Benefits of This Approach

1. **Context Awareness**: AI has full conversation history for better suggestions
2. **Accurate Safety Assessment**: Focuses on recent conversation state
3. **Rapid Relaxation**: Safety level can de-escalate quickly when conversation improves
4. **Double Validation**: Backend + AI safety checks
5. **Flexible Windows**: 5 turns for AI annotation, 10 turns for backend validation

## Metrics to Track

1. **Accuracy**: Does AI assess recent state correctly?
   - ✅ Confirmed in tests: GREEN for calm recent conversation

2. **Context Awareness**: Do suggestions show full history understanding?
   - ✅ Confirmed: Suggestions reference full conversation journey

3. **Cost**: Token usage (cached tokens vs. prompt tokens)
   - To be monitored in production

4. **Speed**: Response latency (ms)
   - To be monitored in production

## Future Enhancements

1. **Experiment Logging**: Track AI vs. backend assessment discrepancies
2. **Dynamic Window Size**: Adjust window based on conversation dynamics
3. **Visual Feedback**: Show annotated section in console.html for transparency
4. **A/B Testing**: Compare old vs. new approach in production

## Related Files

- **Implementation**: `/Users/young/project/career_ios_backend/app/api/realtime.py`
- **Tests**: `/Users/young/project/career_ios_backend/tests/integration/test_annotated_safety_window.py`
- **Existing Tests**:
  - `/Users/young/project/career_ios_backend/tests/unit/test_safety_assessment_sliding_window.py`
  - `/Users/young/project/career_ios_backend/tests/integration/test_realtime_safety_transitions.py`

## Conclusion

The annotated safety window approach successfully addresses the core issue of delayed safety relaxation while maintaining context awareness for quality suggestions. Initial tests confirm AI compliance with annotation instructions and accurate safety assessment based on recent conversation state.

---
**Implementation Status**: ✅ Complete
**Test Coverage**: 14 comprehensive tests
**Production Ready**: Yes (with monitoring recommended)
