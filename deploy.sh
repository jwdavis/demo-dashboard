#!/bin/bash

# Success HQ - Cloud Run Deployment Script
# This script deploys the Success HQ application to Google Cloud Run

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DEFAULT_PROJECT_ID="roigcp-jwd-demos"
DEFAULT_REGION="us-central1"
DEFAULT_SERVICE_NAME="success-hq"
DEFAULT_BIGQUERY_DATASET="events"
DEFAULT_BIGQUERY_LOCATION="US"
DEFAULT_FIRESTORE_DATABASE="success-hq"
DEFAULT_FIRESTORE_LOCATION="nam7"
DEFAULT_LOG_LEVEL="INFO"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to prompt for input with default value
prompt_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    echo -n "$prompt [$default]: "
    read input
    if [ -z "$input" ]; then
        eval "$var_name=\"$default\""
    else
        eval "$var_name=\"$input\""
    fi
}

echo "=============================================="
echo "   Success HQ - Cloud Run Deployment"
echo "=============================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first:"
    print_error "https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_error "No active gcloud authentication found. Please run:"
    print_error "gcloud auth login"
    exit 1
fi

print_status "Collecting deployment configuration..."
echo ""

# Collect configuration
prompt_with_default "Google Cloud Project ID" "$DEFAULT_PROJECT_ID" "PROJECT_ID"
prompt_with_default "Deployment Region" "$DEFAULT_REGION" "REGION"
prompt_with_default "Cloud Run Service Name" "$DEFAULT_SERVICE_NAME" "SERVICE_NAME"
prompt_with_default "BigQuery Dataset" "$DEFAULT_BIGQUERY_DATASET" "BIGQUERY_DATASET"
prompt_with_default "BigQuery Location" "$DEFAULT_BIGQUERY_LOCATION" "BIGQUERY_LOCATION"
prompt_with_default "Firestore Database" "$DEFAULT_FIRESTORE_DATABASE" "FIRESTORE_DATABASE"
prompt_with_default "Firestore Location" "$DEFAULT_FIRESTORE_LOCATION" "FIRESTORE_LOCATION"
prompt_with_default "Log Level" "$DEFAULT_LOG_LEVEL" "LOG_LEVEL"

echo ""
print_status "Configuration Summary:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo "  BigQuery Dataset: $BIGQUERY_DATASET"
echo "  BigQuery Location: $BIGQUERY_LOCATION"
echo "  Firestore Database: $FIRESTORE_DATABASE"
echo "  Firestore Location: $FIRESTORE_LOCATION"
echo "  Log Level: $LOG_LEVEL"
echo ""

# Confirm deployment
echo -n "Do you want to proceed with deployment? (y/N): "
read confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    print_warning "Deployment cancelled."
    exit 0
fi

print_status "Starting deployment process..."

# Set the project
print_status "Setting Google Cloud project to $PROJECT_ID..."
gcloud config set project "$PROJECT_ID"

# Enable required APIs
print_status "Enabling required Google Cloud APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable firestore.googleapis.com

# Submit build to Cloud Build
print_status "Starting Cloud Build deployment..."
gcloud builds submit \
    --config cloudbuild.yaml \
    --substitutions \
_REGION="$REGION",\
_BIGQUERY_DATASET="$BIGQUERY_DATASET",\
_BIGQUERY_LOCATION="$BIGQUERY_LOCATION",\
_BIGQUERY_DESCRIPTION="Events dashboard for Success-HQ",\
_FIRESTORE_DATABASE="$FIRESTORE_DATABASE",\
_FIRESTORE_LOCATION="$FIRESTORE_LOCATION",\
_LOG_LEVEL="$LOG_LEVEL" \
    --timeout=1200s

if [ $? -eq 0 ]; then
    print_success "Deployment completed successfully!"
    
    # Get the service URL
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")
    
    echo ""
    print_success "Success HQ is now available at:"
    echo "  🚀 $SERVICE_URL"
    echo ""
    print_status "Next steps:"
    echo "  1. Visit the application URL above"
    echo "  2. Go to the Setup page to configure BigQuery and Firestore"
    echo "  3. Generate demo data to populate the dashboard"
    echo "  4. Explore customer dashboards and analytics"
    echo ""
    print_warning "Note: The first request may take a few seconds as the service starts up."
else
    print_error "Deployment failed. Please check the Cloud Build logs for details."
    exit 1
fi
