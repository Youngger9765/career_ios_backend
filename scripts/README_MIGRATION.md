# Billing Mode Migration: Prepaid → Subscription

## Overview

This migration converts ALL existing accounts from prepaid billing mode to subscription billing mode.

## What Changed

### Before Migration
- Default billing mode: `prepaid`
- Billing based on `available_credits`
- No monthly usage limits

### After Migration
- Default billing mode: `subscription`
- Monthly usage limit: 360 minutes (6 hours)
- Usage tracking per 30-day period
- `available_credits` preserved but not used

## Migration Scripts

### 1. `migrate_to_subscription.py` - Main Migration Script

Converts all prepaid accounts to subscription mode.

**Dry Run (Preview)**:
```bash
python scripts/migrate_to_subscription.py
```

**Execute Migration**:
```bash
python scripts/migrate_to_subscription.py --execute
```

**What It Does**:
- Finds all counselors with `billing_mode = 'prepaid'`
- Updates each account:
  - `billing_mode`: `prepaid` → `subscription`
  - `monthly_usage_limit_minutes`: → `360` (6 hours)
  - `monthly_minutes_used`: → `0`
  - `usage_period_start`: → `NOW()`
  - `available_credits`: PRESERVED (not deleted)
- Requires confirmation before executing
- All changes in single transaction (rollback on error)

### 2. `verify_migration.py` - Verification Script

Checks migration results.

```bash
python scripts/verify_migration.py
```

**Output**:
- Shows test account details
- Counts subscription vs prepaid accounts
- Lists any remaining prepaid accounts

### 3. `test_usage_api.py` - API Test

Tests the usage stats endpoint with migrated account.

```bash
python scripts/test_usage_api.py
```

**Verifies**:
- ✅ `billing_mode = subscription`
- ✅ `monthly_limit_minutes = 360`
- ✅ `monthly_used_minutes = 0`
- ✅ API returns subscription fields correctly

### 4. `create_test_account.py` - Helper Script

Creates a test account for API testing.

```bash
python scripts/create_test_account.py
```

**Test Credentials**:
- Email: `migration-test@example.com`
- Password: `test123456`
- Tenant: `career`

## Migration Results

### Execution Date
2026-02-03

### Statistics
- **Total accounts migrated**: 55
- **Prepaid accounts before**: 55
- **Prepaid accounts after**: 0
- **Subscription accounts after**: 55

### Sample Migrated Accounts
- admin@island.com
- purpleice9765@msn.com (career)
- admin@island-parents.com
- counselor@island-parents.com
- (and 51 more...)

## Verification

### Database Verification
```bash
python scripts/verify_migration.py
```

Expected output:
```
Total Accounts: 55
Subscription Mode: 55
Prepaid Mode: 0
✅ All accounts successfully migrated to subscription mode!
```

### API Verification
```bash
python scripts/test_usage_api.py
```

Expected response:
```json
{
  "billing_mode": "subscription",
  "monthly_limit_minutes": 360,
  "monthly_used_minutes": 0,
  "monthly_remaining_minutes": 360,
  "usage_percentage": 0.0,
  "is_limit_reached": false,
  "usage_period_start": "2026-02-03T05:49:15.109016Z",
  "usage_period_end": "2026-03-05T05:49:15.109016Z",
  "available_credits": null
}
```

## Important Notes

1. **Credits Preserved**: `available_credits` field is NOT deleted, just not used in subscription mode
2. **30-Day Periods**: Usage tracking resets every 30 days from `usage_period_start`
3. **New Accounts**: All new accounts created after this migration will default to subscription mode
4. **No Rollback Needed**: Migration was successful, all 55 accounts converted
5. **Backward Compatibility**: Old prepaid logic still exists in code for potential future use

## Testing with Real Account

```bash
# Use migration-test account
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"migration-test@example.com","password":"test123456","tenant_id":"career"}'

# Get token from response, then:
curl -X GET http://localhost:8000/api/v1/usage/stats \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Related Files

### Models
- `app/models/counselor.py` - Counselor model with billing fields

### API Endpoints
- `app/api/v1/endpoints/usage.py` - Usage stats endpoint

### Migration Scripts
- `scripts/migrate_to_subscription.py` - Main migration
- `scripts/verify_migration.py` - Verification
- `scripts/test_usage_api.py` - API testing
- `scripts/create_test_account.py` - Test account creation

## Rollback (If Needed)

If you need to rollback, create a reverse migration:

```python
# NOT NEEDED - Migration was successful
# But here's how you would do it:
for counselor in subscription_counselors:
    counselor.billing_mode = BillingMode.PREPAID.value
    counselor.monthly_usage_limit_minutes = None
    counselor.monthly_minutes_used = None
    counselor.usage_period_start = None
```

## Next Steps

1. ✅ Migration completed successfully
2. ✅ All accounts verified in subscription mode
3. ✅ API endpoint tested and working
4. ⏳ Monitor production for any issues
5. ⏳ Update frontend to show subscription UI
6. ⏳ Update documentation with new billing model

## Support

For issues or questions about this migration, contact the development team.
