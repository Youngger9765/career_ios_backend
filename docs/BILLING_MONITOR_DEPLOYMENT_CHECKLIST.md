# GCP Billing Monitor - Deployment Checklist

Use this checklist to deploy the GCP Billing Monitor system.

## Pre-Deployment

### 1. BigQuery Setup
- [ ] BigQuery API enabled in GCP project
- [ ] Billing export configured in GCP Console
- [ ] Dataset `billing_export` created
- [ ] Table `gcp_billing_export_*` exists
- [ ] Verified data is flowing (wait 48 hours after setup)
- [ ] Test query runs successfully

**Verify:**
```bash
bq query --use_legacy_sql=false \
'SELECT COUNT(*) as row_count
FROM `YOUR_PROJECT_ID.billing_export.gcp_billing_export_*`
WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY);'
```

### 2. Environment Configuration
- [ ] `.env` file created (copied from `.env.example`)
- [ ] `GCS_PROJECT` set to your GCP project ID
- [ ] `BILLING_DATASET_ID` configured (default: `billing_export`)
- [ ] `BILLING_TABLE_ID` configured (default: `gcp_billing_export`)
- [ ] `OPENAI_API_KEY` set and verified
- [ ] `API_ADMIN_KEY` generated (32+ chars, random)

**Generate Admin Key:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Email Configuration

#### Option A: Gmail
- [ ] Gmail account created/selected
- [ ] 2-Step Verification enabled
- [ ] App Password generated
- [ ] `SMTP_USER` set to Gmail address
- [ ] `SMTP_PASSWORD` set to 16-char app password
- [ ] `FROM_EMAIL` set (defaults to SMTP_USER)
- [ ] `BILLING_REPORT_EMAIL` set to recipient

#### Option B: SendGrid
- [ ] SendGrid account created
- [ ] Sender email verified
- [ ] API key generated
- [ ] `SMTP_HOST` set to `smtp.sendgrid.net`
- [ ] `SMTP_USER` set to `apikey`
- [ ] `SMTP_PASSWORD` set to SendGrid API key
- [ ] `FROM_EMAIL` set to verified sender
- [ ] `BILLING_REPORT_EMAIL` set to recipient

### 4. Dependencies
- [ ] `google-cloud-bigquery` added to `pyproject.toml`
- [ ] Dependencies installed: `poetry install`
- [ ] All imports working: `poetry run python -c "from app.services.billing_analyzer import billing_analyzer"`

### 5. IAM Permissions (Local Development)
- [ ] gcloud CLI installed
- [ ] Authenticated: `gcloud auth application-default login`
- [ ] Project set: `gcloud config set project YOUR_PROJECT_ID`
- [ ] User has `roles/bigquery.dataViewer`
- [ ] User has `roles/bigquery.jobUser`

**Verify:**
```bash
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:YOUR_EMAIL"
```

## Local Testing

### 6. API Testing
- [ ] Server starts: `poetry run uvicorn app.main:app --reload`
- [ ] Health check works: `curl http://localhost:8000/health`
- [ ] Swagger UI loads: `http://localhost:8000/docs`
- [ ] Billing routes visible in Swagger

### 7. Endpoint Testing

#### Test Report Generation
```bash
curl -X GET "http://localhost:8000/api/v1/billing/report" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  | jq .
```

- [ ] Returns 200 status
- [ ] JSON response has `summary`, `cost_data`, `ai_insights`
- [ ] `summary.total_cost` is a number
- [ ] `cost_data` is an array
- [ ] `ai_insights.analysis_text` contains analysis

#### Test Raw Cost Data
```bash
curl -X GET "http://localhost:8000/api/v1/billing/costs/7days" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  | jq .
```

- [ ] Returns 200 status
- [ ] `data` array contains cost records
- [ ] `summary` object present

#### Test Email Sending
```bash
curl -X POST "http://localhost:8000/api/v1/billing/send-report" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

- [ ] Returns 200 status
- [ ] Response shows `"status": "success"`
- [ ] Email received in inbox
- [ ] HTML formatting looks correct
- [ ] AI insights section present

### 8. Security Testing
- [ ] Test without API key (should get 403)
- [ ] Test with wrong API key (should get 403)
- [ ] Test with correct API key (should work)

```bash
# Should fail
curl -X GET "http://localhost:8000/api/v1/billing/report"

# Should fail
curl -X GET "http://localhost:8000/api/v1/billing/report" \
  -H "X-Admin-Key: wrong-key"

# Should succeed
curl -X GET "http://localhost:8000/api/v1/billing/report" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

### 9. Code Quality
- [ ] Ruff check passes: `poetry run ruff check app/`
- [ ] Format applied: `poetry run ruff check --fix app/`
- [ ] No obvious errors in logs

## Cloud Deployment

### 10. Service Account Setup (Production)
- [ ] Service account created: `billing-monitor@PROJECT_ID.iam.gserviceaccount.com`
- [ ] `roles/bigquery.dataViewer` granted to service account
- [ ] `roles/bigquery.jobUser` granted to service account
- [ ] Key file generated (if needed for local testing)

**Create Service Account:**
```bash
gcloud iam service-accounts create billing-monitor \
  --display-name="Billing Monitor Service Account"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:billing-monitor@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:billing-monitor@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

### 11. Secret Manager (Recommended)
- [ ] Secret Manager API enabled
- [ ] Secrets created:
  - [ ] `OPENAI_API_KEY`
  - [ ] `API_ADMIN_KEY`
  - [ ] `SMTP_PASSWORD`
- [ ] Service account has `roles/secretmanager.secretAccessor`

**Create Secrets:**
```bash
echo -n "YOUR_OPENAI_KEY" | \
  gcloud secrets create openai-api-key --data-file=-

echo -n "YOUR_ADMIN_KEY" | \
  gcloud secrets create billing-admin-key --data-file=-

echo -n "YOUR_SMTP_PASSWORD" | \
  gcloud secrets create smtp-password --data-file=-
```

### 12. Cloud Run Deployment
- [ ] `Dockerfile` exists or using buildpack
- [ ] Environment variables configured
- [ ] Service account attached
- [ ] Region selected (e.g., `us-central1`)
- [ ] Min instances set (0 for cost savings)
- [ ] Max instances set (e.g., 10)
- [ ] Memory allocated (512MB+)
- [ ] Timeout set (300s for long queries)

**Deploy:**
```bash
gcloud run deploy career-backend \
  --source . \
  --region us-central1 \
  --service-account billing-monitor@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars "GCS_PROJECT=YOUR_PROJECT_ID,BILLING_DATASET_ID=billing_export,BILLING_TABLE_ID=gcp_billing_export,SMTP_HOST=smtp.gmail.com,SMTP_PORT=587,SMTP_USER=your-email@gmail.com,FROM_EMAIL=your-email@gmail.com,BILLING_REPORT_EMAIL=dev02@example.com" \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,API_ADMIN_KEY=billing-admin-key:latest,SMTP_PASSWORD=smtp-password:latest" \
  --memory 512Mi \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 10 \
  --allow-unauthenticated
```

- [ ] Deployment successful
- [ ] Service URL obtained
- [ ] Health check endpoint works: `https://YOUR_URL/health`

### 13. Cloud Scheduler Setup
- [ ] Cloud Scheduler API enabled
- [ ] Region configured (same as Cloud Run)
- [ ] Job created with correct schedule
- [ ] Headers include `X-Admin-Key`
- [ ] HTTP method set to POST
- [ ] Retry configuration set

**Create Job:**
```bash
gcloud scheduler jobs create http daily-billing-report \
  --location=us-central1 \
  --schedule="0 9 * * *" \
  --uri="https://YOUR_CLOUD_RUN_URL/api/v1/billing/send-report" \
  --http-method=POST \
  --headers="X-Admin-Key=YOUR_ADMIN_KEY" \
  --description="Send daily GCP billing report via email" \
  --time-zone="Etc/UTC" \
  --attempt-deadline=300s \
  --max-retry-attempts=3
```

- [ ] Job created successfully
- [ ] Manual trigger works: `gcloud scheduler jobs run daily-billing-report --location=us-central1`
- [ ] Email received from manual trigger
- [ ] Schedule verified in GCP Console

### 14. Post-Deployment Testing
- [ ] Test all endpoints via Cloud Run URL
- [ ] Verify email delivery
- [ ] Check Cloud Run logs for errors
- [ ] Monitor first scheduled run
- [ ] Verify costs are reasonable

**Test Production Endpoints:**
```bash
CLOUD_RUN_URL="https://YOUR_CLOUD_RUN_URL"
ADMIN_KEY="YOUR_ADMIN_KEY"

# Test report
curl -X GET "$CLOUD_RUN_URL/api/v1/billing/report" \
  -H "X-Admin-Key: $ADMIN_KEY"

# Test email
curl -X POST "$CLOUD_RUN_URL/api/v1/billing/send-report" \
  -H "X-Admin-Key: $ADMIN_KEY"
```

## Monitoring & Maintenance

### 15. Logging
- [ ] Cloud Logging enabled
- [ ] Log-based alerts configured
- [ ] Log retention policy set

**View Logs:**
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=career-backend" \
  --limit 50 \
  --format json
```

### 16. Monitoring
- [ ] Cloud Monitoring enabled
- [ ] Dashboard created for billing monitor
- [ ] Uptime checks configured
- [ ] Error rate alerts set

**Metrics to Monitor:**
- Request latency
- Error rate (5xx errors)
- Memory usage
- BigQuery query costs

### 17. Cost Monitoring
- [ ] Billing budget set for project
- [ ] Budget alerts configured
- [ ] Cost breakdown reviewed

**Expected Costs:**
- BigQuery: ~$0.01/day
- Cloud Run: ~$0.01/day
- Cloud Scheduler: ~$0.10/month
- OpenAI API: ~$0.02/report
- **Total**: ~$1-2/month

### 18. Security Review
- [ ] API admin key secured
- [ ] Secrets not in git
- [ ] Service account follows least privilege
- [ ] HTTPS only
- [ ] Cloud Run ingress restricted (optional)
- [ ] VPC connector configured (optional)

## Verification

### 19. Final Checks
- [ ] First automated report received
- [ ] Email looks professional
- [ ] AI insights are relevant
- [ ] Cost data is accurate
- [ ] No errors in logs
- [ ] Cloud Scheduler shows successful run

### 20. Documentation
- [ ] Setup guide reviewed
- [ ] Team notified
- [ ] Runbook created for incidents
- [ ] Contact info for support documented

## Rollback Plan

If issues occur:

1. **Disable Scheduler:**
   ```bash
   gcloud scheduler jobs pause daily-billing-report --location=us-central1
   ```

2. **Roll back Cloud Run:**
   ```bash
   gcloud run services update-traffic career-backend \
     --to-revisions=PREVIOUS_REVISION=100 \
     --region=us-central1
   ```

3. **Debug locally:**
   - Pull latest logs
   - Test endpoints locally
   - Fix issues
   - Re-deploy

4. **Re-enable:**
   ```bash
   gcloud scheduler jobs resume daily-billing-report --location=us-central1
   ```

## Success Criteria

- [ ] Billing reports delivered daily at scheduled time
- [ ] Email formatting is professional and readable
- [ ] AI insights are accurate and actionable
- [ ] System costs < $2/month
- [ ] No errors in production logs
- [ ] Team is receiving and reviewing reports

## Next Steps

After successful deployment:

1. **Week 1**: Monitor daily reports for accuracy
2. **Week 2**: Adjust AI prompts based on feedback
3. **Month 1**: Review cost optimization suggestions
4. **Quarter 1**: Measure cost savings from recommendations

## Support

For issues:
1. Check [BILLING_MONITOR_SETUP.md](./BILLING_MONITOR_SETUP.md) troubleshooting section
2. Review Cloud Run logs
3. Test components individually
4. Verify all environment variables

---

**Deployment Date**: _____________
**Deployed By**: _____________
**Cloud Run URL**: _____________
**Scheduler Job**: daily-billing-report
**Email Recipient**: dev02@example.com

---

**Last Updated**: 2025-11-30
