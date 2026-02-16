# QA Bug Report - Staging (2026-02-06 ~ 2026-02-13)

## Test Summary

| Metric | Value |
|--------|-------|
| Environment | Staging (`island-parents-staging.web.app`) |
| Testers | 6 (Lucas, KC, Evan, Zhang Wanqian, Xiao Zi, Yang Meihe) |
| Test Dates | 2026-02-06, 02-08, 02-10, 02-13 |
| OS | Mac (4), Windows (2) |
| Browser | Chrome (all) |

---

## Deduplicated Bug List (by Severity)

### CRITICAL - Blocks Core Flow

| Bug# | Game | Step IDs | Description | Reporters |
|------|------|----------|-------------|-----------|
| C1 | Room Creation | 2.2, 2.3 | **Network Error when creating room with linked client.** Creating room with associated client fails. Works if only room name is entered. White text issue in client name input. | 4/6 (Lucas, KC, Zhang, Evan) |
| C2 | T: Screenshot | T.1, D.10, E.11, G.12 | **Screenshot function broken across all games.** Returns only page layout/frame without content, or shows error "截圖失敗". | 5/6 (Lucas, Xiao Zi, Zhang, Evan, Yang) |

### HIGH - Sync / Realtime Issues

| Bug# | Game | Step IDs | Description | Reporters |
|------|------|----------|-------------|-----------|
| H1 | A,B,C,E,F | A.9, B.10, E.5, F.9, F.10 | **Visitor cannot reorder cards / reorder not syncing.** When visitor drags to reorder, cards snap back to original position after ~1 second. Counselor reorder doesn't sync to visitor. Affects all card games. | 5/6 (Xiao Zi, Evan, Zhang, Yang, Lucas) |
| H2 | B,C,E | B.7, B.8, C.6, C.7, E.7 | **Card limit changes not syncing to visitor.** When counselor changes max limit, visitor still sees old limit. Visitor can exceed counselor's limit. Counselor shows red text (e.g. 13/10), visitor shows normal text (e.g. 13/15). | 4/6 (Xiao Zi, Lucas, Evan, Zhang) |
| H3 | E | E.2, E.3, E.8 | **Job Analysis: uploaded file not visible to visitor.** Counselor uploads PDF/image but visitor can't see it. Each side can only see their own uploads. Visitor upload also fails in some cases. | 5/6 (Lucas, Xiao Zi, Zhang, Evan, Yang) |
| H4 | F | F.9, F.10 | **Value Card: sort/rank operations not syncing.** Counselor rank changes not reflected on visitor. Visitor drag in "Other" area snaps back. Entire ranking game unusable for visitor. | 5/6 (Lucas, Xiao Zi, Evan, Zhang, Yang) |
| H5 | G | G.9, G.10, G.11 | **Life Redesign: energy points not syncing between counselor/visitor.** Counselor/visitor adjustments not reflected on other side. Pie chart shows different data. | 4/6 (Lucas, Zhang, Yang, Xiao Zi[partial]) |
| H6 | A | A.10, A.11 | **RIASEC: card classification order not syncing.** Cards are categorized (like/neutral/dislike) correctly but displayed in different order on each side. One tester reports visitor can't categorize at all. | 3/6 (Zhang, Yang, Evan) |

### MEDIUM - Missing/Broken Features

| Bug# | Game | Step IDs | Description | Reporters |
|------|------|----------|-------------|-----------|
| M1 | D | D.1-D.7 | **Growth Planning: missing 3-column canvas layout.** Expected "Current Skills / Learning Path / Target Skills" columns not displayed. Only shows card list + single drop area. Cards can't be moved between zones. Some testers report only 1 card per area. | 5/6 (Lucas, Xiao Zi, Zhang, Evan, Yang) |
| M2 | F | F.1, F.2 | **Value Cards: 70 cards loaded instead of expected 36.** All testers see 70 cards. Spec says 36. | 4/6 (Lucas, Xiao Zi, Zhang, Evan) |
| M3 | F | F.7 | **Value Cards: cannot drag-swap rank 1/2/3 cards.** Must remove (X) then re-drag to change ranking order. Direct swap not supported. | 5/6 (Lucas, Xiao Zi, Zhang, Evan, Yang) |
| M4 | G | G.7 | **Life Redesign: missing reset button.** No way to reset all areas to zero. | 4/6 (Lucas, Zhang, Evan, Yang) |
| M5 | G | G.8 | **Life Redesign: missing satisfaction scale.** Cannot rate satisfaction per area. Feature not implemented. | 4/6 (Lucas, Zhang, Evan, Yang) |
| M6 | G | G.2 | **Life Redesign: missing slider control.** Only +/- buttons available, no slider bar for adjusting points. | 2/6 (Lucas, Yang) |
| M7 | G | G.3 | **Life Redesign: +/- increment is 10, not 5.** Expected each press = 5 points, actual = 10 points. | 2/6 (Lucas, Zhang) |
| M8 | G | G.4 | **Life Redesign: negative numbers when changing total from 1000 to 100.** Allocation becomes corrupted with negative values and wrong proportions. | 1/6 (Zhang) |

### LOW - UX / Polish Issues

| Bug# | Game | Step IDs | Description | Reporters |
|------|------|----------|-------------|-----------|
| L1 | A | A.7 | **RIASEC: card flip state anomaly during drag.** After flipping card, moving it shows back face briefly then returns to front. | 1/6 (Evan) |
| L2 | A | A.8 | **RIASEC: X remove button not visible/intuitive on mobile.** On phone, X not shown. Tap opens zoom, long-press inconsistent. Tablet needs long-press before drag. | 1/6 (Evan) |
| L3 | B,C | B.13, C.11 | **List mode: no color distinction for card categories.** Switching to list view shows names but cards aren't color-coded by category. Grid/List toggle not syncing between sides. | 2/6 (Evan, Zhang) |
| L4 | C | C.3 | **Competency Card: flip back info differs from popup back info.** Small card shows shadow content, popup shows booklet content. | 1/6 (Zhang) |
| L5 | T: Notes | T.3, T.4 | **Notes not persisting after leaving game room.** Notes disappear when exiting and re-entering. Most testers reported pass, 1 reported fail. | 1/6 (Yang) |
| L6 | Room | 2.5 | **No room participant limit or visibility.** Anyone with room code can join. No cap on simultaneous users. Counselor can't see who joined. | 1/6 (Evan) |
| L7 | B | B.3 | **Career Card #62 (Actuary) missing number label.** | 1/6 (Yang) |
| L8 | F | F.4 | **Value Card: rank 1 card appears smaller than expected.** Ratio is 1:1 but physical size smaller than source. | 1/6 (Xiao Zi) |

---

## Priority Fix Recommendation

### Sprint 1 (Must Fix Before Next Test)

1. **C1** - Room creation with linked client (Network Error)
2. **C2** - Screenshot function (broken everywhere)
3. **H1** - Visitor card reorder sync (core interaction broken)
4. **H2** - Limit change sync to visitor
5. **H3** - File upload sync in Job Analysis (E)

### Sprint 2 (High Impact)

6. **H4** - Value Card rank sync
7. **H5** - Life Redesign energy sync
8. **H6** - RIASEC classification order sync
9. **M1** - Growth Planning 3-column layout (entire game mode broken)
10. **M2** - Value Cards: fix card count (70 vs 36)

### Sprint 3 (Medium/Low)

11. **M3** - Value Cards rank swap UX
12. **M4-M8** - Life Redesign missing features
13. **L1-L8** - Polish items

---

## Cross-Cutting Root Cause Analysis

| Root Cause | Affected Bugs | Impact |
|-----------|--------------|--------|
| **WebSocket reorder events not sent/received** | H1, H4, H6 | Visitor-side reorder broken across 4+ games |
| **Settings broadcast missing** | H2 | Limit/config changes are local-only |
| **File upload not via WebSocket/shared state** | H3 | Upload stored client-side only |
| **html2canvas / screenshot library issue** | C2 | Cross-origin images or canvas elements not captured |
| **Game D template incomplete** | M1 | Growth Planning mode has wrong layout |
| **Wrong card deck loaded for Game F** | M2 | Loading full 70-card deck instead of 36-card subset |

---

*Generated: 2026-02-15*
