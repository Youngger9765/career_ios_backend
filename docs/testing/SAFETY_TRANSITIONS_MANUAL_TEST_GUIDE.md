# Safety Level Transitions - Manual Test Guide

## Overview

This guide provides step-by-step instructions for manually testing safety level transitions in the realtime counseling system.

**Goal**: Verify that the system correctly transitions safety levels (and visual indicators) when transcript content changes from dangerous to safe (or vice versa).

**Critical Constraint**: Transcripts are CUMULATIVE (appended, not replaced).

---

## Test Environment Setup

### Prerequisites

1. **Backend Running**: Start the backend server
   ```bash
   poetry run uvicorn app.main:app --reload --port 8000
   ```

2. **Browser**: Open Chrome/Firefox with Developer Console enabled (F12)

3. **Page**: Navigate to the realtime counseling page
   ```
   http://localhost:8000/realtime-counseling
   ```

4. **Demo Mode**: Enable "Demo Mode" checkbox on the page

---

## Test Scenarios

### Scenario 1: RED → GREEN Transition

**Objective**: Test transition from high-risk to safe conversation

#### Step-by-Step Instructions

1. **Initial State (RED)**
   - [ ] Click "快速測試 RED" button
   - [ ] Observe the visual indicators:
     - Circle color: Should be **RED**
     - Text color: Should be `text-red-900`
     - Safety indicator: 🔴
   - [ ] Open browser console, verify log:
     ```
     Safety level: red
     Analysis interval: 15000ms
     ```

2. **Add Safe Content**
   - [ ] In the transcript area, append the following (manually type or paste):
     ```
     諮詢師：我聽到你的痛苦了，讓我們一起深呼吸，慢慢來。
     案主：好的...（深呼吸）
     諮詢師：你願意和我分享發生了什麼事嗎？
     案主：謝謝你陪我冷靜下來。我知道不該這樣對孩子。
     諮詢師：你能覺察自己的情緒，這很棒。
     案主：我願意試試看。我希望和孩子的關係可以更好。
     ```

3. **Trigger Analysis**
   - [ ] Wait for auto-analysis (15 seconds) OR manually click "立即分析"
   - [ ] Observe the transition:
     - Circle color: RED → **GREEN**
     - Text color: `text-red-900` → `text-green-900`
     - Safety indicator: 🔴 → 🟢
   - [ ] Check console log:
     ```
     Safety level: green (changed from red)
     Analysis interval: 60000ms (changed from 15000ms)
     ```

4. **Verification Checklist**
   - [ ] Circle gradient changed to green
   - [ ] Text color changed to green
   - [ ] Safety level indicator shows 🟢
   - [ ] Analysis interval increased to 60s
   - [ ] Suggestions became less urgent, more reflective
   - [ ] No console errors

**Expected Result**: ✅ RED → GREEN transition successful

---

### Scenario 2: GREEN → RED Transition

**Objective**: Test transition from safe to high-risk conversation

#### Step-by-Step Instructions

1. **Initial State (GREEN)**
   - [ ] Click "快速測試 GREEN" button
   - [ ] Observe visual indicators:
     - Circle color: Should be **GREEN**
     - Text color: `text-green-900`
     - Safety indicator: 🟢
   - [ ] Verify console log:
     ```
     Safety level: green
     Analysis interval: 60000ms
     ```

2. **Add Dangerous Content**
   - [ ] In the transcript area, append:
     ```
     諮詢師：那很好，繼續保持。
     案主：但是...昨天他又不聽話了！
     諮詢師：發生什麼事了？
     案主：他一直玩手機不寫功課，我氣到想打死他！他就是故意激怒我！
     案主：我真的受不了了，有時候我想乾脆去死算了。
     ```

3. **Trigger Analysis**
   - [ ] Wait for auto-analysis (60 seconds) OR manually click "立即分析"
   - [ ] Observe the transition:
     - Circle color: GREEN → **RED**
     - Text color: `text-green-900` → `text-red-900`
     - Safety indicator: 🟢 → 🔴
   - [ ] Check console log:
     ```
     Safety level: red (changed from green)
     Analysis interval: 15000ms (changed from 60000ms)
     ```

4. **Verification Checklist**
   - [ ] Circle gradient changed to red
   - [ ] Text color changed to red
   - [ ] Safety level indicator shows 🔴
   - [ ] Analysis interval decreased to 15s
   - [ ] Suggestions became more urgent/directive
   - [ ] No console errors

**Expected Result**: ✅ GREEN → RED transition successful

---

### Scenario 3: RED → YELLOW → GREEN Gradual Transition

**Objective**: Test gradual de-escalation through all three levels

#### Step-by-Step Instructions

1. **Phase 1: RED**
   - [ ] Click "快速測試 RED" button
   - [ ] Verify: RED circle, 🔴, 15s interval
   - [ ] Console shows: `Safety level: red`

2. **Phase 2: Add YELLOW Content**
   - [ ] Append to transcript:
     ```
     諮詢師：我聽到你的憤怒，先深呼吸好嗎？
     案主：好...（呼吸）我真的很煩，他都不聽話。
     諮詢師：你感覺很受挫，對嗎？
     案主：對，我快被他氣死了，但我知道不能打他。
     ```
   - [ ] Click "立即分析"
   - [ ] Verify: YELLOW circle, 🟡, 30s interval
   - [ ] Console shows: `Safety level: yellow`

3. **Phase 3: Add GREEN Content**
   - [ ] Append to transcript:
     ```
     諮詢師：你能覺察自己的情緒，這很好。我們一起想想怎麼辦。
     案主：好的，謝謝你。我冷靜多了。
     諮詢師：你想要和孩子建立更好的關係嗎？
     案主：當然，我很愛他。我希望我們能好好溝通，不要總是吵架。
     諮詢師：那我們來討論一些具體的溝通方法。
     案主：好，我願意試試看。我相信我可以做得更好。
     ```
   - [ ] Click "立即分析"
   - [ ] Verify: GREEN circle, 🟢, 60s interval
   - [ ] Console shows: `Safety level: green`

4. **Verification Checklist**
   - [ ] All three levels detected correctly
   - [ ] Visual indicators changed smoothly
   - [ ] Intervals: 15s → 30s → 60s
   - [ ] Suggestions adapted to each level
   - [ ] No console errors

**Expected Result**: ✅ RED → YELLOW → GREEN gradual transition successful

---

### Scenario 4: GREEN → YELLOW → RED Escalation

**Objective**: Test gradual escalation through all three levels

#### Step-by-Step Instructions

1. **Phase 1: GREEN**
   - [ ] Click "快速測試 GREEN" button
   - [ ] Verify: GREEN circle, 🟢, 60s interval

2. **Phase 2: Add YELLOW Content**
   - [ ] Append to transcript:
     ```
     諮詢師：那很好，繼續保持。
     案主：不過...今天他又開始不聽話了。
     諮詢師：發生什麼事了？
     案主：他說謊，我真的很煩，快被他氣死了。
     ```
   - [ ] Click "立即分析"
   - [ ] Verify: YELLOW circle, 🟡, 30s interval

3. **Phase 3: Add RED Content**
   - [ ] Append to transcript:
     ```
     諮詢師：你感覺很生氣...
     案主：何止生氣！我真的受不了了！我想打死他！
     案主：我恨死他了！他就是故意要把我逼瘋！
     案主：我覺得活著沒意義，每天都是這樣的折磨。
     ```
   - [ ] Click "立即分析"
   - [ ] Verify: RED circle, 🔴, 15s interval

4. **Verification Checklist**
   - [ ] All three levels detected correctly
   - [ ] Visual indicators escalated properly
   - [ ] Intervals: 60s → 30s → 15s
   - [ ] Suggestions became more urgent
   - [ ] No console errors

**Expected Result**: ✅ GREEN → YELLOW → RED escalation detected successfully

---

## Visual Indicators Reference

### Circle Color Gradients

| Safety Level | Circle Color | CSS Gradient |
|--------------|--------------|--------------|
| 🔴 RED       | Red          | `from-red-400 via-red-500 to-red-600` |
| 🟡 YELLOW    | Yellow       | `from-yellow-400 via-yellow-500 to-yellow-600` |
| 🟢 GREEN     | Green        | `from-green-400 via-green-500 to-green-600` |

### Text Color

| Safety Level | Text Color | CSS Class |
|--------------|------------|-----------|
| 🔴 RED       | Dark Red   | `text-red-900` |
| 🟡 YELLOW    | Dark Yellow| `text-yellow-900` |
| 🟢 GREEN     | Dark Green | `text-green-900` |

### Analysis Intervals

| Safety Level | Interval | Description |
|--------------|----------|-------------|
| 🔴 RED       | 15s      | High frequency (urgent monitoring) |
| 🟡 YELLOW    | 30s      | Medium frequency (cautious monitoring) |
| 🟢 GREEN     | 60s      | Normal frequency (routine monitoring) |

---

## Console Log Monitoring

### Key Logs to Watch

1. **Safety Level Changes**
   ```
   Safety level: red
   Safety level: yellow
   Safety level: green
   ```

2. **Interval Updates**
   ```
   Analysis interval: 15000ms
   Analysis interval: 30000ms
   Analysis interval: 60000ms
   ```

3. **API Responses**
   ```
   Analysis result: {
     safety_level: "red",
     summary: "...",
     suggestions: [...]
   }
   ```

4. **Errors to Check**
   - No `Failed to analyze` errors
   - No `TypeError` or `null reference` errors
   - No network failures

---

## Troubleshooting

### Issue: Circle color not changing

**Possible Causes**:
- JavaScript error in console
- CSS classes not applied
- API not returning `safety_level`

**Fix**:
1. Check console for JavaScript errors
2. Inspect element to verify CSS classes
3. Verify API response includes `safety_level` field

### Issue: Interval not updating

**Possible Causes**:
- `setInterval` not cleared properly
- Analysis not triggered

**Fix**:
1. Check console for interval logs
2. Manually trigger analysis
3. Reload page and retry

### Issue: Safety level stuck on one color

**Possible Causes**:
- API not detecting keywords
- Transcript not cumulative

**Fix**:
1. Verify transcript content includes expected keywords
2. Check that new content is appended (not replaced)
3. Review API `/analyze` response in Network tab

---

## Expected Results Summary

| Scenario | Initial | Final | Expected Changes |
|----------|---------|-------|------------------|
| Scenario 1 | 🔴 RED | 🟢 GREEN | Circle: Red→Green, Interval: 15s→60s |
| Scenario 2 | 🟢 GREEN | 🔴 RED | Circle: Green→Red, Interval: 60s→15s |
| Scenario 3 | 🔴 RED | 🟢 GREEN (via YELLOW) | Circle: Red→Yellow→Green, Interval: 15s→30s→60s |
| Scenario 4 | 🟢 GREEN | 🔴 RED (via YELLOW) | Circle: Green→Yellow→Red, Interval: 60s→30s→15s |

---

## Test Data Reference

### RED Keywords (High Risk)
- 打死, 殺, 揍, 恨死, 暴力, 打人
- 受不了, 不想活, 去死, 滾

### YELLOW Keywords (Medium Risk)
- 氣死, 煩死, 受夠, 不聽話
- 說謊, 快瘋, 崩潰, 發火

### GREEN Indicators (Safe)
- 感謝, 願意, 試試看, 學習
- 開心, 很好, 冷靜, 理解

---

## Mobile Testing Notes

### Additional Checks for Mobile

1. **Responsive Design**
   - [ ] Circle size appropriate on mobile
   - [ ] Text readable on small screens
   - [ ] Safety indicator visible

2. **Touch Interactions**
   - [ ] "立即分析" button easily tappable
   - [ ] Demo mode buttons work on touch
   - [ ] Transcript area scrollable

3. **Performance**
   - [ ] Animations smooth on mobile
   - [ ] No lag during transitions
   - [ ] Battery usage reasonable

---

## Validation Checklist (Summary)

After completing all scenarios, verify:

- [ ] Safety level changes in API response
- [ ] Circle gradient changes visually (RED/YELLOW/GREEN)
- [ ] Text color changes (`text-red-900`/`text-yellow-900`/`text-green-900`)
- [ ] Interval updates correctly (15s/30s/60s)
- [ ] Console logs show transitions
- [ ] Works on desktop browser
- [ ] Works on mobile browser
- [ ] No JavaScript errors
- [ ] No network failures
- [ ] Suggestions adapt to safety level

---

## Report Template

After testing, document results:

```
## Safety Transitions Manual Test Report

**Date**: [YYYY-MM-DD]
**Tester**: [Name]
**Environment**: [Local/Staging/Production]

### Test Results

| Scenario | Status | Notes |
|----------|--------|-------|
| RED → GREEN | ✅/❌ | [Notes] |
| GREEN → RED | ✅/❌ | [Notes] |
| RED → YELLOW → GREEN | ✅/❌ | [Notes] |
| GREEN → YELLOW → RED | ✅/❌ | [Notes] |

### Issues Found

1. [Issue description]
2. [Issue description]

### Screenshots

- [Attach screenshots of transitions]

### Conclusion

[Overall assessment]
```

---

**Last Updated**: 2025-12-26
**Version**: 1.0
