import json
import time

from google.cloud import bigquery, bigquery_storage_v1
from google.cloud.exceptions import NotFound

from ..utils import get_logger
from ..utils.exceptions import ExternalServiceError

logger = get_logger(__name__)


class BigQueryService:
    """BigQuery service for dataset and table operations."""

    def __init__(self, cfg):
        # Configuration
        self.project_id = cfg.project
        self.dataset_id = cfg.bigquery_dataset
        self.dataset_location = cfg.bigquery_location
        self.dataset_description = cfg.bigquery_description
        self.table_schemas = cfg.table_schemas

        # Initialize clients
        try:
            self.client = bigquery.Client(project=self.project_id)
            self.write_client = bigquery_storage_v1.BigQueryWriteClient()
            logger.info("BigQuery client initialized", project=self.project_id)
        except Exception as e:
            logger.error("Failed to initialize BigQuery clients", error=str(e))
            raise ExternalServiceError(
                f"Failed to initialize BigQuery clients: {str(e)}"
            )

    def _create_dataset_if_not_exists(self):
        """Create dataset if it doesn't exist."""
        client = self.client
        dataset_ref = client.dataset(self.dataset_id)
        try:
            dataset = client.get_dataset(dataset_ref)
            logger.info(f"Dataset {self.dataset_id} already exists")
            return dataset
        except NotFound:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = self.dataset_location
            dataset.description = self.dataset_description
            dataset = client.create_dataset(dataset)
            logger.info(f"Created dataset {self.dataset_id}")
            return dataset

    def _create_table(self, dataset, table_id, schema):
        """Create table, replacing existing table if present."""
        client = self.client
        table_ref = dataset.table(table_id)
        try:
            client.get_table(table_ref)
            logger.info(f"Table {table_id} exists, deleting it")
            client.delete_table(table_ref)
            logger.info(f"Deleted table {table_id}")
        except NotFound:
            logger.info(f"Table {table_id} does not exist")

        # Create the table
        table = bigquery.Table(table_ref, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY, field="timestamp"
        )
        client.create_table(table)
        logger.info(f"Created table {table_id}")
        return True

    def setup(self):
        """Set up BigQuery dataset and tables."""
        try:
            dataset = self._create_dataset_if_not_exists()
            created_tables = []
            for table_id, schema in self.table_schemas.items():
                if self._create_table(dataset, table_id, schema):
                    created_tables.append(table_id)

            return {
                "success": True,
                "message": (
                    f"BigQuery setup completed successfully. Created tables: {created_tables}"
                ),
                "project_id": self.project_id,
                "dataset_id": self.dataset_id,
            }

        except Exception as e:
            logger.error(f"Error setting up BigQuery: {str(e)}")
            return {"success": False, "message": f"Error setting up BigQuery: {str(e)}"}

    def execute_query(self, query: str, project_id: str = None):
        try:
            client = self.client
            query_job = client.query(query)
            results = query_job.result()
            rows = []
            for row in results:
                rows.append(dict(row))

            logger.info(f"Query executed successfully, returned {len(rows)} rows")
            return rows

        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise

    def delete_all_rows(self, table_name: str):
        try:
            # Use TRUNCATE TABLE instead of DELETE to avoid streaming buffer issues
            query = f"TRUNCATE TABLE `{self.project_id}.{self.dataset_id}.{table_name}`"

            logger.info(f"Truncating table {table_name}")
            job = self.client.query(query)
            job.result()  # Wait for completion

            logger.info(f"Successfully truncated table {table_name}")
            return {
                "success": True,
                "message": f"Successfully truncated table {table_name}",
            }

        except Exception as e:
            error_msg = f"Error truncating table {table_name}: {str(e)}"
            logger.error(error_msg)
            raise ExternalServiceError(error_msg)

    def write_rows_to_table(self, table_name: str, rows: list):
        try:
            if not rows:
                logger.warning(f"No rows to insert into table {table_name}")
                return {
                    "success": True,
                    "message": f"No rows to insert into table {table_name}",
                    "rows_inserted": 0,
                }

            table_ref = f"{self.project_id}.{self.dataset_id}.{table_name}"
            batch_size = 10000
            total_inserted = 0

            # Retry logic for table not found errors after truncation
            max_retries = 3
            base_delay = 1  # Start with 1 second delay

            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]

                for retry_attempt in range(max_retries):
                    try:
                        errors = self.client.insert_rows_json(table_ref, batch)
                        if errors:
                            error_msg = f"BigQuery insert_rows_json errors: {errors}"
                            logger.error(error_msg)
                            raise ExternalServiceError(error_msg)
                        total_inserted += len(batch)
                        break  # Success, exit retry loop

                    except Exception as e:
                        error_str = str(e)
                        # Check if this is a "table not found" error that might be transient
                        if (
                            "not found" in error_str.lower()
                            and retry_attempt < max_retries - 1
                        ):
                            delay = base_delay * (
                                2**retry_attempt
                            )  # Exponential backoff
                            logger.warning(
                                f"Table {table_name} not found on attempt {retry_attempt + 1}, "
                                f"retrying in {delay} seconds..."
                            )
                            time.sleep(delay)
                            continue
                        else:
                            # Either not a retryable error, or we've exhausted retries
                            raise e

            logger.info(
                f"Successfully inserted {total_inserted} rows into table {table_name} using legacy streaming API"
            )
            return {
                "success": True,
                "message": (
                    f"Successfully inserted {total_inserted} rows into table {table_name}"
                ),
                "rows_inserted": total_inserted,
            }

        except Exception as e:
            error_msg = f"Error writing rows to table {table_name}: {str(e)}"
            logger.error(error_msg)
            raise ExternalServiceError(error_msg)
