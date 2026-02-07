# Dashboard Time Filtering - Before vs After

## Visual Comparison

### Bug #1: `get_top_users` - Missing Gemini cost filter

**BEFORE (Wrong):**
```python
.outerjoin(SessionAnalysisLog, SessionUsage.session_id == SessionAnalysisLog.session_id)
.where(SessionUsage.created_at >= start_time)  # ✅ Filters usage
# ❌ MISSING: No filter on SessionAnalysisLog.analyzed_at
```

**Result:** User selects "Today", but sees Gemini costs from last month.

**AFTER (Fixed):**
```python
.outerjoin(SessionAnalysisLog, SessionUsage.session_id == SessionAnalysisLog.session_id)
.where(SessionUsage.created_at >= start_time)  # ✅ Filters usage
.where(
    or_(
        SessionAnalysisLog.id.is_(None),
        SessionAnalysisLog.analyzed_at >= start_time  # ✅ Filters analysis
    )
)
```

**Result:** User selects "Today", sees only today's Gemini costs.

---

### Bug #2: `get_user_segments` - Ignored time_range parameter

**BEFORE (Wrong):**
```python
def get_user_segments(
    time_range: Literal["day", "week", "month"] = Query("month"),  # ❌ UNUSED
    ...
):
    base_query = (
        select(...)
        .outerjoin(SessionUsage, ...)
        .outerjoin(SessionAnalysisLog, ...)
        .where(Counselor.created_at < now - timedelta(days=7))  # ❌ Only checks registration
        # ❌ MISSING: No start_time calculation
        # ❌ MISSING: No filter on SessionUsage.created_at
        # ❌ MISSING: No filter on SessionAnalysisLog.analyzed_at
    )
```

**Result:** User segments always show ALL historical data, regardless of time range selection.

**AFTER (Fixed):**
```python
def get_user_segments(
    time_range: Literal["day", "week", "month"] = Query("month"),  # ✅ USED
    ...
):
    start_time = get_time_filter(time_range)  # ✅ Calculate filter

    base_query = (
        select(...)
        .outerjoin(SessionUsage, ...)
        .outerjoin(SessionAnalysisLog, ...)
        .where(Counselor.created_at < now - timedelta(days=7))
        .where(  # ✅ Filter usage by time
            or_(
                SessionUsage.id.is_(None),
                SessionUsage.created_at >= start_time
            )
        )
        .where(  # ✅ Filter analysis by time
            or_(
                SessionAnalysisLog.id.is_(None),
                SessionAnalysisLog.analyzed_at >= start_time
            )
        )
    )
```

**Result:** User segments reflect activity within selected time range.

---

### Bug #3: `export_csv` - Missing Gemini cost filter

**BEFORE (Wrong):**
```python
.outerjoin(SessionAnalysisLog, SessionUsage.session_id == SessionAnalysisLog.session_id)
.where(SessionUsage.created_at >= start_time)  # ✅ Filters usage
# ❌ MISSING: No filter on SessionAnalysisLog.analyzed_at
```

**Result:** CSV exports include all historical Gemini costs, even when "Today" is selected.

**AFTER (Fixed):**
```python
.outerjoin(SessionAnalysisLog, SessionUsage.session_id == SessionAnalysisLog.session_id)
.where(SessionUsage.created_at >= start_time)  # ✅ Filters usage
.where(
    or_(
        SessionAnalysisLog.id.is_(None),
        SessionAnalysisLog.analyzed_at >= start_time  # ✅ Filters analysis
    )
)
```

**Result:** CSV exports match the selected time range accurately.

---

## Impact on Real Data

### Test Database Statistics

```
SessionUsage records (last 7 days): 5
SessionAnalysisLog records (last 7 days): 51
SessionAnalysisLog records (BEFORE last 7 days): 924  ← Would be wrongly included!
```

### Example Scenario

**User selects "7 Days":**

| Metric | Before Fix | After Fix |
|--------|-----------|-----------|
| ElevenLabs cost | ✅ Last 7 days only | ✅ Last 7 days only |
| Gemini cost | ❌ ALL TIME (924 + 51 = 975 logs) | ✅ Last 7 days only (51 logs) |
| User segments | ❌ ALL TIME activity | ✅ Last 7 days only |
| CSV export | ❌ ALL TIME costs | ✅ Last 7 days only |

**Cost Inflation:** If average Gemini cost is $0.01 per log:
- Before: $9.75 (975 logs × $0.01)
- After: $0.51 (51 logs × $0.01)
- **Error: 1800% inflation!**

---

## Why `or_(SessionAnalysisLog.id.is_(None), ...)` Pattern?

### Without the Pattern (WRONG):

```python
.outerjoin(SessionAnalysisLog, ...)
.where(SessionAnalysisLog.analyzed_at >= start_time)  # ❌ Drops sessions without analysis
```

**Problem:** Filters out sessions that don't have analysis logs yet (NULL values from outerjoin).

### With the Pattern (CORRECT):

```python
.outerjoin(SessionAnalysisLog, ...)
.where(
    or_(
        SessionAnalysisLog.id.is_(None),  # Keep sessions without analysis
        SessionAnalysisLog.analyzed_at >= start_time  # Filter sessions with analysis
    )
)
```

**Benefits:**
1. ✅ Keeps sessions without analysis logs (NULL handling)
2. ✅ Filters analysis logs by time range (accurate costs)
3. ✅ Correct user counts (doesn't lose users with sessions but no analysis)

---

## Testing the Fix

### Before Deployment

```bash
# Run manual test
poetry run python tests/manual/test_dashboard_time_filtering.py

# Check linting
poetry run ruff check app/api/v1/admin/dashboard.py
```

### After Deployment

1. **Open Admin Dashboard**
2. **Select "Today"**
   - Note the "Total Cost"
3. **Select "7 Days"**
   - Total Cost should be >= Today's cost
4. **Select "30 Days"**
   - Total Cost should be >= 7 Days' cost
5. **Verify Top Users table**
   - Costs should change with time range
6. **Export CSV**
   - Verify costs match dashboard display

---

## Files Changed

```
app/api/v1/admin/dashboard.py                    # Fixed 3 endpoints
tests/manual/test_dashboard_time_filtering.py    # Verification test
DASHBOARD_TIME_FILTER_FIXES.md                   # Technical summary
DASHBOARD_FIX_COMPARISON.md                      # This file
```

---

## Deployment Checklist

- [x] Fix applied to `get_top_users`
- [x] Fix applied to `get_user_segments`
- [x] Fix applied to `export_csv`
- [x] Import `or_` added
- [x] Linting passed
- [x] Module imports successfully
- [x] Manual test created
- [x] Documentation written
- [ ] Push to staging branch
- [ ] Test on staging server
- [ ] Verify dashboard displays correct costs
- [ ] Merge to production
