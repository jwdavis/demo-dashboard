# Deployment Configuration Guide

This guide explains how to configure the Success HQ application for different deployment environments.

## Environment Variables

### Required Variables
These variables must be set for the application to function properly:

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `GOOGLE_CLOUD_PROJECT` | Your Google Cloud project ID | `my-project-123` | Yes |
| `BIGQUERY_DATASET` | BigQuery dataset name for events | `events` | Yes |
| `BIGQUERY_LOCATION` | BigQuery location | `US` or `EU` | Yes |
| `FIRESTORE_DATABASE` | Firestore database name | `success-hq` | Yes |
| `FIRESTORE_LOCATION` | Firestore location/region | `us-central1` | Yes |

### Optional Variables
| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `BIGQUERY_DESCRIPTION` | Description for BigQuery dataset | `"Events dashboard for Success-HQ"` | Any string |
| `LOG_LEVEL` | Application logging level | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ENV` | Environment type | `development` | `development`, `production` |
| `PORT` | Application port | `8080` | Any valid port number |

## Cloud Run Deployment Options

### 1. Using the Interactive Deployment Script (Recommended)

```bash
./deploy.sh
```

**Benefits:**
- Guided setup with prompts for all configuration
- Validates prerequisites and enables required APIs
- Provides clear feedback and error handling
- Shows deployment summary and service URL

**Best for:** First-time deployments, different environments

### 2. Using the Quick Deploy Script

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
./quick-deploy.sh
```

**Benefits:**
- Fast deployment with minimal interaction
- Uses default values from cloudbuild.yaml
- Good for CI/CD pipelines

**Best for:** Repeated deployments, automation

### 3. Direct Cloud Build Submission

```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions _REGION=us-central1,_BIGQUERY_DATASET=events
```

**Benefits:**
- Maximum control over build parameters
- Can override any substitution variable
- Integrates with existing Cloud Build workflows

**Best for:** Advanced users, custom configurations

## Environment-Specific Configurations

### Development Environment
```bash
# Local .env file
GOOGLE_CLOUD_PROJECT=my-dev-project
BIGQUERY_DATASET=events_dev
BIGQUERY_LOCATION=US
FIRESTORE_DATABASE=success-hq-dev
FIRESTORE_LOCATION=us-central1
LOG_LEVEL=DEBUG
ENV=development
```

### Staging Environment
```bash
# Cloud Build substitutions
_REGION=us-central1
_BIGQUERY_DATASET=events_staging
_FIRESTORE_DATABASE=success-hq-staging
_LOG_LEVEL=INFO
```

### Production Environment
```bash
# Cloud Build substitutions
_REGION=us-central1
_BIGQUERY_DATASET=events
_FIRESTORE_DATABASE=success-hq
_LOG_LEVEL=WARNING
```

## Customizing Cloud Build Configuration

You can modify the `cloudbuild.yaml` file to customize the deployment:

### Change Resource Allocation
```yaml
# In the Cloud Run deploy step, modify:
- '--memory'
- '4Gi'          # Increase memory
- '--cpu'
- '4'            # Increase CPU
```

### Change Scaling Configuration
```yaml
# Add these arguments to the gcloud run deploy step:
- '--min-instances'
- '1'            # Keep warm instances
- '--max-instances'
- '20'           # Allow more scaling
```

### Add Custom Environment Variables
```yaml
# In the --set-env-vars argument, add:
CUSTOM_VAR=${_CUSTOM_VAR},OTHER_VAR=value
```

### Use Different Regions
```yaml
substitutions:
  _REGION: europe-west1  # Change default region
```

## Security Considerations

### Service Account Permissions
Ensure your Cloud Build service account has these IAM roles:
- Cloud Run Admin
- Storage Admin (for Container Registry)
- Service Account User

### Network Security
For production deployments, consider:
- Using Cloud Run with VPC connector for private network access
- Implementing authentication/authorization
- Using HTTPS-only with custom domains

### Secrets Management
For sensitive configuration:
```bash
# Use Secret Manager instead of environment variables
gcloud secrets create app-config --data-file=config.json
```

## Monitoring and Logging

### Cloud Logging
Logs are automatically sent to Cloud Logging with the `CLOUD_LOGGING_ONLY` option.

### Cloud Monitoring
Set up monitoring for:
- Request latency
- Error rates
- Memory/CPU usage
- Custom application metrics

### Health Checks
The application includes basic health check endpoints that Cloud Run uses automatically.

## Troubleshooting

### Common Issues

1. **Build Timeout**
   - Increase timeout in cloudbuild.yaml: `timeout: 1800s`

2. **Memory Issues**
   - Increase memory allocation: `--memory 4Gi`

3. **API Not Enabled**
   - Run: `gcloud services enable [api-name]`

4. **Permission Denied**
   - Check IAM roles for Cloud Build service account

5. **Environment Variables Not Set**
   - Verify substitution variables in cloudbuild.yaml
   - Check the deployed service environment variables:
     ```bash
     gcloud run services describe success-hq --region=us-central1
     ```

### Getting Service Information
```bash
# Get service URL
gcloud run services describe success-hq --region=us-central1 --format="value(status.url)"

# Get service configuration
gcloud run services describe success-hq --region=us-central1

# View logs
gcloud logs read --service=success-hq --limit=50
```
