# Safety Level Transitions - Expected Test Results

## Overview

This document provides a comprehensive reference table of expected results for safety level transition tests.

---

## Test Scenarios Summary

### Scenario 1: RED → GREEN Transition

| Stage | Initial Content | Added Content | Expected Result |
|-------|-----------------|---------------|-----------------|
| **Initial** | "案主：我真的快要氣死了，我想打死他！這孩子就是不聽話！" | - | 🔴 RED |
| **Final** | (Initial content) | "諮詢師：我聽到你的痛苦了，讓我們一起深呼吸...\n案主：謝謝你陪我冷靜下來。我知道不該這樣對孩子。\n案主：我願意試試看。我希望和孩子的關係可以更好。" | 🟢 GREEN |

**Expected Changes**:
- Safety Level: `red` → `green`
- Circle Color: Red gradient → Green gradient
- Text Color: `text-red-900` → `text-green-900`
- Safety Indicator: 🔴 → 🟢
- Analysis Interval: 15s → 60s
- Suggestions: Urgent/directive → Reflective/educational

---

### Scenario 2: GREEN → RED Transition

| Stage | Initial Content | Added Content | Expected Result |
|-------|-----------------|---------------|-----------------|
| **Initial** | "諮詢師：你好，今天想聊什麼呢？\n案主：最近孩子在學校交了新朋友，我很開心。\n案主：是的，他變得更開朗了。" | - | 🟢 GREEN |
| **Final** | (Initial content) | "案主：但是...昨天他又不聽話了！\n案主：他一直玩手機不寫功課，我氣到想打死他！\n案主：我真的受不了了，有時候我想乾脆去死算了。" | 🔴 RED |

**Expected Changes**:
- Safety Level: `green` → `red`
- Circle Color: Green gradient → Red gradient
- Text Color: `text-green-900` → `text-red-900`
- Safety Indicator: 🟢 → 🔴
- Analysis Interval: 60s → 15s
- Suggestions: Reflective → Urgent/crisis intervention

---

### Scenario 3: RED → YELLOW → GREEN Gradual Transition

| Stage | Content Summary | Keywords Detected | Expected Result |
|-------|-----------------|-------------------|-----------------|
| **Phase 1** | "我快要受不了了！我想揍他一頓！這孩子就是故意氣死我的！" | 受不了, 揍, 氣死 | 🔴 RED |
| **Phase 2** | (Phase 1) + "我真的很煩...我快被他氣死了，但我知道不能打他。" | 煩, 氣死 (but no violence) | 🟡 YELLOW |
| **Phase 3** | (Phase 2) + "我冷靜多了...我願意試試看。我相信我可以做得更好。" | 冷靜, 願意, 試試看 | 🟢 GREEN |

**Expected Changes**:

| Transition | Safety Level | Circle Color | Text Color | Interval |
|------------|--------------|--------------|------------|----------|
| Phase 1 → Phase 2 | red → yellow | Red → Yellow | text-red-900 → text-yellow-900 | 15s → 30s |
| Phase 2 → Phase 3 | yellow → green | Yellow → Green | text-yellow-900 → text-green-900 | 30s → 60s |

---

### Scenario 4: GREEN → YELLOW → RED Escalation

| Stage | Content Summary | Keywords Detected | Expected Result |
|-------|-----------------|-------------------|-----------------|
| **Phase 1** | "今天感覺如何？\n還不錯，孩子最近表現很好。" | - (positive) | 🟢 GREEN |
| **Phase 2** | (Phase 1) + "他說謊，我真的很煩，快被他氣死了。" | 說謊, 煩, 氣死 | 🟡 YELLOW |
| **Phase 3** | (Phase 2) + "我想打死他！我恨死他了！我覺得活著沒意義..." | 打死, 恨死, 沒意義 | 🔴 RED |

**Expected Changes**:

| Transition | Safety Level | Circle Color | Text Color | Interval |
|------------|--------------|--------------|------------|----------|
| Phase 1 → Phase 2 | green → yellow | Green → Yellow | text-green-900 → text-yellow-900 | 60s → 30s |
| Phase 2 → Phase 3 | yellow → red | Yellow → Red | text-yellow-900 → text-red-900 | 30s → 15s |

---

## Detailed Expected Results by Safety Level

### 🔴 RED (High Risk)

**Triggers**:
- Violent language: 打死, 殺, 揍, 打人, 暴力
- Extreme emotions: 恨死, 受不了, 滾
- Crisis indicators: 不想活, 去死

**Visual Indicators**:
- Circle Color: `bg-gradient-to-br from-red-400 via-red-500 to-red-600`
- Text Color: `text-red-900`
- Safety Indicator: 🔴
- Border: `ring-red-500`

**Behavior**:
- Analysis Interval: 15 seconds (urgent monitoring)
- Suggestions: Urgent, directive, crisis intervention
- Alerts: High priority warnings

**Example Suggestions (RED)**:
```
💡 立即穩定情緒：引導深呼吸，暫停對話
💡 評估安全風險：詢問是否需要緊急協助
⚠️ 考慮轉介專業資源（危機處理）
```

---

### 🟡 YELLOW (Medium Risk)

**Triggers**:
- Frustration: 氣死, 煩死, 受夠
- Escalating conflict: 不聽話, 說謊
- Stress indicators: 快瘋, 崩潰, 發火

**Visual Indicators**:
- Circle Color: `bg-gradient-to-br from-yellow-400 via-yellow-500 to-yellow-600`
- Text Color: `text-yellow-900`
- Safety Indicator: 🟡
- Border: `ring-yellow-500`

**Behavior**:
- Analysis Interval: 30 seconds (cautious monitoring)
- Suggestions: Preventive, de-escalation focused
- Alerts: Moderate warnings

**Example Suggestions (YELLOW)**:
```
💡 注意情緒升溫：建議暫停，休息一下
💡 引導表達感受：同理家長的挫折感
💡 提供具體策略：正向教養技巧
```

---

### 🟢 GREEN (Safe)

**Triggers**:
- Positive emotions: 開心, 感謝, 很好
- Willingness to learn: 願意, 試試看, 學習
- Calm state: 冷靜, 理解, 放鬆

**Visual Indicators**:
- Circle Color: `bg-gradient-to-br from-green-400 via-green-500 to-green-600`
- Text Color: `text-green-900`
- Safety Indicator: 🟢
- Border: `ring-green-500`

**Behavior**:
- Analysis Interval: 60 seconds (routine monitoring)
- Suggestions: Reflective, educational, growth-oriented
- Alerts: Positive feedback, encouragement

**Example Suggestions (GREEN)**:
```
💡 持續正向互動：鼓勵家長繼續保持
💡 深化親子關係：探討長期成長策略
💡 反思與學習：分享成功經驗，建立信心
```

---

## API Response Structure

### Expected JSON Response

```json
{
  "safety_level": "red" | "yellow" | "green",
  "summary": "案主處境簡述（1-3 句）",
  "alerts": [
    "💡 同理案主感受",
    "⚠️ 需關注的部分",
    "✅ 正向的部分"
  ],
  "suggestions": [
    "💡 核心建議（簡短）",
    "💡 具體做法（可行）",
    "💡 反思提示（深化）"
  ],
  "time_range": "0:00-1:00",
  "timestamp": "2025-12-26T10:30:00Z",
  "rag_sources": [
    {
      "title": "正向教養手冊",
      "content": "...",
      "score": 0.75,
      "theory": "正向教養"
    }
  ],
  "cache_metadata": {
    "cache_name": "...",
    "cache_created": false,
    "cached_tokens": 1024,
    "prompt_tokens": 256
  },
  "provider_metadata": {
    "provider": "gemini",
    "latency_ms": 1234,
    "model": "gemini-2.5-flash"
  }
}
```

---

## Keyword Detection Reference

### RED Keywords (High Priority)

| Category | Keywords | Detection Pattern |
|----------|----------|-------------------|
| Violence | 打死, 殺, 揍, 打人, 暴力 | Any occurrence triggers RED |
| Extreme Emotions | 恨死, 受不了, 滾 | Combined with other indicators |
| Crisis | 不想活, 去死 | Immediate RED flag |

### YELLOW Keywords (Medium Priority)

| Category | Keywords | Detection Pattern |
|----------|----------|-------------------|
| Frustration | 氣死, 煩死, 受夠 | Indicates rising tension |
| Conflict | 不聽話, 說謊, 頂嘴 | Behavioral issues |
| Stress | 快瘋, 崩潰, 發火 | Emotional distress |

### GREEN Indicators (Positive)

| Category | Keywords | Detection Pattern |
|----------|----------|-------------------|
| Positive Emotions | 開心, 感謝, 很好, 棒 | Calm, safe interaction |
| Willingness | 願意, 試試看, 學習 | Growth mindset |
| Calm State | 冷靜, 理解, 放鬆, 穩定 | Emotional regulation |

---

## Validation Checklist

### For Each Test Scenario

- [ ] **API Response**
  - [ ] `safety_level` field present
  - [ ] Correct value (`red`, `yellow`, or `green`)
  - [ ] `summary`, `alerts`, `suggestions` populated

- [ ] **Visual Indicators**
  - [ ] Circle color gradient matches safety level
  - [ ] Text color class applied correctly
  - [ ] Safety emoji (🔴/🟡/🟢) displayed
  - [ ] Border ring color matches

- [ ] **Behavior**
  - [ ] Analysis interval updated (15s/30s/60s)
  - [ ] Auto-analysis triggered at correct interval
  - [ ] Suggestions match urgency level

- [ ] **Console Logs**
  - [ ] `Safety level: [red/yellow/green]` logged
  - [ ] `Analysis interval: [15000/30000/60000]ms` logged
  - [ ] No JavaScript errors
  - [ ] API requests successful (200 OK)

- [ ] **Edge Cases**
  - [ ] Empty transcript handled gracefully
  - [ ] Very long cumulative transcript works
  - [ ] Rapid transitions handled correctly
  - [ ] Network errors handled with fallback

---

## Performance Expectations

### API Latency

| Provider | Expected Latency | Acceptable Range |
|----------|------------------|------------------|
| Gemini Flash | 1-2 seconds | < 5 seconds |
| Codeer | 2-4 seconds | < 10 seconds |

### Frontend Rendering

| Action | Expected Time | Acceptable Range |
|--------|---------------|------------------|
| Circle color change | < 100ms | < 500ms |
| Text color update | < 50ms | < 200ms |
| Suggestions render | < 200ms | < 1 second |

### Browser Compatibility

| Browser | Expected Support | Notes |
|---------|------------------|-------|
| Chrome 90+ | ✅ Full support | Recommended |
| Firefox 88+ | ✅ Full support | Recommended |
| Safari 14+ | ✅ Full support | Tested on macOS/iOS |
| Edge 90+ | ✅ Full support | Chromium-based |

---

## Test Data Examples

### RED Test Data

```
案主：我真的快要氣死了！我想打死他！
案主：這孩子就是不聽話！我恨死他了！
案主：我受不了了！我要去死算了！
```

**Expected**: 🔴 RED, 15s interval, urgent suggestions

---

### YELLOW Test Data

```
案主：他說謊，我真的很煩。
案主：快被他氣死了，我快要崩潰了。
案主：他都不聽話，我快要發火了。
```

**Expected**: 🟡 YELLOW, 30s interval, preventive suggestions

---

### GREEN Test Data

```
案主：謝謝你的建議，我冷靜多了。
案主：我願意試試看，我相信可以做得更好。
案主：和孩子的關係真的改善了，我很開心。
```

**Expected**: 🟢 GREEN, 60s interval, reflective suggestions

---

## Troubleshooting Guide

### Issue: Safety level always GREEN

**Possible Causes**:
- RED/YELLOW keywords not detected
- Transcript not cumulative
- API keyword detection logic issue

**Fix**:
1. Verify keywords in `_assess_safety_level()` function
2. Check transcript content in API request
3. Test with explicit RED keywords

---

### Issue: Circle color not changing

**Possible Causes**:
- CSS classes not applied
- JavaScript error preventing update
- API response missing `safety_level`

**Fix**:
1. Inspect element to check CSS classes
2. Check browser console for errors
3. Verify API response in Network tab

---

### Issue: Interval not updating

**Possible Causes**:
- `setInterval` not cleared
- JavaScript logic error
- Analysis not triggered

**Fix**:
1. Check console logs for interval changes
2. Manually trigger analysis
3. Reload page and retry

---

**Last Updated**: 2025-12-26
**Version**: 1.0
