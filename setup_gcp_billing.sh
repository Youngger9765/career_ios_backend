#!/bin/bash
# GCP Billing Monitor - Setup Script
# Run this script to configure BigQuery billing export and Cloud Scheduler

set -e  # Exit on error

# Configuration
PROJECT_ID="groovy-iris-473015-h3"
BILLING_ACCOUNT_ID="012E4D-01ACF3-0FF7FC"  # 从 GCP Console 获取
DATASET_ID="billing_export"
SERVICE_ACCOUNT="billing-monitor@${PROJECT_ID}.iam.gserviceaccount.com"
REGION="us-central1"
ADMIN_API_KEY="0iaiIHuIbnqwiEOKINaZKUzpykAbtnLJjdZpFyeSU_Q"

echo "================================================"
echo "GCP Billing Monitor Setup"
echo "Project: $PROJECT_ID"
echo "================================================"

# 1. Set active project
echo ""
echo "Step 1: Setting active GCP project..."
gcloud config set project $PROJECT_ID

# 2. Enable required APIs
echo ""
echo "Step 2: Enabling required APIs..."
gcloud services enable bigquery.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable run.googleapis.com

# 3. Check if billing export is already configured
echo ""
echo "Step 3: Checking BigQuery billing export..."
echo "⚠️  IMPORTANT: BigQuery billing export must be configured in GCP Console:"
echo "   1. Go to: https://console.cloud.google.com/billing/${BILLING_ACCOUNT_ID}"
echo "   2. Click 'Billing export' → 'BigQuery export'"
echo "   3. Edit 'Detailed usage cost' export"
echo "   4. Select dataset: ${DATASET_ID}"
echo "   5. Table will be auto-created as: gcp_billing_export_resource_v1_*"
echo ""
echo "Press Enter after configuring billing export in Console..."
read -r

# 4. Verify billing data exists
echo ""
echo "Step 4: Verifying billing data in BigQuery..."
bq query --use_legacy_sql=false \
"SELECT COUNT(*) as row_count
FROM \`${PROJECT_ID}.${DATASET_ID}.gcp_billing_export_*\`
WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY);" || {
    echo "⚠️  Warning: No billing data found. Wait 48 hours after enabling export."
    echo "Continuing setup anyway..."
}

# 5. Create service account (if not exists)
echo ""
echo "Step 5: Creating service account for billing monitor..."
if gcloud iam service-accounts describe $SERVICE_ACCOUNT 2>/dev/null; then
    echo "Service account already exists: $SERVICE_ACCOUNT"
else
    gcloud iam service-accounts create billing-monitor \
        --display-name="Billing Monitor Service Account" \
        --description="Service account for GCP billing monitor with BigQuery access"
fi

# 6. Grant BigQuery permissions
echo ""
echo "Step 6: Granting BigQuery permissions to service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/bigquery.dataViewer" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/bigquery.jobUser" \
    --condition=None

# 7. Get Cloud Run URL (需要先部署)
echo ""
echo "Step 7: Checking Cloud Run service..."
CLOUD_RUN_URL=$(gcloud run services describe career-backend \
    --region=$REGION \
    --format='value(status.url)' 2>/dev/null || echo "NOT_DEPLOYED")

if [ "$CLOUD_RUN_URL" = "NOT_DEPLOYED" ]; then
    echo "⚠️  Cloud Run service not deployed yet."
    echo "Deploy first with: gcloud run deploy career-backend --source . --region $REGION"
    echo ""
    echo "After deployment, run this script again to setup Cloud Scheduler."
    exit 1
fi

echo "Cloud Run URL: $CLOUD_RUN_URL"

# 8. Create Cloud Scheduler job
echo ""
echo "Step 8: Creating Cloud Scheduler job for daily billing reports..."

# Delete existing job if present
gcloud scheduler jobs delete daily-billing-report \
    --location=$REGION \
    --quiet 2>/dev/null || true

# Create new job
gcloud scheduler jobs create http daily-billing-report \
    --location=$REGION \
    --schedule="0 9 * * *" \
    --time-zone="Asia/Taipei" \
    --uri="${CLOUD_RUN_URL}/api/v1/billing/send-report" \
    --http-method=POST \
    --headers="X-Admin-Key=${ADMIN_API_KEY}" \
    --description="Send daily GCP billing report via email at 9 AM Taiwan time" \
    --attempt-deadline=300s \
    --max-retry-attempts=3

echo ""
echo "================================================"
echo "✅ Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Update SMTP credentials in .env file:"
echo "   - SMTP_USER=your-gmail@gmail.com"
echo "   - SMTP_PASSWORD=your-16-char-app-password"
echo "   - BILLING_REPORT_EMAIL=dev02@example.com"
echo ""
echo "2. Generate Gmail App Password:"
echo "   https://myaccount.google.com/apppasswords"
echo ""
echo "3. Test locally:"
echo "   poetry run uvicorn app.main:app --reload"
echo "   curl -X POST http://localhost:8000/api/v1/billing/send-report \\"
echo "     -H 'X-Admin-Key: ${ADMIN_API_KEY}'"
echo ""
echo "4. Manual trigger Cloud Scheduler:"
echo "   gcloud scheduler jobs run daily-billing-report --location=$REGION"
echo ""
echo "================================================"
