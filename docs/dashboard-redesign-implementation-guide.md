# Dashboard Redesign Implementation Guide

**Version**: 2.0
**Date**: 2026-02-08
**Status**: Ready for Implementation

---

## Overview

This guide provides step-by-step instructions to implement the business-driven Admin Dashboard redesign.

---

## What Changed

### From: Technical Monitoring Dashboard
- Focus: Tokens, models, raw metrics
- User: Engineering team
- Value: Monitor system health

### To: Business Decision Platform
- Focus: Cost control, user retention, actionable insights
- User: Operations Manager, Finance Director
- Value: Make data-driven business decisions

---

## New Features

### 1. Cost Control Center 💰

**Features**:
- **Cost Prediction**: Forecast next month's cost based on current trend
- **Cost Anomaly Detection**: Identify users with abnormal spending patterns
- **Actionable Alerts**: "3 high-cost users, 1 test account detected"
- **Cost per Session**: Efficiency metric to track optimization

**New API Endpoints**:
```
GET /api/v1/admin/dashboard/cost-prediction
GET /api/v1/admin/dashboard/cost-per-user
```

**Business Value**:
- Prevent budget overruns
- Identify wasteful test accounts
- Prioritize users for upgrade offers

---

### 2. User Health Dashboard 👥

**Features**:
- **User Segmentation**: Power Users, Active, At-Risk, Churned
- **Engagement Metrics**: Sessions per user, cost per user
- **Churn Alerts**: "3 users haven't logged in for 7 days"
- **Suggested Actions**: "Send re-engagement email to at-risk users"

**New API Endpoints**:
```
GET /api/v1/admin/dashboard/user-segments
```

**Business Value**:
- Reduce churn by identifying at-risk users early
- Find high-value users for upsell opportunities
- Measure product-market fit (engagement levels)

---

### 3. Operational Efficiency ⚙️

**Features**:
- **Average Cost per Session**: Track AI optimization efforts
- **Service Cost Breakdown**: ElevenLabs vs Gemini spend
- **Daily Averages**: Normalized metrics for trend analysis

**Existing Endpoints** (Enhanced):
```
GET /api/v1/admin/dashboard/summary
GET /api/v1/admin/dashboard/cost-breakdown
```

**Business Value**:
- Measure ROI of optimization work
- Decide where to invest engineering time

---

## Implementation Steps

### Phase 1: Backend API Development (Week 1)

#### Step 1.1: Add New Endpoints to dashboard.py

**File**: `app/api/v1/admin/dashboard.py`

**Endpoints to Add**:
1. `/cost-per-user` - Cost anomaly detection
2. `/user-segments` - User cohort analysis
3. `/cost-prediction` - Monthly cost forecasting

**Status**: ✅ Already added in this PR

**Testing**:
```bash
# Test cost-per-user
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/admin/dashboard/cost-per-user?time_range=month&limit=20"

# Test user-segments
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/admin/dashboard/user-segments?time_range=month"

# Test cost-prediction
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/admin/dashboard/cost-prediction?time_range=month"
```

**Expected Response Examples**:

`/cost-per-user`:
```json
[
  {
    "email": "user@example.com",
    "full_name": "John Doe",
    "total_cost_usd": 45.20,
    "sessions": 120,
    "cost_per_session": 0.38,
    "total_minutes": 240.5,
    "status": "high_cost",
    "suggested_action": "Contact for premium upgrade"
  }
]
```

`/user-segments`:
```json
{
  "power_users": {
    "count": 3,
    "avg_sessions": 50.0,
    "avg_cost_usd": 25.0,
    "suggested_action": "Upsell to premium tier",
    "users": [...]
  },
  "active_users": {...},
  "at_risk_users": {...},
  "churned_users": {...}
}
```

`/cost-prediction`:
```json
{
  "current_month_cost": 125.50,
  "days_elapsed": 8,
  "days_remaining": 22,
  "daily_average": 15.69,
  "predicted_month_cost": 470.70,
  "last_month_cost": 380.00,
  "growth_pct": 23.9
}
```

---

#### Step 1.2: Write Integration Tests

**File**: `tests/integration/test_dashboard_v2.py` (New)

```python
"""
Integration tests for Dashboard v2 API endpoints
"""
import pytest
from app.models.counselor import CounselorRole


def test_cost_per_user(client, admin_headers, db_session):
    """Test cost-per-user endpoint returns user cost data"""
    response = client.get(
        "/api/v1/admin/dashboard/cost-per-user?time_range=month",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        user = data[0]
        assert "email" in user
        assert "total_cost_usd" in user
        assert "sessions" in user
        assert "cost_per_session" in user
        assert "status" in user
        assert user["status"] in ["normal", "high_cost", "test_account"]


def test_user_segments(client, admin_headers, db_session):
    """Test user-segments endpoint returns cohort data"""
    response = client.get(
        "/api/v1/admin/dashboard/user-segments?time_range=month",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "power_users" in data
    assert "active_users" in data
    assert "at_risk_users" in data
    assert "churned_users" in data

    # Check structure
    assert isinstance(data["power_users"]["count"], int)
    assert isinstance(data["power_users"]["users"], list)


def test_cost_prediction(client, admin_headers, db_session):
    """Test cost-prediction endpoint returns forecast"""
    response = client.get(
        "/api/v1/admin/dashboard/cost-prediction?time_range=month",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "current_month_cost" in data
    assert "predicted_month_cost" in data
    assert "days_elapsed" in data
    assert "days_remaining" in data
    assert "growth_pct" in data


def test_cost_per_user_requires_admin(client, counselor_headers):
    """Test cost-per-user requires admin role"""
    response = client.get(
        "/api/v1/admin/dashboard/cost-per-user?time_range=month",
        headers=counselor_headers
    )
    assert response.status_code == 403
```

**Run Tests**:
```bash
poetry run pytest tests/integration/test_dashboard_v2.py -v
```

---

### Phase 2: Frontend Development (Week 1-2)

#### Step 2.1: Create New Dashboard Template

**File**: `app/templates/admin_dashboard_v2.html`

**Status**: ✅ Already created

**Key Components**:
1. **Cost Control Center**:
   - Cost prediction cards
   - Cost anomaly table
   - Cost trend chart
2. **User Health Dashboard**:
   - Segmentation cards (Power/Active/At-Risk/Churned)
   - Segment detail table with filters
3. **Operational Efficiency**:
   - Summary metrics
   - Cost breakdown by service

---

#### Step 2.2: Add Route for New Dashboard

**File**: `app/main.py`

**Add Route**:
```python
from fastapi.responses import HTMLResponse

@app.get("/admin/dashboard-v2", response_class=HTMLResponse)
async def admin_dashboard_v2():
    """Serve new business-driven dashboard"""
    with open("app/templates/admin_dashboard_v2.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)
```

**Access**:
```
http://localhost:8000/admin/dashboard-v2
```

---

### Phase 3: Testing & Validation (Week 2)

#### Step 3.1: Manual Testing Checklist

**Test Scenarios**:

1. **Cost Prediction**:
   - [ ] Verify "本月累計成本" shows current month total
   - [ ] Verify "本月預測成本" shows realistic forecast
   - [ ] Verify "成本警告" shows count of anomalous users
   - [ ] Verify growth percentage is correct (compare with last month)

2. **Cost Anomaly Table**:
   - [ ] Verify users are sorted by cost (highest first)
   - [ ] Verify "疑似測試帳號" badge appears for users with many sessions but low cost/session
   - [ ] Verify "高成本" badge appears for users with cost > 2x platform average
   - [ ] Verify "建議行動" column shows helpful suggestions

3. **User Segmentation**:
   - [ ] Verify "Power Users" count matches top 10% by session count
   - [ ] Verify "At-Risk" users are those with 7-30 days of inactivity
   - [ ] Verify "Churned" users are those with 30+ days of inactivity
   - [ ] Verify clicking segment buttons updates the detail table

4. **Time Range Selector**:
   - [ ] Verify clicking "今天" / "過去7天" / "過去30天" reloads all data
   - [ ] Verify active button is highlighted

5. **Responsive Design**:
   - [ ] Test on desktop (1920x1080)
   - [ ] Test on tablet (768x1024)
   - [ ] Test on mobile (375x667)

---

#### Step 3.2: Performance Testing

**Objectives**:
- Ensure dashboard loads in < 3 seconds
- Ensure API responses are < 500ms

**Test Script**:
```bash
# Load test cost-per-user endpoint
ab -n 100 -c 10 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/admin/dashboard/cost-per-user?time_range=month

# Expected: 95% of requests < 500ms
```

**Optimization**:
- Add database indexes if queries are slow:
  ```sql
  CREATE INDEX idx_session_usages_counselor_created_at
    ON session_usages (counselor_id, created_at);

  CREATE INDEX idx_session_analysis_logs_counselor_analyzed_at
    ON session_analysis_logs (counselor_id, analyzed_at);
  ```

---

### Phase 4: Deployment (Week 2)

#### Step 4.1: Staging Deployment

**Branch**: `staging`

**Steps**:
1. Merge PR to `staging` branch
2. Wait for CI/CD to deploy to staging
3. Access staging dashboard: `https://career-app-api-staging-XXX.run.app/admin/dashboard-v2`
4. Run through manual testing checklist
5. Fix any bugs found

---

#### Step 4.2: Production Deployment

**Branch**: `main`

**Steps**:
1. Create PR from `staging` to `main`
2. Get approval from stakeholder (show screenshots/demo)
3. Merge PR
4. Wait for CI/CD to deploy to production
5. Monitor for errors in Cloud Logging

---

#### Step 4.3: Feature Toggle (Optional)

If you want to A/B test old vs new dashboard:

**Add Feature Flag**:
```python
# app/core/config.py
class Settings(BaseSettings):
    USE_DASHBOARD_V2: bool = False  # Default to old dashboard
```

**Update Route**:
```python
@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard():
    """Serve dashboard (v1 or v2 based on feature flag)"""
    template = "admin_dashboard_v2.html" if settings.USE_DASHBOARD_V2 else "admin_dashboard.html"
    with open(f"app/templates/{template}", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)
```

**Enable v2**:
```bash
# In .env or GitHub Secrets
USE_DASHBOARD_V2=true
```

---

## Database Schema Considerations

### Existing Indexes (Verify)

Check if these indexes exist:
```sql
-- SessionUsage indexes
SELECT indexname FROM pg_indexes
WHERE tablename = 'session_usages';

-- SessionAnalysisLog indexes
SELECT indexname FROM pg_indexes
WHERE tablename = 'session_analysis_logs';
```

### Recommended Indexes (If Missing)

```sql
-- For cost-per-user queries
CREATE INDEX IF NOT EXISTS idx_session_usages_counselor_created_at
  ON session_usages (counselor_id, created_at);

CREATE INDEX IF NOT EXISTS idx_session_usages_tenant_created_at
  ON session_usages (tenant_id, created_at);

-- For user-segments queries
CREATE INDEX IF NOT EXISTS idx_session_usages_created_at
  ON session_usages (created_at);

-- For cost analysis
CREATE INDEX IF NOT EXISTS idx_session_analysis_logs_counselor_analyzed_at
  ON session_analysis_logs (counselor_id, analyzed_at);

CREATE INDEX IF NOT EXISTS idx_session_analysis_logs_tenant_analyzed_at
  ON session_analysis_logs (tenant_id, analyzed_at);
```

**Run Migration**:
```bash
# Create migration
alembic revision -m "add dashboard v2 indexes"

# Apply
alembic upgrade head
```

---

## Monitoring & Alerts

### Key Metrics to Monitor

1. **Dashboard Load Time**:
   - Target: < 3 seconds
   - Alert if > 5 seconds

2. **API Response Time**:
   - Target: < 500ms
   - Alert if > 1000ms

3. **Error Rate**:
   - Target: < 0.1%
   - Alert if > 1%

### Cloud Logging Queries

**Slow API Requests**:
```
resource.type="cloud_run_revision"
jsonPayload.message=~"GET /api/v1/admin/dashboard"
jsonPayload.duration_ms > 1000
```

**Error Responses**:
```
resource.type="cloud_run_revision"
jsonPayload.message=~"/api/v1/admin/dashboard"
httpRequest.status >= 500
```

---

## Rollback Plan

If new dashboard has critical bugs:

1. **Immediate Rollback** (if using feature flag):
   ```bash
   # Set environment variable
   USE_DASHBOARD_V2=false

   # Redeploy
   gcloud run services update career-app-api --set-env-vars USE_DASHBOARD_V2=false
   ```

2. **Code Rollback** (if no feature flag):
   ```bash
   # Revert to previous commit
   git revert <commit-hash>
   git push origin main

   # Wait for auto-deploy
   ```

3. **Notify Users**:
   - Send email to stakeholders
   - Update status page if applicable

---

## Success Criteria

### Quantitative Metrics

1. **Time to Insight**: < 30 seconds
   - Stakeholder can answer "Which users cost the most?" in < 30s
   - Measure: Time from page load to identifying top cost user

2. **Action Rate**: > 50%
   - At least 50% of alerts result in an action (email sent, user contacted, etc.)
   - Measure: Track actions taken per alert shown

3. **Cost Savings**: 10%+ reduction
   - Dashboard helps identify and eliminate $X in waste per month
   - Measure: Track cost changes after implementing suggested actions

### Qualitative Metrics

1. **Stakeholder Satisfaction**:
   - Survey after 2 weeks of use
   - Questions:
     - "Does this dashboard help you make decisions?" (1-5 scale)
     - "How often do you use this dashboard?" (Daily/Weekly/Monthly/Never)
     - "What's missing?" (Open-ended)

2. **Usability**:
   - Observe stakeholder using dashboard
   - Note: Confusion points, questions asked, tasks completed

---

## Future Enhancements (Phase 3)

### 1. Automated Actions

**Feature**: Auto-send emails to at-risk users

**Implementation**:
```python
# app/services/user_retention.py
async def send_reengagement_email(user_email: str):
    """Send 'We miss you' email with 20% discount code"""
    # Use email_sender.py
    pass

# Cron job (daily)
async def check_and_reengage_users():
    at_risk_users = get_at_risk_users()
    for user in at_risk_users:
        await send_reengagement_email(user.email)
```

### 2. Custom Alerts

**Feature**: Slack/Email notifications when cost > threshold

**Implementation**:
```python
# app/services/cost_alerts.py
async def check_cost_threshold():
    current_cost = get_current_month_cost()
    if current_cost > ALERT_THRESHOLD:
        send_slack_message(f"⚠️ Cost alert: ${current_cost} (threshold: ${ALERT_THRESHOLD})")
```

### 3. ROI Analysis

**Feature**: Track revenue per user and calculate LTV

**Implementation**:
- Add `revenue` field to counselors table
- Calculate LTV = revenue / months_active
- Show ROI = LTV / total_cost

### 4. Predictive Churn Model

**Feature**: ML model to predict churn probability

**Implementation**:
- Train on features: sessions, last_activity, cost, duration
- Output: Churn probability (0-100%)
- Show in dashboard: "User X has 75% churn risk"

---

## Troubleshooting

### Issue: "Cost prediction shows $0"

**Cause**: No data in current month yet

**Fix**: Show message "Insufficient data for prediction (need at least 3 days)"

---

### Issue: "User segments API returns empty arrays"

**Cause**: All users are new (< 7 days old)

**Fix**: Filter only applies to users created > 7 days ago (already implemented)

---

### Issue: "Dashboard loads slowly (> 5s)"

**Cause**: Missing database indexes

**Fix**: Run index creation SQL (see "Recommended Indexes" section)

---

### Issue: "Cost anomaly table shows all users as 'normal'"

**Cause**: Not enough data variance (all users have similar cost/session)

**Fix**: This is expected in early stages. Wait for more diverse usage patterns.

---

## Appendix

### A. API Documentation

See: `docs/dashboard-redesign-product-strategy.md` for detailed API specs

### B. Design Mockups

See: `docs/dashboard-redesign-product-strategy.md` for wireframes

### C. User Research Notes

**Interview with Operations Manager (2026-02-05)**:
- "I need to know which users are wasting credits on tests"
- "I can't predict next month's invoice, makes budgeting hard"
- "Would be great to auto-email users who haven't logged in for a week"

**Key Insights**:
- Cost control is #1 priority
- Predictive analytics are highly valued
- Automation of repetitive tasks (emails) is desired

---

## Changelog

**2026-02-08 (v2.0)**:
- Initial redesign specification
- Added 3 new API endpoints
- Created new dashboard template (v2)
- Comprehensive implementation guide

---

**Next Steps**:
1. Review this guide with team
2. Create GitHub issue/ticket
3. Assign to developer
4. Start Phase 1 (Backend API)
5. Weekly sync to review progress
