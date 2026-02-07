# Dashboard Upgrade - 2025-02-07

## Overview

Complete overhaul of the Admin Dashboard to provide meaningful cost analysis and usage metrics, eliminating misleading "Total Tokens" aggregation and providing service-level cost breakdown.

## Changes Summary

### 1. Centralized Pricing Module (`app/core/pricing.py`)

**Purpose**: Single source of truth for all AI service pricing.

**Features**:
- ElevenLabs Scribe v2 Realtime pricing
- Gemini Flash Lite pricing (emotion analysis)
- Gemini 1.5 Flash pricing (deep analysis, quick feedback)
- Gemini 1.5 Flash Report pricing (report generation)
- Model name to pricing mapping
- Helper functions for cost calculation

**Example Usage**:
```python
from app.core.pricing import calculate_cost_for_model

cost = calculate_cost_for_model(
    model_name="gemini-flash-lite-latest",
    input_tokens=1000,
    output_tokens=500
)
```

**Pricing Sources**:
- ElevenLabs: https://elevenlabs.io/pricing
- Gemini: https://ai.google.dev/pricing

---

### 2. Service Updates (Using Centralized Pricing)

Updated the following services to use `app/core/pricing`:

1. **`app/services/analysis/emotion_service.py`**
   - Now uses `calculate_cost_for_model("gemini-flash-lite-latest", ...)`

2. **`app/services/core/quick_feedback_service.py`**
   - Now uses `calculate_cost_for_model("gemini-1.5-flash-latest", ...)`

3. **`app/services/analysis/parents_report_service.py`**
   - Now uses `calculate_gemini_cost()` with report-tier pricing

4. **`app/services/analysis/session_billing_service.py`**
   - Now uses `calculate_elevenlabs_cost(duration_seconds)`

**Benefits**:
- No more hardcoded pricing in multiple files
- Easy to update pricing when vendors change rates
- Consistent cost calculation across all services
- Traceable pricing sources (links in comments)

---

### 3. Database Fix Script (`scripts/fix_emotion_model_names.py`)

**Problem**: Historical data incorrectly labeled emotion analysis as `gemini-3-flash-preview`.

**Solution**: Interactive script to update all emotion analysis logs to `gemini-flash-lite-latest`.

**Usage**:
```bash
cd /Users/young/project/career_ios_backend
poetry run python scripts/fix_emotion_model_names.py
```

**Features**:
- Preview changes before applying
- Interactive confirmation
- Verification after update
- Audit trail in logs

**Safety**:
- Read-only preview first
- User confirmation required
- Reversible (logs old values)

---

### 4. Dashboard API Updates (`app/api/v1/admin/dashboard.py`)

#### Removed Endpoints:
- None (all existing endpoints preserved for backward compatibility)

#### Modified Endpoints:

**`GET /summary`**:
- **Removed**: `total_tokens` field
- **Why**: Tokens from different models are not comparable (different pricing)
- **Response**:
  ```json
  {
    "total_cost_usd": 12.34,
    "total_sessions": 123,
    "active_users": 45
  }
  ```

**`GET /model-distribution`**:
- **Changed**: Now returns cost distribution instead of token count
- **Response**:
  ```json
  {
    "labels": ["Gemini Flash Lite", "Gemini Flash 1.5"],
    "costs": [8.23, 4.11],
    "tokens": [1234567, 567890]
  }
  ```

#### New Endpoints:

**`GET /cost-breakdown`** (NEW):
- **Purpose**: Show cost by service type (ElevenLabs STT vs AI models)
- **Response**:
  ```json
  {
    "services": [
      {
        "name": "ElevenLabs STT",
        "cost": 8.50,
        "percentage": 65.5,
        "usage": "21.3 hours"
      },
      {
        "name": "Gemini Flash Lite",
        "cost": 2.30,
        "percentage": 17.7,
        "usage": "12.5M tokens"
      },
      {
        "name": "Gemini Flash 1.5",
        "cost": 2.20,
        "percentage": 16.8,
        "usage": "3.2M tokens"
      }
    ],
    "total_cost": 13.00
  }
  ```

**`GET /session-trend`** (NEW):
- **Purpose**: Show daily session count and usage duration trends
- **Replaces**: Token usage trend (which was confusing)
- **Response**:
  ```json
  {
    "labels": ["2/1", "2/2", "2/3", "2/4", "2/5"],
    "sessions": [12, 15, 8, 20, 18],
    "duration_hours": [2.5, 3.1, 1.8, 4.2, 3.7]
  }
  ```

---

### 5. Dashboard UI Updates (`app/templates/admin_dashboard.html`)

#### Summary Cards (Top Row):
- **Before**: 4 cards (Total Tokens, Total Cost, Total Sessions, Active Users)
- **After**: 3 cards (Total Cost, Total Sessions, Active Users)
- **Why**: "Total Tokens" is meaningless when mixing different models

#### New Section: Cost Breakdown by Service
- **Location**: Below summary cards
- **Purpose**: Show which service is costing the most
- **Display**: List with service name, cost, percentage, and usage
- **Example**:
  ```
  Cost Breakdown by Service
  ┌─────────────────────────────────────────────┐
  │ ElevenLabs STT:  $8.50 (65.5%)  21.3 hours  │
  │ Gemini Lite:     $2.30 (17.7%)  12.5M tokens│
  │ Gemini Flash 1.5:$2.20 (16.8%)  3.2M tokens │
  └─────────────────────────────────────────────┘
  ```

#### Charts:
1. **Cost Trend** (unchanged)
   - Line chart showing cost over time

2. **Daily Session Trend** (NEW - replaced Token Usage Trend)
   - Dual-axis line chart
   - Left Y-axis: Session count
   - Right Y-axis: Duration in hours
   - **Why**: More meaningful than token counts

3. **Model Distribution** (updated)
   - Pie chart showing cost distribution (not token count)
   - Tooltip shows both cost and token count
   - **Why**: Cost is what matters for business decisions

4. **Safety Level Distribution** (unchanged)
   - Bar chart showing green/yellow/red safety levels

---

## Testing Checklist

### Backend Testing:

```bash
# 1. Start server
poetry run uvicorn app.main:app --reload

# 2. Test new endpoints
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://localhost:8000/api/v1/admin/dashboard/cost-breakdown?time_range=week"

curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://localhost:8000/api/v1/admin/dashboard/session-trend?time_range=week"

# 3. Test updated endpoints
curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://localhost:8000/api/v1/admin/dashboard/summary?time_range=week"

curl -H "Authorization: Bearer <ADMIN_TOKEN>" \
  "http://localhost:8000/api/v1/admin/dashboard/model-distribution?time_range=week"
```

### Database Fix Testing:

```bash
# Run the fix script (interactive)
poetry run python scripts/fix_emotion_model_names.py

# Verify manually
poetry run python -c "
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT model_name, COUNT(*) as count
        FROM session_analysis_logs
        WHERE analysis_result->>'analysis_type' = 'emotion_feedback'
        GROUP BY model_name
    '''))
    for row in result:
        print(f'{row.model_name}: {row.count}')
"
```

Expected output:
```
gemini-flash-lite-latest: 456  # All emotion logs should have this model
```

### Frontend Testing:

1. **Login as admin**:
   - Navigate to: https://island-parents-staging.web.app/admin/login
   - Login with admin credentials

2. **Check Summary Cards**:
   - Should show 3 cards (not 4)
   - Total Tokens card should be gone
   - Values should load correctly

3. **Check Cost Breakdown**:
   - New section below summary cards
   - Should show ElevenLabs STT + Gemini models
   - Percentages should add up to ~100%

4. **Check Charts**:
   - Cost Trend: should work as before
   - Daily Session Trend: new chart (2 lines: sessions + hours)
   - Model Distribution: pie chart, hover shows cost + tokens
   - Safety Distribution: should work as before

5. **Test Time Range Filters**:
   - Click "今天" (Today)
   - Click "過去7天" (Past 7 days)
   - Click "過去30天" (Past 30 days)
   - All data should update

6. **Test Tenant Filter**:
   - Select "All Tenants"
   - Select "Career"
   - Select "Island Parents"
   - Cost breakdown should update

---

## Migration Plan

### Phase 1: Backend (Safe Deployment)
1. Deploy `app/core/pricing.py` (new file)
2. Deploy updated services (backward compatible)
3. Deploy updated dashboard API (backward compatible)
4. **Risk**: Low (all changes backward compatible)

### Phase 2: Database Fix (Low Risk)
1. Run `fix_emotion_model_names.py` on staging
2. Verify results
3. Run on production
4. **Risk**: Low (read-only queries + manual confirmation)

### Phase 3: Frontend (High Visibility)
1. Deploy updated dashboard HTML to staging
2. Test all features (summary, breakdown, charts)
3. Deploy to production
4. **Risk**: Medium (UI changes visible to all admins)

---

## Rollback Plan

### If backend issues:
```bash
# Revert to previous commit
git revert <commit-hash>
git push origin staging
```

### If database fix issues:
```bash
# Rollback SQL (restore old model_name)
poetry run python -c "
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('''
        UPDATE session_analysis_logs
        SET model_name = 'gemini-3-flash-preview'
        WHERE model_name = 'gemini-flash-lite-latest'
          AND analysis_result->>'analysis_type' = 'emotion_feedback'
    '''))
    conn.commit()
"
```

### If frontend issues:
- Revert `app/templates/admin_dashboard.html` to previous version
- Redeploy

---

## Performance Considerations

### Database Queries:
- All queries use indexed fields (`analyzed_at`, `created_at`, `tenant_id`)
- Cost breakdown uses aggregation (fast)
- Session trend uses date_trunc (optimized)

### Expected Query Times:
- Summary: <100ms
- Cost Breakdown: <200ms
- Session Trend: <150ms
- Model Distribution: <150ms

### Optimization Recommendations:
1. Add composite index if needed:
   ```sql
   CREATE INDEX idx_sal_analyzed_tenant ON session_analysis_logs(analyzed_at, tenant_id);
   ```

2. Consider materialized view for cost breakdown (if slow):
   ```sql
   CREATE MATERIALIZED VIEW daily_cost_breakdown AS
   SELECT ...
   REFRESH MATERIALIZED VIEW daily_cost_breakdown;
   ```

---

## Documentation Updates Needed

1. **API Docs** (`docs/api.md`):
   - Add `/cost-breakdown` endpoint
   - Add `/session-trend` endpoint
   - Update `/summary` response schema
   - Update `/model-distribution` response schema

2. **User Guide** (`docs/admin-guide.md`):
   - Update dashboard screenshots
   - Add explanation of cost breakdown
   - Explain session trend chart

3. **Developer Guide** (`docs/development.md`):
   - Document centralized pricing module
   - Add pricing update procedures

---

## Future Improvements

### Short-term (Next Sprint):
1. Add cost alerts (email when exceeding budget)
2. Add cost projections (forecast next 30 days)
3. Add per-user cost breakdown

### Medium-term (1-2 months):
1. Add cost optimization suggestions
2. Add model performance comparison (cost vs quality)
3. Add budget management features

### Long-term (3-6 months):
1. Real-time cost dashboard (WebSocket updates)
2. Cost anomaly detection (ML-based)
3. Multi-currency support

---

## Success Metrics

### Technical Metrics:
- Database fix script completes in <2 minutes
- All API endpoints respond in <200ms
- Dashboard loads in <2 seconds

### Business Metrics:
- Admins can identify most expensive service in 5 seconds
- Cost decisions based on accurate service breakdown
- Reduced confusion about "Total Tokens" metric

---

## Questions & Answers

**Q: Why not just fix the "Total Tokens" calculation?**
A: Because tokens from different models have different costs. Adding "1000 Flash Lite tokens" + "1000 Flash 1.5 tokens" is like adding "1 apple" + "1 car" - the units are incomparable.

**Q: Can we still see token counts somewhere?**
A: Yes! In the Model Distribution pie chart tooltip, and in the Cost Breakdown section (shows "X.XM tokens" for each model).

**Q: What if pricing changes?**
A: Update `app/core/pricing.py` only. All services will automatically use new pricing. Historical data costs are already stored in DB.

**Q: Will this affect billing to customers?**
A: No. This only affects internal monitoring. Customer billing uses `CreditLog` table, which is separate.

---

## Contact

For questions about this upgrade:
- Implementation: @claude (AI assistant)
- Review: @young (Product Owner)
- Testing: QA Team
- Deployment: DevOps Team

---

**Document Version**: 1.0
**Last Updated**: 2025-02-07
**Status**: Ready for Review
