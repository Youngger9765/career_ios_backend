# GCP Configuration Example

## If GCP configuration is incorrect, use gcp-config-manager:

```python
Task(
    subagent_type="gcp-config-manager",
    description="Fix GCP configuration",
    prompt="Ensure gcloud is configured with project [PROJECT_ID], account [SERVICE_ACCOUNT], region [REGION]"
)
```

## Environment Variables Template

Instead of hardcoding sensitive information, use environment variables:

```bash
# .env.example
GCP_PROJECT_ID=your-project-id
GCP_SERVICE_ACCOUNT=your-service-account
GCP_REGION=your-region
```

## Security Best Practices

1. **NEVER** commit actual project IDs, service accounts, or API keys
2. **ALWAYS** use environment variables for sensitive configuration
3. **USE** `.env.example` files with placeholder values
4. **ADD** `.env` to `.gitignore`

## Configuration Check Script

```bash
#!/bin/bash
# check-gcp-config.sh

# Load from environment
PROJECT_ID="${GCP_PROJECT_ID}"
SERVICE_ACCOUNT="${GCP_SERVICE_ACCOUNT}"
REGION="${GCP_REGION:-us-central1}"

if [[ -z "$PROJECT_ID" || -z "$SERVICE_ACCOUNT" ]]; then
    echo "❌ Missing GCP configuration environment variables"
    echo "Please set GCP_PROJECT_ID and GCP_SERVICE_ACCOUNT"
    exit 1
fi

echo "✅ GCP Configuration:"
echo "   Project: [REDACTED]"
echo "   Account: [REDACTED]"
echo "   Region: $REGION"
```

## Note on Security

This file contains EXAMPLES ONLY. Never include actual:
- Project IDs
- Service Account emails
- API Keys
- Credentials
- Any sensitive information

Always use environment variables or secure secret management systems.
