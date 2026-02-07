# Dashboard Upgrade Checklist - 2025-02-07

## Pre-Deployment Checklist

### 1. Code Review
- [ ] Review `app/core/pricing.py` (new file)
- [ ] Review service updates (emotion, quick_feedback, parents_report, session_billing)
- [ ] Review dashboard API changes (`app/api/v1/admin/dashboard.py`)
- [ ] Review dashboard HTML updates (`app/templates/admin_dashboard.html`)
- [ ] Review database fix script (`scripts/fix_emotion_model_names.py`)

### 2. Local Testing
- [ ] Run `poetry run python -c "from app.core.pricing import *"` (imports work)
- [ ] Start local server: `poetry run uvicorn app.main:app --reload`
- [ ] Test `/api/v1/admin/dashboard/summary` (no total_tokens field)
- [ ] Test `/api/v1/admin/dashboard/cost-breakdown` (new endpoint)
- [ ] Test `/api/v1/admin/dashboard/session-trend` (new endpoint)
- [ ] Test `/api/v1/admin/dashboard/model-distribution` (cost-based)
- [ ] Open dashboard in browser, check all 3 summary cards load
- [ ] Check cost breakdown section appears
- [ ] Check session trend chart shows (not token trend)

### 3. Staging Deployment

#### Backend:
- [ ] Push to `staging` branch
- [ ] Wait for CI/CD to pass
- [ ] Verify staging API responds: `curl https://career-app-api-staging-978304030758.us-central1.run.app/api/v1/admin/dashboard/cost-breakdown?time_range=day`

#### Database Fix:
- [ ] SSH to staging environment (if needed)
- [ ] Run: `poetry run python scripts/fix_emotion_model_names.py`
- [ ] Review preview, type "yes" to confirm
- [ ] Verify: Check that all emotion logs have `gemini-flash-lite-latest`

#### Frontend:
- [ ] Check dashboard on staging: https://island-parents-staging.web.app/admin/dashboard
- [ ] Login with admin account
- [ ] Verify 3 summary cards (not 4)
- [ ] Verify cost breakdown section visible
- [ ] Verify session trend chart visible (not token trend)
- [ ] Test time range filters (today, 7 days, 30 days)
- [ ] Test tenant filter (all, career, island_parents)

### 4. Production Deployment

#### Backend:
- [ ] Create PR: `staging` → `main`
- [ ] Get approval from team
- [ ] Merge PR
- [ ] Wait for CI/CD to pass
- [ ] Verify production API: `curl https://career-app-api-978304030758.us-central1.run.app/api/v1/admin/dashboard/cost-breakdown?time_range=day`

#### Database Fix (CRITICAL - User's Main Issue):
- [ ] **IMPORTANT**: Run on production DB
- [ ] `poetry run python scripts/fix_emotion_model_names.py`
- [ ] Preview changes
- [ ] Confirm with "yes"
- [ ] Verify results
- [ ] **This fixes the main issue**: All emotion analysis now correctly labeled

#### Frontend:
- [ ] Check dashboard on production: https://island-parents-app.web.app/admin/dashboard
- [ ] Verify all features work
- [ ] Notify admin users of new features

---

## Post-Deployment Verification

### Functional Tests:
- [ ] Summary shows correct cost (matches old dashboard)
- [ ] Cost breakdown shows ElevenLabs + Gemini models
- [ ] Session trend shows dual-axis chart (sessions + hours)
- [ ] Model distribution shows cost (pie chart with tooltip)
- [ ] All time ranges work (day/week/month)
- [ ] All tenant filters work
- [ ] Export CSV still works

### Performance Tests:
- [ ] Dashboard loads in <2 seconds
- [ ] All API calls respond in <200ms
- [ ] No JavaScript errors in console
- [ ] No 500 errors in server logs

### Data Validation:
- [ ] Query staging DB:
  ```sql
  SELECT model_name, COUNT(*)
  FROM session_analysis_logs
  WHERE analysis_result->>'analysis_type' = 'emotion_feedback'
  GROUP BY model_name;
  ```
- [ ] Should show: `gemini-flash-lite-latest: XXX` (all emotion logs)
- [ ] Should NOT show: `gemini-3-flash-preview` (old incorrect name)

### Business Validation:
- [ ] Admin can identify most expensive service
- [ ] Cost breakdown percentages add up to ~100%
- [ ] Session trend shows realistic numbers
- [ ] Model costs match expected values

---

## Rollback Plan (If Needed)

### If Backend Issues:
```bash
git revert <commit-hash>
git push origin staging  # or main
# Wait for CI/CD
```

### If Database Fix Issues:
```bash
poetry run python -c "
from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Rollback: restore old model_name
    conn.execute(text('''
        UPDATE session_analysis_logs
        SET model_name = 'gemini-3-flash-preview'
        WHERE model_name = 'gemini-flash-lite-latest'
          AND analysis_result->>'analysis_type' = 'emotion_feedback'
    '''))
    conn.commit()
"
```

### If Frontend Issues:
```bash
git revert <commit-hash> -- app/templates/admin_dashboard.html
git commit -m "revert: rollback dashboard UI changes"
git push origin staging  # or main
```

---

## Known Issues & Limitations

### Issue 1: Historical Costs May Not Be 100% Accurate
- **Why**: We're fixing model names in DB, but costs were calculated with wrong pricing
- **Impact**: Dashboard shows slightly different historical costs
- **Solution**: Accept this as data quality improvement going forward

### Issue 2: ElevenLabs Cost Based on Session Duration
- **Why**: We don't store exact STT usage duration, only session duration
- **Impact**: Cost may be slightly overestimated (includes pause time)
- **Solution**: Future improvement to track actual audio duration

### Issue 3: Large Time Range Queries May Be Slow
- **Why**: Aggregating 30 days of data across multiple models
- **Impact**: "Past 30 days" may take 1-2 seconds to load
- **Solution**: Add database indexes if needed (see docs)

---

## Communication Plan

### Internal Team:
- [ ] Notify team in Slack: "Dashboard upgrade deployed to staging"
- [ ] Share documentation: Link to `docs/dashboard-upgrade-2025-02-07.md`
- [ ] Demo new features in standup

### Admin Users:
- [ ] Send email: "Dashboard now shows cost breakdown by service"
- [ ] Highlight key changes:
  - "Total Tokens" removed (confusing metric)
  - "Cost Breakdown" added (see which service costs most)
  - "Session Trend" added (see daily usage patterns)

### Support Team:
- [ ] Update admin guide with new screenshots
- [ ] Add FAQ: "Where did Total Tokens go?"
- [ ] Add FAQ: "What is Cost Breakdown?"

---

## Success Criteria

✅ **Must Have** (Blocking):
1. All API endpoints return 200
2. Dashboard loads without errors
3. Cost breakdown shows correct services
4. Database fix completes successfully

✅ **Should Have** (Important):
1. Dashboard loads in <2 seconds
2. Charts render correctly
3. All time range filters work
4. Admin can identify most expensive service in <5 seconds

✅ **Nice to Have** (Optional):
1. Tooltips show detailed info
2. Animations are smooth
3. Mobile view works

---

## Sign-off

- [ ] **Developer**: Code complete and tested locally
- [ ] **QA**: Staging testing passed
- [ ] **Product Owner**: Features approved
- [ ] **DevOps**: Production deployment completed
- [ ] **Support**: Documentation updated

---

**Checklist Version**: 1.0
**Created**: 2025-02-07
**Owner**: @young
