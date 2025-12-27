# Incremental Billing Test Suite - Implementation Guide

## Overview
This test suite verifies incremental billing with ceiling rounding for SessionUsage.

## Current Status
- ✅ Test file created: `test_incremental_billing.py`
- ❌ Implementation incomplete: Tests will fail until incremental billing logic is added

## What Needs to be Implemented

### 1. Update `save_analysis_log_and_usage()` in `keyword_analysis_service.py`

The current implementation uses **token-based pricing**. For incremental billing with ceiling rounding, we need to add **time-based pricing** support.

#### Required Changes:

```python
# In save_analysis_log_and_usage() method (around line 410-503)

# Add after line 434 (current_time = datetime.now(timezone.utc)):

# Calculate duration and minutes (ceiling rounding)
if session_usage:
    # Existing session: calculate duration from start_time
    duration_seconds = int((current_time - session_usage.start_time).total_seconds())
else:
    # New session: first analysis at 0 seconds
    duration_seconds = 0

# Calculate current total minutes (ceiling rounding)
import math
current_total_minutes = math.ceil(duration_seconds / 60) if duration_seconds > 0 else 0

# Get last billed minutes (incremental billing tracking)
last_billed_minutes = session_usage.last_billed_minutes if session_usage else 0

# Calculate incremental minutes (only charge for NEW minutes)
incremental_minutes = max(0, current_total_minutes - last_billed_minutes)

# If pricing rule is time-based, use incremental minutes
pricing_rule = self._get_pricing_rule(tenant_id)
if pricing_rule.get("unit") == "minute":
    # Time-based pricing: only charge for new minutes
    credits_for_this_analysis = incremental_minutes * pricing_rule.get("rate", 1.0)
else:
    # Token-based pricing (existing logic)
    credits_for_this_analysis = self._calculate_credits(pricing_rule, total_tokens)

# Update last_billed_minutes
if session_usage:
    session_usage.last_billed_minutes = current_total_minutes
else:
    # New session usage will be created with last_billed_minutes
    pass
```

#### Update CREATE section (around line 470-487):

```python
# When creating new SessionUsage, add:
session_usage = SessionUsage(
    # ... existing fields ...
    last_billed_minutes=incremental_minutes,  # ADD THIS
)
```

#### Update UPDATE section (around line 436-467):

```python
# When updating existing SessionUsage, add:
session_usage.last_billed_minutes = current_total_minutes  # ADD THIS
```

### 2. Update Counselor Credits

Currently, `counselor.credits_used` is NOT automatically updated in `save_analysis_log_and_usage()`.

#### Required Changes:

```python
# In save_analysis_log_and_usage(), before self.db.commit() (around line 496):

# Update counselor.credits_used (IMPORTANT: synchronize with session_usage.credits_deducted)
from app.models.counselor import Counselor
counselor = self.db.query(Counselor).filter(Counselor.id == counselor_id).first()
if counselor:
    # Add incremental credits (only the credits from THIS analysis)
    counselor.credits_used = (counselor.credits_used or 0) + credits_for_this_analysis
    logger.info(
        f"Updated counselor {counselor_id} credits_used: "
        f"+{credits_for_this_analysis} → total {counselor.credits_used}"
    )
```

### 3. Update Pricing Rule Configuration

The current `_get_pricing_rule()` returns token-based pricing by default. For time-based billing tests:

```python
# In _get_pricing_rule() method (around line 505-519):

def _get_pricing_rule(self, tenant_id: str) -> Dict:
    """
    Get pricing rule for tenant.

    Returns:
        Pricing rule dict:
        - Time-based: {"unit": "minute", "rate": 1.0}
        - Token-based: {"unit": "token", "rate": 0.001}
    """
    # TODO: Load from database tenant configuration
    # For now, default to time-based pricing for all tenants
    return {"unit": "minute", "rate": 1.0}

    # Alternative: tenant-specific rules
    # if tenant_id == "island_parents":
    #     return {"unit": "minute", "rate": 1.0}
    # else:
    #     return {"unit": "token", "rate": 0.001}
```

## Test Suite Coverage

### Scenarios Tested (10 tests):

1. ✅ **test_single_minute_multiple_analyses**
   - Multiple analyses within 60 seconds
   - Should only deduct 1 credit total

2. ✅ **test_cross_minute_incremental_billing**
   - Analyses at 30s, 90s, 185s
   - Incremental: 1, +1, +2 credits = 4 total

3. ✅ **test_rapid_consecutive_analyses**
   - 10 analyses in 60 seconds
   - Prevent duplicate billing: only 1 credit

4. ✅ **test_edge_case_boundaries**
   - Test ceiling at 1s, 59s, 60s, 61s, 119s, 121s
   - Verify ceiling rounding correctness

5. ✅ **test_normal_completion_workflow**
   - Multiple analyses with final completion
   - Verify credits match ceiling(duration/60)

6. ✅ **test_interrupted_session**
   - Analyses without completion call
   - Verify credits already deducted (no loss)

7. ✅ **test_long_gap_between_analyses**
   - 30s → 600s (10 minutes)
   - Incremental: 1, +9 credits = 10 total

8. ✅ **test_zero_duration_analysis**
   - Edge case: analysis at start_time
   - Should handle duration=0 gracefully

9. ✅ **test_multi_tenant_isolation**
   - Two counselors, two tenants, two sessions
   - Verify billing isolation

10. ✅ **test_counselor_credits_used_updated**
    - Verify counselor.credits_used increments
    - Should match session_usage.credits_deducted

## How to Run Tests

```bash
# Run only incremental billing tests
poetry run pytest tests/integration/test_incremental_billing.py -v

# Run specific test
poetry run pytest tests/integration/test_incremental_billing.py::TestIncrementalBilling::test_cross_minute_incremental_billing -v

# Run with detailed output
poetry run pytest tests/integration/test_incremental_billing.py -v -s
```

## Expected Behavior

### Ceiling Rounding Formula:
```python
import math
billed_minutes = math.ceil(duration_seconds / 60)
```

### Incremental Billing Logic:
```python
# Only charge for NEW minutes
incremental_credits = (current_total_minutes - last_billed_minutes) * rate
```

### Example Timeline:
| Time | Duration | Ceiling Minutes | Last Billed | Incremental | Credits Deducted |
|------|----------|----------------|-------------|-------------|------------------|
| 30s  | 30s      | 1              | 0           | 1           | 1                |
| 90s  | 90s      | 2              | 1           | 1           | 2                |
| 185s | 185s     | 4              | 2           | 2           | 4                |

## Database Schema

### SessionUsage Table
```sql
-- Relevant fields for incremental billing
session_usages {
  duration_seconds INTEGER,          -- Total duration from start_time to end_time
  credits_deducted NUMERIC(10,2),    -- Total credits deducted (cumulative)
  last_billed_minutes INTEGER,       -- Last billed minutes (for incremental billing)
  start_time TIMESTAMP,              -- Session start time
  end_time TIMESTAMP,                -- Latest analysis time
}
```

### Counselor Table
```sql
-- Relevant fields for credit tracking
counselors {
  credits_total INTEGER,             -- Total credits purchased
  credits_used INTEGER,              -- Total credits consumed across all sessions
  available_credits INTEGER,         -- credits_total - credits_used (computed)
}
```

## Implementation Checklist

- [ ] Update `save_analysis_log_and_usage()` to calculate duration
- [ ] Implement ceiling rounding: `math.ceil(duration_seconds / 60)`
- [ ] Implement incremental billing: only charge for new minutes
- [ ] Update `last_billed_minutes` field in SessionUsage
- [ ] Update `counselor.credits_used` when deducting credits
- [ ] Update `_get_pricing_rule()` to support time-based pricing
- [ ] Run tests to verify implementation
- [ ] All 10 tests should pass

## Notes

- **Token-based pricing is NOT removed**: Both time-based and token-based pricing should coexist
- **Backward compatibility**: Existing token-based tests should still pass
- **Multi-tenant support**: Each tenant can have different pricing rules
- **Incremental safety**: Prevents double-billing if analysis is interrupted

## Next Steps

1. Implement incremental billing logic in `keyword_analysis_service.py`
2. Run tests: `pytest tests/integration/test_incremental_billing.py -v`
3. Fix any failing tests
4. Verify counselor.credits_used is synchronized
5. Add time-based pricing configuration to tenant settings (future enhancement)
