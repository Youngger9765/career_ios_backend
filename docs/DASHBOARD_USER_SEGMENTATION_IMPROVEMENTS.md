# Dashboard User Segmentation Table Improvements

## Summary
Enhanced the user segmentation table in the Admin Dashboard with new columns and improved default display.

## Changes Made

### 1. Backend API Changes (`app/api/v1/admin/dashboard.py`)

#### Updated `/api/v1/admin/dashboard/user-segments` endpoint:

**New fields in query:**
- `total_duration_seconds`: Sum of all session durations
- `days_used`: Count of distinct days with activity (using `func.date_trunc`)

**New fields in response:**
- `total_duration_minutes`: Total duration in minutes (rounded to 1 decimal)
- `days_used`: Number of unique days the user has been active

**All user segments now include:**
```json
{
  "email": "user@example.com",
  "sessions": 10,
  "last_activity": "2024-02-09 15:30",
  "total_cost_usd": 5.42,
  "total_duration_minutes": 125.5,  // NEW
  "days_used": 8                     // NEW
}
```

### 2. Frontend Changes (`app/templates/admin_dashboard.html`)

#### New Features:
1. **Default Display**: Shows all users by default (no filter applied)
2. **New "全部用戶" Button**: Added as the first filter button
3. **New Columns**: Added 總時長 and 使用天數
4. **Chinese Headers**: All column headers now in Chinese

#### Updated Table Structure:
| Column | Chinese Header | English Equivalent | Data Type |
|--------|----------------|-------------------|-----------|
| Email | Email | Email | String |
| Sessions | 對話次數 | Session Count | Integer |
| Last Activity | 最後活動 | Last Activity | DateTime |
| Total Cost | 總成本 | Total Cost | USD (2 decimals) |
| **Total Duration** | **總時長** | **Total Duration** | **Minutes (1 decimal)** |
| **Days Used** | **使用天數** | **Days Used** | **Integer + "天"** |

#### Filter Buttons:
- **全部用戶** (All Users) - Shows all users combined
- **Power Users** - Top 10% by session count
- **Active Users** - Active in last 7 days
- **At-Risk** - No activity in 7-30 days
- **Churned** - No activity in 30+ days

#### Visual Improvements:
- Active button highlight (opacity: 1)
- Inactive buttons (opacity: 0.7)
- Proper loading state on page load
- Updated colspan to 6 for proper table layout

### 3. Data Calculation Details

**總時長 (Total Duration):**
- Calculated from `SessionUsage.duration_seconds`
- Converted to minutes: `duration_seconds / 60`
- Rounded to 1 decimal place
- Displayed as "X.X 分鐘"

**使用天數 (Days Used):**
- Uses SQL `func.count(func.distinct(func.date_trunc("day", SessionUsage.created_at)))`
- Counts unique calendar days with activity
- Displayed as "X 天"

## Testing Checklist

- [x] Backend syntax validation passed
- [x] Frontend HTML validation passed
- [x] Ruff linting passed
- [ ] Manual browser testing needed
- [ ] API response validation needed
- [ ] Test with different time ranges (day/week/month)

## API Response Example

```json
{
  "power_users": {
    "count": 5,
    "avg_sessions": 25.4,
    "avg_cost_usd": 12.34,
    "users": [
      {
        "email": "power@example.com",
        "sessions": 30,
        "last_activity": "2024-02-09 15:30",
        "total_cost_usd": 15.42,
        "total_duration_minutes": 245.5,
        "days_used": 12
      }
    ]
  },
  "active_users": {
    "count": 20,
    "avg_sessions": 10.2,
    "avg_cost_usd": 5.67,
    "users": [...]
  },
  "at_risk_users": {
    "count": 8,
    "users": [
      {
        "email": "atrisk@example.com",
        "sessions": 5,
        "last_activity": "2024-02-01 10:00",
        "days_inactive": 8,
        "total_duration_minutes": 45.5,
        "days_used": 3
      }
    ]
  },
  "churned_users": {
    "count": 3,
    "users": [...]
  }
}
```

## Files Modified

1. `/app/api/v1/admin/dashboard.py` - Backend API
2. `/app/templates/admin_dashboard.html` - Frontend template

## Backwards Compatibility

✓ All existing fields preserved
✓ No breaking changes to API structure
✓ Only additive changes (new fields)

## Next Steps

1. Test the dashboard in browser
2. Verify data accuracy with real database
3. Consider adding CSV export for new columns
4. Monitor performance with large user bases (pagination may be needed)

---
**Date**: 2024-02-09
**Version**: 1.0
**Author**: Claude Code
