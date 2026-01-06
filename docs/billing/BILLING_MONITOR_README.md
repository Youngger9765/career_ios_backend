# GCP Billing Monitor - Implementation Summary

Complete GCP Billing Monitor system with AI analysis and automated email reports.

## Overview

This system monitors GCP costs by querying BigQuery billing data, analyzing trends with OpenAI, and sending formatted HTML email reports daily.

## Architecture

```
┌─────────────────┐
│ Cloud Scheduler │ (Daily at 9 AM)
└────────┬────────┘
         │
         v
┌─────────────────┐
│  FastAPI API    │ (/api/v1/billing/send-report)
└────────┬────────┘
         │
         v
┌─────────────────┐
│ BillingAnalyzer │ (Query BigQuery + AI Analysis)
└────────┬────────┘
         │
         v
┌─────────────────┐
│  EmailSender    │ (Send HTML Report)
└─────────────────┘
```

## Files Created/Modified

### New Files

1. **app/services/email_sender.py** (400+ lines)
   - HTML email generation with responsive design
   - SMTP/SendGrid integration
   - Top services table
   - Daily cost trend visualization
   - AI insights formatting

2. **app/api/billing_reports.py** (100+ lines)
   - `GET /api/v1/billing/report` - Return JSON report
   - `POST /api/v1/billing/send-report` - Generate and email report
   - `GET /api/v1/billing/costs/7days` - Raw cost data
   - Admin API key authentication

3. **docs/BILLING_MONITOR_SETUP.md** (700+ lines)
   - Complete setup guide
   - BigQuery billing export configuration
   - Email setup (Gmail/SendGrid)
   - IAM permissions
   - Cloud Scheduler setup
   - Testing instructions
   - Troubleshooting guide

4. **docs/BILLING_MONITOR_README.md** (This file)
   - Implementation summary
   - Quick reference

### Modified Files

1. **app/services/billing_analyzer.py**
   - Fixed: Changed from non-existent `gemini_service` to `OpenAIService`
   - Added: Environment variable configuration
   - Improved: AI prompt for better analysis

2. **app/main.py**
   - Added: Import billing_reports router
   - Added: Include billing_reports.router

3. **.env.example**
   - Added: GCP billing configuration
   - Added: Email SMTP configuration
   - Added: Admin API key

4. **pyproject.toml**
   - Added: `google-cloud-bigquery = "^3.14.0"`

## Features

### 1. BigQuery Cost Analysis
- Query last 7 days of billing data
- Aggregate costs by service and date
- Calculate percentage changes
- Handle missing data gracefully

### 2. AI-Powered Insights
- OpenAI GPT-4 analysis of cost trends
- Identifies top services and cost hotspots
- Detects anomalies (>50% increases)
- Provides optimization recommendations
- Generates action items

### 3. HTML Email Reports
- Responsive design (mobile-friendly)
- Summary statistics dashboard
- Top 10 services table with costs
- Daily trend chart (visual bars)
- AI insights in formatted section
- Professional styling

### 4. API Endpoints
- Admin-protected endpoints
- JSON and email output options
- Custom recipient support
- Error handling and logging

### 5. Automated Delivery
- Cloud Scheduler integration
- Daily reports at configurable time
- Retry logic built-in
- Cost-effective (~$1-2/month)

## Quick Start

### 1. Install Dependencies

```bash
poetry install
```

### 2. Configure Environment

Copy and update `.env`:

```bash
# GCP Billing
GCS_PROJECT=your-gcp-project-id
BILLING_DATASET_ID=billing_export
BILLING_TABLE_ID=gcp_billing_export

# Email
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
BILLING_REPORT_EMAIL=dev02@example.com

# Security
API_ADMIN_KEY=generate-secure-random-key

# OpenAI
OPENAI_API_KEY=sk-your-key
```

### 3. Test API

```bash
# Start server
poetry run uvicorn app.main:app --reload

# Test report generation
curl -X GET "http://localhost:8000/api/v1/billing/report" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"

# Send test email
curl -X POST "http://localhost:8000/api/v1/billing/send-report" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

### 4. Setup Cloud Scheduler

```bash
gcloud scheduler jobs create http daily-billing-report \
  --location=us-central1 \
  --schedule="0 9 * * *" \
  --uri="https://YOUR_CLOUD_RUN_URL/api/v1/billing/send-report" \
  --http-method=POST \
  --headers="X-Admin-Key=YOUR_ADMIN_KEY"
```

## Email Report Preview

```
┌────────────────────────────────────────┐
│  GCP Cost Report - Last 7 Days         │
├────────────────────────────────────────┤
│  Summary                               │
│  • Total Cost: $123.45 USD             │
│  • Daily Average: $17.64 USD           │
│  • Services Count: 15                  │
│  • Date Range: 2025-11-23 to 2025-11-30│
├────────────────────────────────────────┤
│  Top Services by Cost                  │
│  ┌──────────────────────────────────┐  │
│  │ # │ Service     │ Cost  │ Change │  │
│  ├───┼─────────────┼───────┼────────┤  │
│  │ 1 │ Cloud Run   │ $45.00│ +12.5% │  │
│  │ 2 │ BigQuery    │ $30.00│ -5.2%  │  │
│  │ 3 │ Cloud SQL   │ $25.00│ +8.0%  │  │
│  └──────────────────────────────────┘  │
├────────────────────────────────────────┤
│  Daily Cost Trend                      │
│  ┌──────────────────────────────────┐  │
│  │ Date       │ Cost   │ Bar        │  │
│  ├────────────┼────────┼────────────┤  │
│  │ 2025-11-30 │ $18.50 │ ████████   │  │
│  │ 2025-11-29 │ $17.20 │ ███████    │  │
│  └──────────────────────────────────┘  │
├────────────────────────────────────────┤
│  AI Insights & Recommendations         │
│                                        │
│  • Cost Trend: 上升 (+5%)              │
│  • Hotspot: Cloud Run 費用增加 12.5%   │
│  • Optimization: 考慮使用預留執行個體   │
│  • Action: 檢查 Cloud Run 自動擴展設定  │
└────────────────────────────────────────┘
```

## API Reference

### Authentication

All endpoints require admin authentication:

```bash
-H "X-Admin-Key: YOUR_ADMIN_KEY"
```

### Endpoints

#### GET /api/v1/billing/report

Generate and return full report (JSON).

**Response:**
```json
{
  "report_date": "2025-11-30T10:00:00",
  "summary": {
    "total_cost": 123.45,
    "avg_daily": 17.64,
    "services_count": 15,
    "currency": "USD"
  },
  "cost_data": [...],
  "ai_insights": {...}
}
```

#### POST /api/v1/billing/send-report

Generate report and send via email.

**Query Parameters:**
- `to_email` (optional): Custom recipient

**Response:**
```json
{
  "status": "success",
  "message": "Billing report sent successfully",
  "to_email": "dev02@example.com",
  "summary": {...}
}
```

#### GET /api/v1/billing/costs/7days

Get raw cost data.

**Response:**
```json
{
  "summary": {...},
  "data": [...],
  "count": 100
}
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GCS_PROJECT` | Yes | - | GCP project ID |
| `BILLING_DATASET_ID` | No | `billing_export` | BigQuery dataset |
| `BILLING_TABLE_ID` | No | `gcp_billing_export` | BigQuery table |
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USER` | Yes | - | SMTP username |
| `SMTP_PASSWORD` | Yes | - | SMTP password |
| `FROM_EMAIL` | No | `SMTP_USER` | From email address |
| `BILLING_REPORT_EMAIL` | No | `dev02@example.com` | Default recipient |
| `API_ADMIN_KEY` | Yes | - | Admin API key |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |

## Cost Breakdown

| Service | Usage | Cost/Month |
|---------|-------|------------|
| BigQuery Queries | ~30 queries | ~$0.30 |
| Cloud Scheduler | 1 job | ~$0.10 |
| Cloud Run | Minimal traffic | ~$0.30 |
| OpenAI API | 30 reports | ~$0.60 |
| **Total** | | **~$1.30** |

Very cost-effective monitoring solution!

## Security

- Admin API key required for all endpoints
- Store credentials in Secret Manager (production)
- Use Gmail app passwords (not account password)
- Follow least privilege for IAM permissions
- HTTPS only for API endpoints

## Troubleshooting

### No billing data found
- Wait 48 hours after configuring billing export
- Verify dataset/table names in `.env`
- Check BigQuery directly with manual query

### Email not sending
- Test SMTP credentials independently
- Check firewall allows port 587
- Verify Gmail app password is generated
- Check application logs for errors

### Permission denied
- Grant `roles/bigquery.dataViewer` to service account
- Grant `roles/bigquery.jobUser` to service account
- Run `gcloud auth application-default login` locally

See [BILLING_MONITOR_SETUP.md](./BILLING_MONITOR_SETUP.md) for detailed troubleshooting.

## Next Steps

1. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy career-backend \
     --source . \
     --region us-central1 \
     --allow-unauthenticated
   ```

2. **Setup Cloud Scheduler**
   - Create daily job at 9 AM
   - Point to deployed Cloud Run URL
   - Include admin API key in headers

3. **Configure Alerts** (Optional)
   - Add Cloud Monitoring alerts for high costs
   - Setup Slack notifications
   - Create budget alerts in GCP Console

4. **Customize Reports**
   - Modify AI prompt for specific insights
   - Adjust HTML template styling
   - Add additional cost metrics

## Support & Documentation

- **Setup Guide**: [BILLING_MONITOR_SETUP.md](./BILLING_MONITOR_SETUP.md)
- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **Code**:
  - `app/services/billing_analyzer.py`
  - `app/services/email_sender.py`
  - `app/api/billing_reports.py`

## Testing

```bash
# Test via Swagger UI
poetry run uvicorn app.main:app --reload
# Open http://localhost:8000/docs

# Test via curl
curl -X POST "http://localhost:8000/api/v1/billing/send-report" \
  -H "X-Admin-Key: YOUR_KEY"

# Check logs
tail -f logs/app.log
```

## License

Part of Career Counseling Backend API.

---

**Last Updated**: 2025-11-30
**Version**: 1.0.0
