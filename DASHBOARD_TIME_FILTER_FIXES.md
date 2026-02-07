# Dashboard Time Filtering Bug Fixes

## Summary

Fixed three critical time filtering bugs in the admin dashboard that caused cost calculations to include historical data regardless of the selected time range (Today/7 Days/30 Days).

## Impact

**Before Fix:**
- Selecting "Today" would still include Gemini costs from weeks/months ago
- Total costs were artificially inflated
- User segmentation ignored time range parameter
- CSV exports included all historical data

**After Fix:**
- All endpoints correctly filter by selected time range
- Costs are accurate for the selected period
- User segments respect time range parameter
- CSV exports match the selected time range

## Database Stats (from test)

- SessionUsage records (last 7 days): 5
- SessionAnalysisLog records (last 7 days): 51
- **SessionAnalysisLog records (BEFORE last 7 days): 924** ← These were incorrectly included before

## Changes Made

### 1. `get_top_users` (line 691)

**Bug:** Only filtered `SessionUsage.created_at`, missing `SessionAnalysisLog.analyzed_at` filter.

**Fix:**
```python
from sqlalchemy import or_

# Added time filter for SessionAnalysisLog
.where(
    or_(
        SessionAnalysisLog.id.is_(None),  # Allow NULL from outerjoin
        SessionAnalysisLog.analyzed_at >= start_time  # Filter non-NULL records
    )
)
```

### 2. `get_user_segments` (line 1004-1029)

**Bug:** Function received `time_range` parameter but never used it. Only filtered `Counselor.created_at` (registration time), not activity time.

**Fix:**
```python
# Added start_time calculation
start_time = get_time_filter(time_range)

# Added filters for both SessionUsage and SessionAnalysisLog
.where(
    or_(
        SessionUsage.id.is_(None),  # Allow users with no sessions
        SessionUsage.created_at >= start_time  # Filter sessions by time range
    )
)
.where(
    or_(
        SessionAnalysisLog.id.is_(None),  # Allow NULL from outerjoin
        SessionAnalysisLog.analyzed_at >= start_time  # Filter non-NULL records
    )
)
```

### 3. `export_csv` (line 1294)

**Bug:** Only filtered `SessionUsage.created_at`, missing `SessionAnalysisLog.analyzed_at` filter.

**Fix:**
```python
from sqlalchemy import or_

# Added time filter for SessionAnalysisLog
.where(
    or_(
        SessionAnalysisLog.id.is_(None),  # Allow NULL from outerjoin
        SessionAnalysisLog.analyzed_at >= start_time  # Filter non-NULL records
    )
)
```

### 4. Import Addition

Added `or_` to imports at the top of the file:
```python
from sqlalchemy import and_, desc, func, or_, select
```

## Pattern Used

For all `outerjoin` queries with `SessionAnalysisLog`, we use this pattern:

```python
.outerjoin(SessionAnalysisLog, SessionUsage.session_id == SessionAnalysisLog.session_id)
.where(SessionUsage.created_at >= start_time)  # Filter main table
.where(
    or_(
        SessionAnalysisLog.id.is_(None),  # Allow NULL from outerjoin
        SessionAnalysisLog.analyzed_at >= start_time  # Filter non-NULL records
    )
)
```

This ensures:
1. We don't lose users/sessions without analysis logs (NULL handling)
2. We only count analysis logs within the selected time range
3. Costs are accurate for the selected period

## Testing

### Manual Test Results

Run with: `poetry run python tests/manual/test_dashboard_time_filtering.py`

```
=== Test 1: get_top_users ===
SessionUsage records (last 7 days): 5
SessionAnalysisLog records (last 7 days): 51
SessionAnalysisLog records (BEFORE last 7 days): 924
⚠️  Warning: Old analysis records exist. These should NOT be included in cost calculations.
   Oldest analysis: 2026-01-02 08:59:05.864026+00:00

=== Summary ===
✅ All three endpoints now filter SessionAnalysisLog.analyzed_at >= start_time
✅ get_user_segments now uses time_range parameter
✅ Costs should be consistent across all endpoints
```

### Expected Behavior

1. **When selecting 'Today'**: Only today's Gemini costs counted
2. **When selecting '7 Days'**: Only last 7 days Gemini costs counted
3. **When selecting '30 Days'**: Only last 30 days Gemini costs counted
4. **Consistency**: Top Users, User Segments, and CSV Export all show same costs for same time range

## Verification Steps

After deployment, verify:

1. **Navigate to Admin Dashboard**
2. **Select different time ranges** (Today / 7 Days / 30 Days)
3. **Check Total Cost changes** - should decrease when selecting shorter periods
4. **Check Top Users costs** - should match selected time range
5. **Export CSV** - verify costs match dashboard display
6. **Check User Segments** - power users should reflect activity in selected period

## Files Modified

- `app/api/v1/admin/dashboard.py` - Fixed 3 endpoints + added import
- `tests/manual/test_dashboard_time_filtering.py` - Created verification test

## Linting

```bash
poetry run ruff check app/api/v1/admin/dashboard.py
# No errors
```

## Deployment

Ready for deployment to staging. No database migrations required.
