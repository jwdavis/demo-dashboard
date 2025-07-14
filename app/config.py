import os
from google.cloud import bigquery


class AppConfig:
    """Application configuration from environment variables and constants."""

    def __init__(self):
        # Google Cloud settings
        self.project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "")

        # BigQuery settings
        self.bigquery_dataset = os.getenv("BIGQUERY_DATASET", "")
        self.bigquery_location = os.getenv("BIGQUERY_LOCATION", "")
        self.bigquery_description = os.getenv("BIGQUERY_DESCRIPTION", "")

        # Firestore settings
        self.firestore_database = os.getenv("FIRESTORE_DATABASE", "")
        self.firestore_location = os.getenv("FIRESTORE_LOCATION", "")

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "")

        # BigQuery table schemas
        self.table_schemas = {
            "user_events": [
                bigquery.SchemaField("timestamp", "TIMESTAMP"),
                bigquery.SchemaField("type", "STRING"),
                bigquery.SchemaField("user", "STRING"),
                bigquery.SchemaField("company", "STRING"),
                bigquery.SchemaField("call_duration", "INTEGER"),
                bigquery.SchemaField("call_type", "STRING"),
                bigquery.SchemaField("call_num_users", "INTEGER"),
                bigquery.SchemaField("call_os", "STRING"),
                bigquery.SchemaField("rating", "INTEGER"),
                bigquery.SchemaField("comment", "STRING"),
                bigquery.SchemaField("session_id", "STRING"),
                bigquery.SchemaField("dialin_duration", "INTEGER"),
                bigquery.SchemaField("ticket_number", "STRING"),
                bigquery.SchemaField("ticket_driver", "STRING"),
            ],
            "company_events": [
                bigquery.SchemaField("timestamp", "TIMESTAMP"),
                bigquery.SchemaField("type", "STRING"),
                bigquery.SchemaField("company", "STRING"),
                bigquery.SchemaField("purchased", "INTEGER"),
                bigquery.SchemaField("provisioned", "INTEGER"),
                bigquery.SchemaField("serial_number", "STRING"),
                bigquery.SchemaField("box_name", "STRING"),
            ],
        }

        # Required Firestore collections
        self.firestore_collections = [
            "users",
            "companies",
            "projects",
            "trending",
            "renewals",
        ]

        # Demo data: sample comments
        self.good_comments = [
            "Great!",
            "Love this video thing!",
            "Feels like I am there!",
            "Good",
            "Highfive rocks",
        ]
        self.bad_comments = [
            "Disconnected",
            "Video dropouts",
            "Crackling audio",
            "Slows computer down",
            "I am ugly",
        ]

        # Demo data: sample values
        self.operating_systems = ["Mac OSX", "Windows", "Linux", "ios", "Android"]
        self.call_types = ["Web", "Presentation", "Room-and-Web", "Multi-room-and-Web"]
        self.drivers = ["Video", "Audio", "Network"]
        self.project_list = ["Pilot", "Pro Eval", "Global Launch", "QBR", "Case Study"]
        self.metric_list = ["7DAU", "CPW", "CH/B/D", "RU", "Diversity"]

        # Demo data: generation parameters
        self.demo_min_projects_per_company = 1
        self.demo_max_projects_per_company = 3
        self.demo_project_start_delay_days = 90
        self.demo_trending_metrics_count = 3
        self.demo_trending_data_interval_days = 7
        self.demo_trending_data_period_days = 30
        self.demo_min_renewal_days = 30
        self.demo_max_renewal_days = 365
        self.demo_max_reg_delay_minutes = 120
        self.demo_user_events_batch_size = int(
            os.getenv("DEMO_USER_EVENTS_BATCH_SIZE", "1000")
        )
