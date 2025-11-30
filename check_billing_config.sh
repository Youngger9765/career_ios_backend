#!/bin/bash
# GCP Billing Monitor - Configuration Check Script
# Run this to verify your setup is ready

set -e

PROJECT_ID="groovy-iris-473015-h3"
DATASET_ID="billing_export"

echo "================================================"
echo "GCP Billing Monitor - Configuration Check"
echo "================================================"

# Function to check status
check_status() {
    if [ $1 -eq 0 ]; then
        echo "✅ $2"
    else
        echo "❌ $2"
        echo "   Fix: $3"
    fi
}

echo ""
echo "1. Checking .env configuration..."
echo "-----------------------------------"

# Check .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found"
    exit 1
fi

# Check required variables
check_var() {
    if grep -q "^$1=" .env && ! grep -q "^$1=your-" .env && ! grep -q "^$1=.*example.com" .env; then
        echo "✅ $1 is configured"
        return 0
    else
        echo "⚠️  $1 needs configuration"
        echo "   Current: $(grep "^$1=" .env || echo 'NOT SET')"
        return 1
    fi
}

check_var "GCS_PROJECT"
check_var "API_ADMIN_KEY"

# Check SMTP (warning only)
if grep -q "^SMTP_USER=your-gmail" .env; then
    echo "⚠️  SMTP_USER needs real Gmail address"
else
    echo "✅ SMTP_USER is set"
fi

if grep -q "^SMTP_PASSWORD=your-16" .env; then
    echo "⚠️  SMTP_PASSWORD needs Gmail App Password"
else
    echo "✅ SMTP_PASSWORD is set"
fi

echo ""
echo "2. Checking GCP authentication..."
echo "-----------------------------------"

# Check gcloud auth
if gcloud auth list --filter=status:ACTIVE --format="value(account)" &>/dev/null; then
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
    echo "✅ Logged in as: $ACTIVE_ACCOUNT"
else
    echo "❌ Not logged in to gcloud"
    echo "   Fix: gcloud auth login"
    exit 1
fi

# Check active project
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ "$CURRENT_PROJECT" = "$PROJECT_ID" ]; then
    echo "✅ Active project: $PROJECT_ID"
else
    echo "⚠️  Active project: $CURRENT_PROJECT (expected: $PROJECT_ID)"
    echo "   Fix: gcloud config set project $PROJECT_ID"
fi

echo ""
echo "3. Checking GCP APIs..."
echo "-----------------------------------"

check_api() {
    if gcloud services list --enabled --filter="name:$1" --format="value(name)" 2>/dev/null | grep -q "$1"; then
        echo "✅ $2 API enabled"
        return 0
    else
        echo "❌ $2 API not enabled"
        echo "   Fix: gcloud services enable $1"
        return 1
    fi
}

check_api "bigquery.googleapis.com" "BigQuery"
check_api "cloudscheduler.googleapis.com" "Cloud Scheduler"
check_api "run.googleapis.com" "Cloud Run"

echo ""
echo "4. Checking BigQuery billing export..."
echo "-----------------------------------"

# Check if dataset exists
if bq ls -d $PROJECT_ID:$DATASET_ID &>/dev/null; then
    echo "✅ Dataset exists: $DATASET_ID"

    # Check for billing table
    TABLE_COUNT=$(bq ls -n 1000 $PROJECT_ID:$DATASET_ID | grep -c "gcp_billing_export" || echo "0")
    if [ "$TABLE_COUNT" -gt 0 ]; then
        echo "✅ Billing export table found"

        # Check if data exists
        ROW_COUNT=$(bq query --use_legacy_sql=false \
            "SELECT COUNT(*) as cnt FROM \`${PROJECT_ID}.${DATASET_ID}.gcp_billing_export_*\` LIMIT 1" \
            --format=csv --quiet 2>/dev/null | tail -1 || echo "0")

        if [ "$ROW_COUNT" -gt 0 ]; then
            echo "✅ Billing data found: $ROW_COUNT rows"
        else
            echo "⚠️  No billing data yet (wait 24-48 hours after enabling export)"
        fi
    else
        echo "⚠️  No billing export table found"
        echo "   Fix: Configure in GCP Console → Billing → Billing export → BigQuery export"
    fi
else
    echo "⚠️  Dataset not found: $DATASET_ID"
    echo "   Fix: Configure billing export in GCP Console (dataset will auto-create)"
fi

echo ""
echo "5. Checking service account..."
echo "-----------------------------------"

SERVICE_ACCOUNT="billing-monitor@${PROJECT_ID}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $SERVICE_ACCOUNT &>/dev/null; then
    echo "✅ Service account exists: billing-monitor"

    # Check permissions
    ROLES=$(gcloud projects get-iam-policy $PROJECT_ID \
        --flatten="bindings[].members" \
        --filter="bindings.members:serviceAccount:$SERVICE_ACCOUNT" \
        --format="value(bindings.role)" 2>/dev/null)

    if echo "$ROLES" | grep -q "bigquery.dataViewer"; then
        echo "✅ Has bigquery.dataViewer role"
    else
        echo "❌ Missing bigquery.dataViewer role"
    fi

    if echo "$ROLES" | grep -q "bigquery.jobUser"; then
        echo "✅ Has bigquery.jobUser role"
    else
        echo "❌ Missing bigquery.jobUser role"
    fi
else
    echo "⚠️  Service account not created yet"
    echo "   Fix: Run ./setup_gcp_billing.sh"
fi

echo ""
echo "6. Checking Cloud Run deployment..."
echo "-----------------------------------"

CLOUD_RUN_URL=$(gcloud run services describe career-backend \
    --region=us-central1 \
    --format='value(status.url)' 2>/dev/null || echo "")

if [ -n "$CLOUD_RUN_URL" ]; then
    echo "✅ Cloud Run deployed: $CLOUD_RUN_URL"
else
    echo "⚠️  Cloud Run not deployed yet"
    echo "   Fix: gcloud run deploy career-backend --source . --region us-central1"
fi

echo ""
echo "7. Checking Cloud Scheduler..."
echo "-----------------------------------"

if gcloud scheduler jobs describe daily-billing-report --location=us-central1 &>/dev/null; then
    echo "✅ Scheduler job exists: daily-billing-report"

    SCHEDULE=$(gcloud scheduler jobs describe daily-billing-report \
        --location=us-central1 \
        --format='value(schedule)' 2>/dev/null)
    echo "   Schedule: $SCHEDULE (Asia/Taipei)"
else
    echo "⚠️  Scheduler job not created yet"
    echo "   Fix: Run ./setup_gcp_billing.sh (after Cloud Run deployment)"
fi

echo ""
echo "8. Checking Python dependencies..."
echo "-----------------------------------"

if poetry run python -c "from app.services.billing_analyzer import billing_analyzer; from app.services.email_sender import email_sender" 2>/dev/null; then
    echo "✅ All billing modules import successfully"
else
    echo "❌ Import error"
    echo "   Fix: poetry install"
fi

echo ""
echo "================================================"
echo "Configuration Summary"
echo "================================================"
echo ""
echo "Ready to test locally:"
echo "  poetry run uvicorn app.main:app --reload"
echo ""
echo "Test API:"
echo "  curl -X POST http://localhost:8000/api/v1/billing/send-report \\"
echo "    -H 'X-Admin-Key: $(grep API_ADMIN_KEY .env | cut -d= -f2)'"
echo ""
echo "Next steps:"
echo "  1. Configure SMTP in .env (if not done)"
echo "  2. Run ./setup_gcp_billing.sh (if service account/scheduler not ready)"
echo "  3. Test locally"
echo "  4. Deploy to Cloud Run"
echo ""
echo "================================================"
