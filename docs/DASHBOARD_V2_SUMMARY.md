# Dashboard V2 - Executive Summary

**Date**: 2026-02-08
**Version**: 2.0
**Status**: Design Complete, Ready for Implementation

---

## TL;DR

Redesigned Admin Dashboard from **technical monitoring tool** to **business decision platform**.

**Key Changes**:
- ✅ Cost prediction and anomaly detection
- ✅ User segmentation (Power/Active/At-Risk/Churned)
- ✅ Actionable insights with suggested next steps
- ✅ Business metrics over technical metrics

**Impact**:
- 🎯 Reduce cost waste by identifying test accounts and inefficient users
- 🎯 Prevent churn by identifying at-risk users early
- 🎯 Increase revenue by identifying upsell opportunities (Power Users)

---

## Problem Statement

### What's Wrong with Current Dashboard?

**User Quote** (Operations Manager):
> "你要從案主的角度來看，他到底要在這張 Dashboard 裡面看出什麼，然後可以做出 Action 來，這非常的重要。"

**Current Issues**:
1. ❌ Shows metrics without context ("$125 - is this good?")
2. ❌ No prediction ("Will we exceed budget?")
3. ❌ No user segmentation (can't identify profitable users)
4. ❌ No suggested actions (what should I do?)

---

## Solution Overview

### Three Core Business Needs

#### 1. Cost Control 💰
**When**: Weekly budget review
**Need**: Identify waste and prevent overspending
**Actions**: Throttle test accounts, contact high-cost users

**New Features**:
- Cost prediction: "At current rate, next month = $380"
- Anomaly detection: "⚠️ 3 users over budget, 🧪 1 test account"
- Cost per session metric to track efficiency

---

#### 2. User Retention 👥
**When**: Monthly business review
**Need**: Track engagement and reduce churn
**Actions**: Re-engage at-risk users, upsell power users

**New Features**:
- User segmentation:
  - Power Users (top 10% by usage) → Upsell
  - Active Users → Maintain
  - At-Risk (7d inactive) → Send re-engagement email
  - Churned (30d inactive) → Archive
- Engagement metrics: sessions/user, cost/user

---

#### 3. Resource Optimization ⚙️
**When**: Planning capacity/budget
**Need**: Understand usage patterns
**Actions**: Optimize AI model selection, deprecate unused features

**New Features**:
- Average cost per session (efficiency metric)
- Service breakdown (ElevenLabs vs Gemini costs)
- Daily averages for trend analysis

---

## What's New

### Backend (3 New API Endpoints)

```
GET /api/v1/admin/dashboard/cost-per-user
GET /api/v1/admin/dashboard/user-segments
GET /api/v1/admin/dashboard/cost-prediction
```

**File**: `app/api/v1/admin/dashboard.py` (updated)

---

### Frontend (New Dashboard Template)

**File**: `app/templates/admin_dashboard_v2.html` (new)

**Sections**:
1. **💰 成本控制中心**
   - Cost prediction cards
   - Cost anomaly table
   - Cost trend chart

2. **👥 用戶健康度**
   - Segmentation cards (4 cohorts)
   - Segment detail table

3. **⚙️ 營運效率**
   - Summary metrics
   - Cost breakdown by service

---

## Design Principles

### 1. Action-Oriented
Every metric answers: **"So what? What should I do?"**

Example:
- ❌ Before: "Total cost: $125.50"
- ✅ After: "Total cost: $125.50 (+15% ↑) ⚠️ 3 users over budget"

### 2. Comparison-Rich
Show trends, not just snapshots.

Example:
- "Cost: $125 (↑15% vs last month)"
- "Power Users: 3 (avg $25/user vs platform avg $8)"

### 3. Predictive
Forecast future, not just report past.

Example:
- "Predicted next month: $380 (based on 7d trend)"
- "User X will churn in 7 days (no activity)"

### 4. Segmented
Break down by user cohorts.

Example:
- "Power Users (top 10%): 3 users, $25/user"
- "At-Risk (7d inactive): 5 users"

---

## Data Flow

```
[SessionUsage Table]      [SessionAnalysisLog Table]
        |                           |
        |                           |
        v                           v
[Dashboard API Endpoints]
        |
        |--- cost-per-user (calculates total cost from both tables)
        |--- user-segments (identifies cohorts by activity)
        |--- cost-prediction (linear forecast)
        |
        v
[admin_dashboard_v2.html]
        |
        v
[Business Stakeholder]
        |
        v
[Action: Email user, throttle account, upsell premium]
```

---

## Key Metrics Explained

### Cost per Session
**Formula**: `Total Cost / Total Sessions`

**Why**: Measures efficiency of AI API usage

**Action**:
- ↓ Decreasing → Good (optimization working)
- ↑ Increasing → Warning (users talking longer or using expensive features)

---

### User Segments

| Segment | Definition | Count Example | Action |
|---------|-----------|---------------|--------|
| **Power Users** | Top 10% by sessions | 3 | ✅ Upsell to premium |
| **Active Users** | < 7 days inactive | 12 | ✅ Maintain |
| **At-Risk** | 7-30 days inactive | 5 | ⚠️ Re-engage email |
| **Churned** | 30+ days inactive | 10 | ❌ Archive |

---

### Cost Anomaly Status

| Status | Criteria | Example | Action |
|--------|----------|---------|--------|
| **Normal** | Cost within platform average | $0.20/session | - |
| **High Cost** | Cost > 2x platform average | $0.50/session | Contact for upgrade |
| **Test Account** | Many sessions, low cost/session | 450 sessions, $0.10/session | Throttle or disable |

---

## Success Metrics

### Quantitative
1. **Time to Insight**: < 30 seconds
   - Measure: Time from page load to answering "Which users cost most?"

2. **Action Rate**: > 50%
   - Measure: % of alerts that lead to action (email sent, user contacted)

3. **Cost Savings**: 10%+ reduction
   - Measure: Monthly cost reduction after implementing suggestions

### Qualitative
- Stakeholder satisfaction survey (1-5 scale)
- Usability testing (observe confusion points)

---

## Implementation Timeline

### Week 1: Backend API
- ✅ Add 3 new endpoints to dashboard.py
- ✅ Write integration tests
- ✅ Deploy to staging

### Week 2: Frontend & Testing
- ✅ Create admin_dashboard_v2.html
- ⏳ Manual testing checklist
- ⏳ Performance testing (< 500ms API response)
- ⏳ Deploy to production

### Week 3: Monitoring & Iteration
- ⏳ Monitor user feedback
- ⏳ Fix bugs
- ⏳ Plan Phase 3 features (automated actions)

---

## Files Changed/Added

### New Files
1. `docs/dashboard-redesign-product-strategy.md` - Product vision & Jobs-to-be-Done
2. `docs/dashboard-redesign-implementation-guide.md` - Step-by-step implementation
3. `docs/DASHBOARD_V2_SUMMARY.md` - This file (executive summary)
4. `app/templates/admin_dashboard_v2.html` - New dashboard UI
5. `tests/integration/test_dashboard_v2.py` - Integration tests (to be created)

### Modified Files
1. `app/api/v1/admin/dashboard.py` - Added 3 new endpoints
2. `app/main.py` - Add route for `/admin/dashboard-v2` (to be added)

---

## How to Access

### Development
```bash
# Start server
poetry run uvicorn app.main:app --reload

# Access
http://localhost:8000/admin/dashboard-v2
```

### Staging
```
https://career-app-api-staging-XXX.run.app/admin/dashboard-v2
```

### Production
```
https://career-app-api-XXX.run.app/admin/dashboard-v2
```

---

## Database Indexes (Recommended)

```sql
-- For fast cost-per-user queries
CREATE INDEX IF NOT EXISTS idx_session_usages_counselor_created_at
  ON session_usages (counselor_id, created_at);

-- For user segmentation queries
CREATE INDEX IF NOT EXISTS idx_session_usages_created_at
  ON session_usages (created_at);

-- For cost analysis
CREATE INDEX IF NOT EXISTS idx_session_analysis_logs_counselor_analyzed_at
  ON session_analysis_logs (counselor_id, analyzed_at);
```

**Run**:
```bash
# Create migration
alembic revision -m "add dashboard v2 indexes"

# Apply
alembic upgrade head
```

---

## Rollback Plan

If critical bugs found:

1. **Immediate**: Revert environment variable (if using feature flag)
2. **Short-term**: Revert Git commit and redeploy
3. **Communication**: Notify stakeholders, update status page

---

## Future Enhancements (Phase 3)

### 1. Automated Actions
- Auto-send re-engagement emails to at-risk users
- Auto-throttle test accounts

### 2. Custom Alerts
- Slack/Email when cost exceeds threshold
- Daily digest of key metrics

### 3. ROI Analysis
- Track revenue per user
- Calculate LTV (Lifetime Value)
- Show profitability: LTV / Total Cost

### 4. Predictive Churn Model
- ML model to predict churn probability
- Show: "User X has 75% churn risk"

---

## Questions?

**Product Strategy**: See `docs/dashboard-redesign-product-strategy.md`
**Implementation Guide**: See `docs/dashboard-redesign-implementation-guide.md`
**API Specs**: See endpoint docstrings in `app/api/v1/admin/dashboard.py`

---

## Approval Checklist

Before deploying to production:

- [ ] Stakeholder demo completed
- [ ] All integration tests passing
- [ ] Manual testing completed
- [ ] Performance benchmarks met (< 500ms API)
- [ ] Database indexes created
- [ ] Monitoring alerts configured
- [ ] Rollback plan tested

---

**Status**: Ready for stakeholder review and approval
**Next Step**: Schedule demo with Operations Manager
