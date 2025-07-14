# Demo Dashboard - Success HQ

This is a demonstration version of a dashbarod I built over time for the Customer Success team at Highfive. Every card provides data useful in answering questions we used to frame the success and next steps with a customer.

## 🎯 What It Does

**Success HQ** helps CSMs understand:

- **Device Management**: Monitor device purchases, provisioning rates, and activation status
- **Customer Analytics**: Track user engagement, activity patterns, and retention metrics  
- **Project Management**: Monitor customer projects, renewals, and trending metrics

The application combines data from multiple sources to provide a unified view of customer health and business performance, enabling proactive customer success management.

## 🏗️ Architecture

The application follows a modern Flask-based microservices architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask App     │    │  Data Layer     │
│                 │    │                 │    │                 │
│ • Bootstrap UI  │◄──►│ • Flask Views   │◄──►│ • BigQuery      │
│ • Google Charts │    │ • API Routes    │    │ • Firestore     │
│ • JavaScript    │    │ • Services      │    │ • Demo Data     │
│ • AJAX/JSON     │    │ • Utils         │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

**Flask Application (`app/`)**
- **Views** (`views/`): Web page rendering and navigation
- **API** (`api/`): RESTful endpoints for data operations
- **Services** (`services/`): Business logic and data processing
- **Utils** (`utils/`): Shared utilities, logging, and exception handling
- **Templates** (`templates/`): Jinja2 HTML templates
- **Static** (`static/`): CSS, JavaScript, and assets

**Services Layer**
- **DashboardService**: Customer metrics calculation and aggregation
- **BigQueryService**: Data warehouse operations and analytics queries
- **FirestoreService**: NoSQL document storage for application data
- **DemoDataService**: Synthetic data generation for demonstrations

## 🛠️ Technology Stack

### Backend Services
- **Flask 3.0.0**: Web framework and application server
- **Google Cloud BigQuery**: Data warehouse for analytics and event storage
- **Google Cloud Firestore**: NoSQL database for application data
- **Gunicorn**: WSGI HTTP server for production deployment
- **Structlog**: Structured logging for observability

### Frontend Technologies
- **Bootstrap 5.3**: Responsive UI framework
- **Google Charts**: Interactive data visualization
- **JavaScript ES6+**: Modern frontend functionality
- **Jinja2**: Server-side templating

### Development Tools
- **Python 3.13+**: Modern Python runtime
- **python-dotenv**: Environment configuration management
- **Google Cloud SDK**: Cloud services integration

## 📊 Data Architecture

### BigQuery Schema

**Events Dataset**
```sql
-- User Events Table
user_events:
  - timestamp: TIMESTAMP
  - type: STRING (call_started, call_ended, rating, comment, dialin, support_ticket)
  - user: STRING
  - company: STRING
  - call_duration: INTEGER
  - call_type: STRING
  - call_num_users: INTEGER
  - call_os: STRING
  - rating: INTEGER
  - comment: STRING
  - session_id: STRING
  - dialin_duration: INTEGER
  - ticket_number: STRING
  - ticket_driver: STRING

-- Company Events Table  
company_events:
  - timestamp: TIMESTAMP
  - type: STRING (purchased, provisioned)
  - company: STRING
  - purchased: INTEGER
  - provisioned: INTEGER
  - serial_number: STRING
  - box_name: STRING
```

### Firestore Collections
- **users**: User profiles and metadata
- **companies**: Customer company information
- **projects**: Customer project tracking
- **trending**: Trending metrics and analytics
- **renewals**: Renewal tracking and forecasting

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- Google Cloud Platform account
- Google Cloud SDK installed and configured
- BigQuery and Firestore APIs enabled

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd demo-dashboard
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
# Create .env file with your Google Cloud configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
BIGQUERY_DATASET=events
BIGQUERY_LOCATION=US
BIGQUERY_DESCRIPTION="Customer events data warehouse"
FIRESTORE_DATABASE=(default)
FIRESTORE_LOCATION=us-central1
LOG_LEVEL=INFO
ENV=development
PORT=8080
```

5. **Run the application**
```bash
python run.py
```

The application will be available at `http://localhost:8080`

## 🎮 Demo Usage Guide

### Initial Setup

1. **Navigate to Setup Page**
   - Visit the home page and click "Setup"

2. **Configure BigQuery**
   - Click "Set Up BigQuery" to create the events dataset and tables
   - This sets up the data warehouse for analytics

3. **Configure Firestore**
   - Click "Set Up Firestore" to initialize collections
   - This creates the application database

4. **Generate Demo Data**
   - Use the demo data generator to create sample customers and events
   - Adjust the user limit based on your needs (default: 100 users)
   - This creates realistic test data for demonstration
   - Creating a full data set will result in about 15M events records
   - There will be one year of data, ending on the day the demo data was generated

### Dashboard Features

**Customer Overview**
- See upcoming projects and renewals
- Monitor trending metrics across the platform

**Individual Customer Dashboards**
- **Device Metrics**: Track purchases, provisioning rates, and activation
- **Usage Analytics**: Monitor active users, call patterns, and engagement
- **Quality Metrics**: Analyze ratings, support tickets, and user feedback
- **Historical Trends**: View 30-day trends for all key metrics

### Sample Demo Flow

1. **Home page**
   - Discuss that projects are engagement with customer to drive adoption/outcomes
   - Discuss how CSMs might respond to renewals
   - Discuss types of trends, and why seeing them here would be useful (signals)

2. **Deep Dive Analysis**
   - Click a customer link to view its detailed dashboard
   - Walk through some/all of the cards and explain what data is being presented, what it might tell the CSM, and how they might respond

## 🚀 Deployment

### Google Cloud Run (Recommended)

#### Option 1: Interactive Deployment Script
The easiest way to deploy is using the interactive deployment script:

```bash
./deploy.sh
```

This script will:
- Prompt you for all configuration values
- Enable required Google Cloud APIs
- Build and deploy using Cloud Build
- Configure environment variables
- Provide the service URL when complete

#### Option 2: Quick Deployment
If you have environment variables set, use the quick deploy script:

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
./quick-deploy.sh
```

#### Option 3: Manual Cloud Build
For manual control over the deployment:

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com

# Deploy with custom substitutions
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions \
  _REGION=us-central1,\
  _BIGQUERY_DATASET=events,\
  _BIGQUERY_LOCATION=US,\
  _FIRESTORE_DATABASE=success-hq,\
  _FIRESTORE_LOCATION=nam7,\
  _LOG_LEVEL=INFO
```

#### Environment Variables for Cloud Run
The Cloud Build configuration automatically sets these environment variables on the Cloud Run service:

- `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID
- `BIGQUERY_DATASET`: BigQuery dataset name for events
- `BIGQUERY_LOCATION`: BigQuery location (US, EU, etc.)
- `BIGQUERY_DESCRIPTION`: Description for the BigQuery dataset
- `FIRESTORE_DATABASE`: Firestore database name
- `FIRESTORE_LOCATION`: Firestore location/region
- `LOG_LEVEL`: Application logging level
- `ENV`: Set to "production" for Cloud Run deployment

#### Required Google Cloud APIs
The deployment script automatically enables these APIs:
- Cloud Build API
- Cloud Run API
- Container Registry API
- BigQuery API
- Firestore API

#### Service Configuration
The Cloud Run service is configured with:
- **Memory**: 2Gi
- **CPU**: 2 vCPUs
- **Timeout**: 300 seconds
- **Max Instances**: 10
- **Port**: 8080
- **Public Access**: Enabled (unauthenticated)

## 📝 License

This project is intended for demonstration purposes. Please ensure compliance with your organization's data handling and privacy policies when using with real customer data.

**Success HQ** - Empowering customer success through data-driven insights and real-time analytics.