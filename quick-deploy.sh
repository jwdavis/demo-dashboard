# Quick Deploy to Cloud Run
# For when you want to deploy without the interactive script

#!/bin/bash
set -e

PROJECT_ID="${PROJECT_ID:-roigcp-jwd-demos}"
REGION="${REGION:-us-central1}"

echo "Quick deploying to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

gcloud config set project "$PROJECT_ID"

gcloud builds submit \
    --config cloudbuild.yaml \
    --timeout=1200s

echo "Deployment complete!"
gcloud run services describe success-hq --region="$REGION" --format="value(status.url)"
