# GCP Billing Monitor Setup Guide

Complete setup guide for the GCP Billing Monitor system with AI analysis and email reports.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [BigQuery Billing Export Setup](#bigquery-billing-export-setup)
3. [Environment Configuration](#environment-configuration)
4. [Email Configuration](#email-configuration)
5. [IAM Permissions](#iam-permissions)
6. [Cloud Scheduler Setup](#cloud-scheduler-setup)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- GCP Project with billing enabled
- BigQuery API enabled
- Cloud Scheduler API enabled (for automated reports)
- Gmail account or SendGrid account (for email reports)
- Admin access to the GCP project

---

## BigQuery Billing Export Setup

### Step 1: Enable Billing Export to BigQuery

1. **Navigate to Billing Console**
   - Go to [GCP Console](https://console.cloud.google.com/)
   - Click on "Billing" in the navigation menu
   - Select your billing account

2. **Configure Billing Export**
   - Click "Billing export" in the left sidebar
   - Select the "BigQuery export" tab
   - Click "EDIT SETTINGS"

3. **Set Up Export Dataset**
   - **Project**: Select your GCP project (e.g., `groovy-iris-473015-h3`)
   - **Dataset**: Create or select a dataset (recommended: `billing_export`)
   - **Daily cost detail**: Enable
   - **Pricing**: Enable (optional)
   - Click "SAVE"

4. **Verify Export Setup**
   - It may take up to 48 hours for billing data to appear
   - The table will be named `gcp_billing_export_v1_<BILLING_ID>`
   - Data is partitioned by day

### Step 2: Create Dataset (If Not Exists)

```bash
# Via gcloud CLI
gcloud config set project YOUR_PROJECT_ID

bq mk --dataset \
  --location=US \
  --description="GCP Billing Export Dataset" \
  YOUR_PROJECT_ID:billing_export
```

### Step 3: Verify Data is Flowing

```bash
# Check if billing data exists
bq query --use_legacy_sql=false \
'SELECT
  DATE(usage_start_time) as usage_date,
  service.description as service,
  SUM(cost) as total_cost
FROM `YOUR_PROJECT_ID.billing_export.gcp_billing_export_*`
WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY usage_date, service
ORDER BY usage_date DESC, total_cost DESC
LIMIT 10;'
```

---

## Environment Configuration

### Step 1: Update .env File

Add the following to your `.env` file:

```bash
# GCP Billing Monitor
GCS_PROJECT=groovy-iris-473015-h3
BILLING_DATASET_ID=billing_export
BILLING_TABLE_ID=gcp_billing_export

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
FROM_EMAIL=your-email@gmail.com
BILLING_REPORT_EMAIL=dev02@example.com

# Admin API Key (for billing endpoints)
API_ADMIN_KEY=your-secure-random-string-min-32-chars

# OpenAI (required for AI analysis)
OPENAI_API_KEY=sk-your-openai-api-key
```

### Step 2: Generate Secure Admin API Key

```bash
# Generate a secure random API key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use this as your `API_ADMIN_KEY`.

---

## Email Configuration

### Option 1: Gmail SMTP (Recommended for Development)

1. **Enable 2-Step Verification**
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Enable 2-Step Verification

2. **Generate App Password**
   - Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Mail" and "Other (Custom name)"
   - Name it "GCP Billing Monitor"
   - Copy the 16-character password
   - Use this as `SMTP_PASSWORD` in your `.env`

3. **Configure Environment**
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-16-char-app-password
   FROM_EMAIL=your-email@gmail.com
   BILLING_REPORT_EMAIL=dev02@example.com
   ```

### Option 2: SendGrid (Recommended for Production)

1. **Create SendGrid Account**
   - Sign up at [SendGrid](https://sendgrid.com/)
   - Verify your sender email

2. **Create API Key**
   - Go to Settings > API Keys
   - Create API Key with "Mail Send" permission
   - Copy the API key

3. **Configure Environment**
   ```bash
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASSWORD=your-sendgrid-api-key
   FROM_EMAIL=verified-sender@yourdomain.com
   BILLING_REPORT_EMAIL=dev02@example.com
   ```

---

## IAM Permissions

### Step 1: Create Service Account (If Deploying to Cloud Run)

```bash
# Create service account
gcloud iam service-accounts create billing-monitor \
  --display-name="Billing Monitor Service Account"

# Grant BigQuery Data Viewer role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:billing-monitor@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

# Grant BigQuery Job User role (to run queries)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:billing-monitor@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

### Step 2: Required IAM Roles

The service account or user running the billing monitor needs:

- **BigQuery Data Viewer**: `roles/bigquery.dataViewer`
  - Read billing data from BigQuery
- **BigQuery Job User**: `roles/bigquery.jobUser`
  - Execute BigQuery queries

### Step 3: Local Development

For local development, authenticate with gcloud:

```bash
# Authenticate
gcloud auth application-default login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

---

## Cloud Scheduler Setup

### Step 1: Enable Cloud Scheduler API

```bash
gcloud services enable cloudscheduler.googleapis.com
```

### Step 2: Create Daily Billing Report Job

```bash
# Create scheduler job (runs daily at 9 AM UTC)
gcloud scheduler jobs create http daily-billing-report \
  --location=us-central1 \
  --schedule="0 9 * * *" \
  --uri="https://YOUR_CLOUD_RUN_URL/api/v1/billing/send-report" \
  --http-method=POST \
  --headers="X-Admin-Key=YOUR_ADMIN_KEY" \
  --description="Send daily GCP billing report via email" \
  --time-zone="Etc/UTC"
```

### Step 3: Customize Schedule

Cloud Scheduler uses cron format:

```bash
# Every day at 9 AM UTC
0 9 * * *

# Every weekday at 9 AM UTC
0 9 * * 1-5

# Every Monday at 9 AM UTC (weekly report)
0 9 * * 1

# First day of month at 9 AM UTC (monthly report)
0 9 1 * *
```

### Step 4: Test Scheduler Job

```bash
# Manually trigger the job
gcloud scheduler jobs run daily-billing-report --location=us-central1

# View job logs
gcloud scheduler jobs describe daily-billing-report --location=us-central1
```

---

## Testing

### Step 1: Install Dependencies

```bash
# Install new dependency
poetry install
```

### Step 2: Test API Endpoints

#### Get Billing Report (No Email)

```bash
curl -X GET "http://localhost:8000/api/v1/billing/report" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

#### Get Raw Cost Data

```bash
curl -X GET "http://localhost:8000/api/v1/billing/costs/7days" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

#### Send Billing Report Email

```bash
curl -X POST "http://localhost:8000/api/v1/billing/send-report" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

#### Send to Custom Email

```bash
curl -X POST "http://localhost:8000/api/v1/billing/send-report?to_email=custom@example.com" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY"
```

### Step 3: Test via Swagger UI

1. Start the server: `poetry run uvicorn app.main:app --reload`
2. Open browser: `http://localhost:8000/docs`
3. Navigate to "billing" section
4. Click "Authorize" and enter your `API_ADMIN_KEY`
5. Test endpoints

### Step 4: Verify Email Delivery

1. Send a test report
2. Check recipient email inbox
3. Verify HTML formatting is correct
4. Check spam folder if not received

---

## API Endpoints

### GET `/api/v1/billing/report`

Generate and return latest billing report (JSON).

**Headers:**
- `X-Admin-Key`: Admin API key

**Response:**
```json
{
  "report_date": "2025-11-30T10:00:00",
  "summary": {
    "total_cost": 123.45,
    "avg_daily": 17.64,
    "services_count": 15,
    "currency": "USD",
    "date_range": {
      "start": "2025-11-23",
      "end": "2025-11-30"
    }
  },
  "cost_data": [...],
  "ai_insights": {
    "analysis_text": "...",
    "generated_at": "2025-11-30T10:00:00",
    "data_points": 100
  }
}
```

### POST `/api/v1/billing/send-report`

Generate report and send via email.

**Headers:**
- `X-Admin-Key`: Admin API key

**Query Parameters:**
- `to_email` (optional): Recipient email

**Response:**
```json
{
  "status": "success",
  "message": "Billing report sent successfully",
  "to_email": "dev02@example.com",
  "summary": {
    "total_cost": 123.45,
    "currency": "USD",
    "date_range": {...}
  }
}
```

### GET `/api/v1/billing/costs/7days`

Get raw cost data for last 7 days.

**Headers:**
- `X-Admin-Key`: Admin API key

**Response:**
```json
{
  "summary": {...},
  "data": [...],
  "count": 100
}
```

---

## Troubleshooting

### Issue: "No billing data found"

**Causes:**
- Billing export not configured
- Data hasn't started flowing yet (wait 48 hours)
- Wrong dataset or table name
- No costs incurred in last 7 days

**Solutions:**
1. Verify billing export is enabled in GCP Console
2. Check dataset and table names in `.env`
3. Run manual BigQuery query to verify data exists
4. Extend date range in query if needed

### Issue: "Email not sending"

**Causes:**
- SMTP credentials incorrect
- App password not generated (for Gmail)
- Firewall blocking port 587
- SendGrid API key invalid

**Solutions:**
1. Test SMTP credentials with a simple email client
2. Regenerate Gmail app password
3. Check firewall/network settings
4. Verify SendGrid sender email is verified
5. Check application logs for detailed error messages

### Issue: "BigQuery permission denied"

**Causes:**
- Service account lacks permissions
- Not authenticated locally
- Wrong project ID

**Solutions:**
1. Grant `roles/bigquery.dataViewer` and `roles/bigquery.jobUser`
2. Run `gcloud auth application-default login`
3. Verify `GCS_PROJECT` in `.env` matches your GCP project

### Issue: "OpenAI API error"

**Causes:**
- API key not set
- API key invalid
- Rate limit exceeded
- Insufficient quota

**Solutions:**
1. Verify `OPENAI_API_KEY` is set correctly
2. Check API key is valid at [OpenAI Platform](https://platform.openai.com/api-keys)
3. Wait and retry if rate limited
4. Add billing to OpenAI account

### Issue: "Scheduler job fails"

**Causes:**
- Wrong Cloud Run URL
- Admin key incorrect
- Service not deployed
- Network connectivity

**Solutions:**
1. Verify Cloud Run URL is correct
2. Check admin key matches in scheduler and `.env`
3. Ensure service is deployed and running
4. Test endpoint manually with curl first

---

## Advanced Configuration

### Custom BigQuery Query

Edit `/app/services/billing_analyzer.py` to customize the cost query:

```python
async def get_7_day_cost_trend(self) -> List[Dict[str, Any]]:
    query = f"""
    -- Custom query here
    SELECT ...
    FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
    WHERE ...
    """
```

### Custom Email Template

Edit `/app/services/email_sender.py` to customize HTML template:

```python
def _generate_html_body(self, report_data: Dict[str, Any]) -> str:
    # Customize HTML here
    html = """..."""
    return html
```

### Custom AI Analysis Prompt

Edit `/app/services/billing_analyzer.py` to customize the AI analysis:

```python
async def analyze_with_ai(self, cost_data: List[Dict], summary: Dict) -> Dict[str, Any]:
    prompt = f"""
    Custom analysis prompt here...
    """
```

---

## Deployment Checklist

- [ ] BigQuery billing export configured
- [ ] Environment variables set in `.env`
- [ ] Admin API key generated and secured
- [ ] Gmail app password or SendGrid API key configured
- [ ] IAM permissions granted to service account
- [ ] Dependencies installed (`poetry install`)
- [ ] API endpoints tested locally
- [ ] Email delivery tested and verified
- [ ] Service deployed to Cloud Run
- [ ] Cloud Scheduler job created
- [ ] Scheduler job tested manually
- [ ] First automated report received

---

## Security Best Practices

1. **Protect Admin API Key**
   - Store in Secret Manager (production)
   - Never commit to git
   - Rotate regularly

2. **Email Credentials**
   - Use app passwords, not account passwords
   - Store in Secret Manager (production)
   - Enable 2FA on email account

3. **IAM Permissions**
   - Follow principle of least privilege
   - Use separate service account for billing monitor
   - Regularly audit permissions

4. **Network Security**
   - Use HTTPS only
   - Restrict Cloud Run ingress to Cloud Scheduler
   - Enable VPC connector if needed

---

## Cost Optimization

The billing monitor itself incurs minimal costs:

- **BigQuery**: ~$0.01/day (query costs)
- **Cloud Scheduler**: ~$0.10/month
- **Cloud Run**: ~$0.01/day (minimal traffic)
- **OpenAI API**: ~$0.02/report (GPT-4 mini)

**Total estimated cost**: ~$1-2/month

---

## Support

For issues or questions:

1. Check troubleshooting section
2. Review application logs
3. Test each component individually
4. Verify all environment variables are set

---

**Last Updated**: 2025-11-30
