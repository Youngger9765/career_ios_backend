# Admin Dashboard Redesign - Product Strategy

**Version**: 2.0
**Date**: 2026-02-08
**Status**: Design Phase

## Executive Summary

Redesign the Admin Dashboard from a **technical monitoring tool** to a **business decision-making platform**. Focus: **Actionable insights** that drive cost control, user retention, and resource optimization.

---

## Current State Analysis

### What We Have (Technical Dashboard)
```
Summary Cards: Total Cost | Total Sessions | Active Users
Charts:
  - Cost Breakdown by Service (ElevenLabs, Gemini Flash, Gemini Lite)
  - Cost Trend Over Time
  - Daily Session Trend
  - Daily Active Users
  - Safety Distribution
  - Top Users Table
```

### Problems
1. **No Context**: "$125.50" - Is this good or bad? Up or down?
2. **No Prediction**: Can't answer "Will we exceed budget?"
3. **No Segmentation**: Can't identify profitable vs unprofitable users
4. **No Action**: Metrics don't suggest what to do next
5. **Technical Focus**: Safety distribution ≠ business value

---

## Target User: Business Stakeholder

### Primary Persona
**Role**: Operations Manager / Finance Director
**Goals**:
- Control AI API costs (ElevenLabs STT + Gemini Flash)
- Increase user engagement and retention
- Identify revenue opportunities

### Three Core Jobs-to-be-Done

#### Job 1: Cost Control 💰
**When**: Weekly budget review
**I want to**: Quickly identify cost anomalies and waste
**So I can**: Adjust limits, optimize pricing, prevent overspending

**Pain Points**:
- Don't know which users are "unprofitable"
- Can't predict next month's bill
- Miss sudden cost spikes until too late

**Expected Actions**:
- Throttle heavy users
- Contact high-cost users to upgrade
- Shut down test accounts

---

#### Job 2: User Retention 👥
**When**: Monthly business review
**I want to**: Track engagement and identify churn risks
**So I can**: Improve product and prevent revenue loss

**Pain Points**:
- Don't know who stopped using the service
- Can't tell if users find value
- No early warning system for churn

**Expected Actions**:
- Send re-engagement emails
- Offer incentives to at-risk users
- Prioritize features that boost engagement

---

#### Job 3: Resource Optimization ⚙️
**When**: Planning capacity/budget
**I want to**: Understand usage patterns
**So I can**: Allocate resources efficiently

**Pain Points**:
- Don't know peak usage hours
- Can't tell which features are used most
- No ROI analysis for features

**Expected Actions**:
- Schedule maintenance during low-traffic hours
- Invest in high-ROI features
- Deprecate unused features

---

## Redesign Principles

### 1. Action-Oriented
Every metric must answer: **"So what? What should I do?"**

Examples:
- ❌ "Total cost: $125.50"
- ✅ "Total cost: $125.50 (+15% vs last week) ⚠️ 3 users over budget"

### 2. Comparison-Rich
Show trends, benchmarks, and changes.

Examples:
- YoY, MoM, WoW comparisons
- Budget vs actual
- User segments vs platform average

### 3. Predictive
Don't just report past, predict future.

Examples:
- "At current rate, next month = $380"
- "User X will churn in 7 days (no activity)"

### 4. Segmented
Break down by user cohorts.

Examples:
- Power Users (top 10%)
- Active Users (weekly usage)
- At-Risk Users (no activity 7+ days)
- Inactive Users (no activity 30+ days)

---

## New Dashboard Architecture

### Section 1: Cost Control Center 💰 (TOP PRIORITY)

#### 1.1 Cost Overview Cards
```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│ This Month Cost     │ Predicted (Month)   │ Cost Alerts         │
│ $125.50             │ $380                │ ⚠️ 3 users over     │
│ ↑ 15% vs last month │ Based on 7d trend   │ 🧪 1 test account   │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

#### 1.2 Cost Anomaly Table (CRITICAL)
**Purpose**: Identify users who cost more than they're worth

| Email | This Month Cost | Sessions | $/Session | Status | Action |
|-------|----------------|----------|-----------|--------|--------|
| ios-tester@xxx.com | $45.20 | 450 | $0.10 | ⚠️ Test account? | → Throttle |
| client-A@xxx.com | $30.15 | 120 | $0.25 | ⚠️ Over budget | → Contact |
| client-B@xxx.com | $15.80 | 80 | $0.20 | ✅ Normal | - |

**Metrics**:
- **Cost per Session**: Efficiency metric
- **Status**: Automated classification
- **Action**: Suggested next step

**Click Actions**:
- **⚠️ Test account?** → "Disable user" or "Set daily limit"
- **⚠️ Over budget** → "Send upgrade email" or "Show pricing modal"

#### 1.3 Cost Trend with Prediction
```
[Line Chart]
- Historical cost (solid line)
- Predicted cost (dotted line, next 7-30 days)
- Budget line (red horizontal line)
- Anomaly markers (spikes with tooltips)
```

**Interactions**:
- Hover spike → "2/5: 10 users tested at same time"
- Click data point → Show sessions that day

---

### Section 2: User Health Dashboard 👥

#### 2.1 User Engagement Cards
```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Today Active │ 7d Active    │ 30d Active   │ Churn Risk   │
│ 5 users      │ 12 users     │ 25 users     │ 3 users      │
│ 20% DAU/MAU  │ 48% WAU/MAU  │ -            │ 7d no login  │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

#### 2.2 User Segmentation Table
**Purpose**: Classify users by engagement and take targeted actions

| Segment | Count | Avg Sessions/Month | Avg Cost/User | Action |
|---------|-------|-------------------|---------------|--------|
| Power Users (Top 10%) | 3 | 50 | $25 | ✅ Upsell Premium |
| Active Users | 12 | 10 | $8 | ✅ Maintain |
| At-Risk (7d inactive) | 3 | 0 (7d) | - | ⚠️ Re-engage Email |
| Churned (30d inactive) | 10 | 0 (30d) | - | ❌ Archive |

**Auto Actions**:
- **Power Users** → Badge in app, invite to premium tier
- **At-Risk** → Auto-send "We miss you" email with 20% off code
- **Churned** → Move to "inactive" pool, free up resources

#### 2.3 User Growth Chart
```
[Area Chart: Cumulative users]
- New users (green)
- Churned users (red)
- Net growth (blue line)
```

**Insights**:
- "This month: +8 new, -2 churn, net +6"
- "Churn rate: 8% (industry avg: 5%)" ← Benchmark comparison

---

### Section 3: Operational Efficiency ⚙️

#### 3.1 Efficiency Metrics
```
┌──────────────────────┬──────────────────────┬──────────────────────┐
│ Avg Cost/Session     │ Avg Session Duration │ AI Accuracy          │
│ $0.18                │ 8.5 min              │ Safe: 95%            │
│ ↓ 5% (optimizing)    │ ↑ 2min (longer)      │ ⚠️ 5% Unsafe         │
└──────────────────────┴──────────────────────┴──────────────────────┘
```

**Interpretations**:
- **$0.18/session, down 5%** → Good: optimization working
- **8.5 min, up 2min** → Warning: users talking more (cost risk) or finding more value?
- **5% Unsafe** → Actionable: "23 sessions need manual review"

#### 3.2 Feature Usage & ROI
**Purpose**: Decide where to invest engineering time

| Feature | Usage Count | Total Cost | $/Use | ROI | Action |
|---------|------------|-----------|-------|-----|--------|
| Emotion Detection | 1,200 | $18 | $0.015 | High | ✅ Keep |
| Report Generation | 45 | $25 | $0.55 | Medium | 🤔 Review |
| Deep Analysis | 120 | $40 | $0.33 | Low | ⚠️ Deprecate? |

**ROI Calculation**:
- High: Low cost + high usage
- Low: High cost + low usage

**Actions**:
- **Deep Analysis**: "Only 120 uses but costs $40. Contact users to see if needed."

#### 3.3 Peak Hours Heatmap
```
[Heatmap: 24 hours × 7 days]
- Color intensity = usage count
- Identifies: Peak hours (need capacity)
              Low hours (maintenance window)
```

**Business Value**:
- **Peak hours** → Plan scaling
- **Low traffic hours** → Schedule deploys/maintenance

---

## Removed Content (Low Business Value)

### ❌ Safety Distribution Pie Chart
**Why Remove**: 95% safe is not actionable for business stakeholder

**Replacement**: Show **count** of unsafe sessions + link to review queue
- "5% unsafe (23 sessions) → Review now"

### ❌ Token Trend Chart (Standalone)
**Why Remove**: Tokens are technical metric, stakeholders care about cost

**Replacement**: Token data shown in "Cost per Session" table

### ❌ Model Distribution
**Why Remove**: Technical implementation detail

**Replacement**: Model costs are in "Cost Breakdown by Service"

---

## New Metrics & Calculations

### Cost per User (CPU)
```sql
SELECT
  counselor_id,
  SUM(estimated_cost_usd) as total_cost,
  COUNT(DISTINCT session_id) as sessions,
  SUM(estimated_cost_usd) / COUNT(DISTINCT session_id) as cost_per_session
FROM session_usages
WHERE created_at >= :start_date
GROUP BY counselor_id
ORDER BY total_cost DESC
```

### User Segments
```sql
-- Power Users (top 10% by session count)
WITH user_sessions AS (
  SELECT counselor_id, COUNT(*) as session_count
  FROM session_usages
  WHERE created_at >= NOW() - INTERVAL '30 days'
  GROUP BY counselor_id
)
SELECT * FROM user_sessions
WHERE session_count >= (SELECT PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY session_count) FROM user_sessions)
```

### Churn Risk (7 days no activity)
```sql
SELECT c.email, MAX(su.created_at) as last_activity
FROM counselors c
LEFT JOIN session_usages su ON c.id = su.counselor_id
GROUP BY c.id, c.email
HAVING MAX(su.created_at) < NOW() - INTERVAL '7 days'
  AND MAX(su.created_at) >= NOW() - INTERVAL '30 days' -- active in last 30d
```

### Cost Prediction (Linear Regression)
```python
# Simple: Average daily cost × days remaining
avg_daily_cost = total_cost_this_month / days_elapsed
predicted_monthly_cost = avg_daily_cost * days_in_month

# Advanced: Use exponential smoothing or ML model
```

---

## Implementation Priority

### Phase 1: Must Have (Week 1)
1. ✅ Cost per User table
2. ✅ Cost prediction card
3. ✅ User segmentation (Power/Active/At-Risk/Churned)
4. ✅ Cost anomaly alerts

### Phase 2: Should Have (Week 2)
5. ✅ Feature ROI analysis
6. ✅ Peak hours heatmap
7. ✅ User growth chart
8. ✅ Churn risk alerts

### Phase 3: Nice to Have (Week 3)
9. Auto-actions (send emails to at-risk users)
10. Custom alerts (Slack/Email when cost > $X)
11. Export business reports (PDF with insights)

---

## Success Metrics (Dashboard KPIs)

### Measure Dashboard Effectiveness
1. **Time to Insight**: How fast can stakeholder find problems? (Target: <30s)
2. **Action Rate**: % of alerts that lead to action (Target: >50%)
3. **Cost Savings**: How much saved by identifying waste? (Target: 10%+ reduction)

### Example Tracking
```
Week 1:
- Identified 3 test accounts → Throttled → Saved $120/month ✅
- Found 5 at-risk users → Sent email → 2 re-engaged ✅
- Discovered "Deep Analysis" low ROI → Deprecated → Saved $40/month ✅

Total savings: $160/month (12.8% reduction)
```

---

## Technical Architecture

### Frontend Changes
- **Framework**: Vanilla JS + Chart.js (keep existing)
- **New Components**:
  - `CostAnomalyTable.js`
  - `UserSegmentationTable.js`
  - `FeatureROITable.js`
  - `PredictionCard.js`
  - `AlertBadge.js`

### Backend Changes
- **New Endpoints**:
  - `GET /api/v1/admin/dashboard/cost-per-user` - Cost anomaly analysis
  - `GET /api/v1/admin/dashboard/user-segments` - User cohorts
  - `GET /api/v1/admin/dashboard/churn-risk` - At-risk users
  - `GET /api/v1/admin/dashboard/feature-roi` - Feature usage & ROI
  - `GET /api/v1/admin/dashboard/cost-prediction` - Next month forecast
  - `GET /api/v1/admin/dashboard/peak-hours` - Heatmap data

### Database Queries
- Optimize with indexes on `(counselor_id, created_at)`
- Add materialized view for daily aggregates (optional, if slow)

---

## Wireframe (ASCII)

```
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 AI Cost & User Dashboard                      [Day|Week|Month]│
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ 💰 COST CONTROL CENTER                                           │
│ ┌─────────────┬─────────────┬─────────────┐                      │
│ │ This Month  │ Predicted   │ Alerts      │                      │
│ │ $125.50     │ $380        │ ⚠️ 3 users  │                      │
│ │ ↑15% vs last│ (30d trend) │ 🧪 1 test   │                      │
│ └─────────────┴─────────────┴─────────────┘                      │
│                                                                   │
│ ⚠️ Cost Anomaly Users                                             │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Email           | Cost  | Sessions | $/S   | Status | Action│  │
│ │ test@x.com      | $45   | 450      | $0.10 | ⚠️ Test| Limit │  │
│ │ client-a@x.com  | $30   | 120      | $0.25 | ⚠️ High| Email │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ 📈 Cost Trend (with Prediction)                                   │
│ [Line chart: actual + predicted + budget line]                   │
│                                                                   │
│ ─────────────────────────────────────────────────────────────── │
│                                                                   │
│ 👥 USER HEALTH                                                    │
│ ┌─────────┬─────────┬─────────┬─────────┐                        │
│ │ Today   │ 7d      │ 30d     │ At-Risk │                        │
│ │ 5       │ 12      │ 25      │ 3       │                        │
│ └─────────┴─────────┴─────────┴─────────┘                        │
│                                                                   │
│ User Segments                                                     │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Segment     | Count | Sessions/M | Cost/U | Action         │  │
│ │ Power Users | 3     | 50         | $25    | ✅ Upsell      │  │
│ │ Active      | 12    | 10         | $8     | ✅ Maintain    │  │
│ │ At-Risk     | 3     | 0 (7d)     | -      | ⚠️ Re-engage  │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ ─────────────────────────────────────────────────────────────── │
│                                                                   │
│ ⚙️ OPERATIONAL EFFICIENCY                                         │
│ ┌─────────────┬─────────────┬─────────────┐                      │
│ │ $/Session   │ Avg Duration│ AI Accuracy │                      │
│ │ $0.18       │ 8.5 min     │ 95% Safe    │                      │
│ │ ↓5%         │ ↑2min       │ 5% Review   │                      │
│ └─────────────┴─────────────┴─────────────┘                      │
│                                                                   │
│ Feature ROI Analysis                                              │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ Feature      | Uses | Cost | $/Use | ROI  | Action        │  │
│ │ Emotion API  | 1200 | $18  | $0.02 | High | ✅ Keep       │  │
│ │ Deep Analyze | 120  | $40  | $0.33 | Low  | ⚠️ Review     │  │
│ └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ Peak Hours Heatmap                                                │
│ [Heatmap: 24h × 7d, color = usage intensity]                     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Next Steps

1. **Review with Stakeholder** - Validate Jobs-to-be-Done assumptions
2. **Design Iteration** - Adjust based on feedback
3. **API Development** - Implement new endpoints (Phase 1)
4. **Frontend Build** - Build new dashboard UI
5. **A/B Testing** - Compare old vs new dashboard (time to insight)
6. **Launch** - Replace old dashboard, collect feedback

---

**Remember**: Every metric must answer "So What?" and suggest an action.
The best dashboard is one that makes stakeholders feel **in control**, not overwhelmed.
