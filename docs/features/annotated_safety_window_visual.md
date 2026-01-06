# Annotated Safety Window - Visual Guide

## Overview

The annotated safety window approach provides AI with explicit guidance on which part of the conversation to focus on for safety assessment while maintaining full context for understanding.

## Visual Representation

### Conversation Timeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                  FULL CONVERSATION TRANSCRIPT                        │
│                     (0-30 minutes, 50+ turns)                        │
└─────────────────────────────────────────────────────────────────────┘

Turn 1-10: Early conversation (may contain old dangerous keywords)
   ↓
Turn 11-20: Middle conversation
   ↓
Turn 21-30: More conversation
   ↓
┌──────────────────────────────────────────┐
│  ANNOTATED SAFETY WINDOW (Last 5-10 turns) │  ← AI focuses here for safety
│  Turn 41-50: Recent conversation           │
└──────────────────────────────────────────┘
```

## How It Works

### Step 1: Build Full Transcript
```
完整對話逐字稿（供參考，理解背景脈絡）：
┌────────────────────────────────────────────────────┐
│ Turn 1: 諮詢師：你好，今天想聊什麼？                │
│ Turn 2: 案主：我真的很想打死我兒子！[RED]         │
│ Turn 3: 諮詢師：我聽到你的憤怒了...               │
│ Turn 4: 案主：對不起，我不應該這樣說               │
│ Turn 5: 諮詢師：沒關係，我們一起處理               │
│ Turn 6: 案主：謝謝你，我冷靜多了                   │
│ Turn 7: 諮詢師：很好，我們繼續                     │
│ Turn 8: 案主：我知道要怎麼做了                     │
│ Turn 9: 諮詢師：你很棒                             │
│ Turn 10: 案主：我會試試看的                        │
│ Turn 11: 諮詢師：加油                              │
│ Turn 12: 案主：謝謝你的鼓勵                        │
└────────────────────────────────────────────────────┘
       ↑
   Historical context available for understanding
```

### Step 2: Highlight Recent Window
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【最近對話 - 用於安全評估】
（請根據此區塊判斷當前安全等級）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌────────────────────────────────────────────────────┐
│ Turn 8: 案主：我知道要怎麼做了                     │  ← Last 5 turns
│ Turn 9: 諮詢師：你很棒                             │
│ Turn 10: 案主：我會試試看的                        │
│ Turn 11: 諮詢師：加油                              │
│ Turn 12: 案主：謝謝你的鼓勵                        │  ← Most recent
└────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       ↑
   Focus area for safety assessment
```

### Step 3: Critical Instruction
```
⚠️ CRITICAL: 安全等級評估請只根據「【最近對話 - 用於安全評估】」區塊判斷，
完整對話僅作為理解脈絡參考。如果最近對話已緩和，即使之前有危險內容，
也應評估為較低風險。
```

## Safety Assessment Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Incoming Conversation                         │
│                  (transcript + speakers array)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
        ┌───────▼──────┐         ┌───────▼──────┐
        │   Backend    │         │     AI       │
        │ Assessment   │         │ Assessment   │
        │ (10 turns)   │         │ (5 turns)    │
        └───────┬──────┘         └───────┬──────┘
                │                        │
                │  Safety Level          │  Safety Level
                │  (red/yellow/green)    │  (red/yellow/green)
                │                        │
                └────────────┬───────────┘
                             │
                    ┌────────▼────────┐
                    │   Take more     │
                    │  conservative   │
                    │   of the two    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Final Safety   │
                    │     Level       │
                    └─────────────────┘
```

## Example Scenarios

### Scenario 1: RED → GREEN Relaxation

**Turn 2:** "我想打死他" (RED keyword)
**Turns 8-12:** Calm, supportive conversation

```
Old Approach:
┌──────────────────────────────┐
│ Full transcript (all 12 turns)│ → RED (stuck on Turn 2)
└──────────────────────────────┘

New Approach:
┌──────────────────────────────┐
│ Full context: Turns 1-12      │ → Understanding
└──────────────────────────────┘
┌──────────────────────────────┐
│ Safety focus: Turns 8-12      │ → GREEN (recent calm)
└──────────────────────────────┘
```

**Result:** GREEN (situation has calmed down)

### Scenario 2: GREEN → RED Escalation

**Turns 1-10:** Normal conversation
**Turn 11:** "我真的受不了了！"
**Turn 12:** "我想打他！" (RED keyword)

```
Old Approach:
┌──────────────────────────────┐
│ Full transcript (all 12 turns)│ → May dilute recent danger
└──────────────────────────────┘

New Approach:
┌──────────────────────────────┐
│ Full context: Turns 1-12      │ → Understanding
└──────────────────────────────┘
┌──────────────────────────────┐
│ Safety focus: Turns 8-12      │ → RED (recent escalation)
└──────────────────────────────┘
```

**Result:** RED (new danger detected)

## Configuration Parameters

```python
# How many recent speaker turns to evaluate (backend)
SAFETY_WINDOW_SPEAKER_TURNS = 10

# How many recent turns to highlight for AI (annotation)
ANNOTATED_SAFETY_WINDOW_TURNS = 5

# Approximate time coverage
# 5-10 turns ≈ 1-2 minutes of conversation
```

## Benefits Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    Annotated Window Benefits                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. ✅ Faster relaxation when danger passes                 │
│     Old: 10+ turns to relax                                 │
│     New: 5-10 turns to relax                                │
│                                                              │
│  2. ✅ Better escalation detection                          │
│     AI focuses on recent changes                            │
│                                                              │
│  3. ✅ Context-aware suggestions                            │
│     Uses full history for understanding                     │
│     Focuses on recent state for assessment                  │
│                                                              │
│  4. ✅ Explicit AI guidance                                 │
│     Clear instructions on what to focus on                  │
│                                                              │
│  5. ✅ Safety preserved                                     │
│     Backend validation provides fallback                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Testing Coverage

```
Test Categories:
┌────────────────────────────────┐
│ 1. RED → GREEN Relaxation      │ ✅ 2 tests
├────────────────────────────────┤
│ 2. GREEN → RED Escalation      │ ✅ 2 tests
├────────────────────────────────┤
│ 3. Compare Approaches          │ ✅ 2 tests
├────────────────────────────────┤
│ 4. Boundary Cases              │ ✅ 3 tests
├────────────────────────────────┤
│ 5. AI Compliance Check         │ ✅ 2 tests
├────────────────────────────────┤
│ 6. Configuration Tests         │ ✅ 3 tests
├────────────────────────────────┤
│ 7. Report Summary              │ ✅ 1 test
└────────────────────────────────┘
Total: 15 tests, 100% passing
```

## Production Readiness Checklist

- [x] Implementation complete
- [x] Unit tests passing (15/15)
- [x] Integration tests passing
- [x] AI instruction compliance validated
- [x] Safety assessment accuracy confirmed
- [x] Suggestion quality verified
- [x] Backend validation working
- [ ] Load testing (pending)
- [ ] Production monitoring (pending)
- [ ] User documentation (pending)

## References

- Test results: `/docs/annotated_safety_window_test_results.md`
- Approach comparison: `/docs/annotated_safety_window_comparison.md`
- Implementation: `/app/api/realtime.py` (lines 406-448, 809-819)
- Tests: `/tests/integration/test_annotated_safety_window.py`

---

**Last Updated:** 2024-12-26
**Status:** Production Ready ✅
