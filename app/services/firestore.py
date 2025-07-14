from google.api_core import exceptions
from google.cloud import firestore, firestore_admin_v1
from google.cloud.firestore_admin_v1.types.firestore_admin import CreateDatabaseRequest
from google.cloud.firestore_admin_v1.types import Database
import concurrent.futures
import threading
from typing import List

from ..utils import get_logger
from ..utils.exceptions import ExternalServiceError

logger = get_logger(__name__)


class FirestoreService:
    """Firestore database service for document operations."""

    def __init__(self, cfg):
        # Configuration
        self.project_id = cfg.project
        self.database_id = cfg.firestore_database
        self.location_id = cfg.firestore_location
        self.required_collections = cfg.firestore_collections

        if not self.project_id:
            raise ExternalServiceError("Project ID must be provided in configuration")

        # Initialize Firestore client
        try:
            self.client = firestore.Client(
                project=self.project_id, database=self.database_id
            )
            self.database = self.client
            logger.info("Firestore client initialized", project=self.project_id)
        except Exception as e:
            logger.error("Failed to initialize Firestore client", error=str(e))
            raise ExternalServiceError(
                f"Failed to initialize Firestore client: {str(e)}"
            )

        # Initialize admin client
        try:
            self.admin_client = firestore_admin_v1.FirestoreAdminClient()
            logger.info("FirestoreAdminClient created successfully")
        except Exception as e:
            logger.warning("Failed to create FirestoreAdminClient", error=str(e))

    def _database_exists(self):
        """Check if Firestore database exists."""
        database_path = self.admin_client.database_path(
            self.project_id, self.database_id
        )
        print(f"Checking if Firestore database exists at {database_path}")
        try:
            existing_db = self.admin_client.get_database(name=database_path)
            return True
        except exceptions.NotFound:
            return False
        except Exception as e:
            logger.warning(
                "Error checking database existence", error=str(e), exc_info=True
            )
            raise ExternalServiceError(f"Error checking database existence: {str(e)}")

    def _create_database(self):
        """Create new Firestore database."""
        try:
            parent = f"projects/{self.project_id}"
            database_path = self.admin_client.database_path(
                self.project_id, self.database_id
            )

            logger.info("Creating Firestore database", database_id=self.database_id)
            database = Database(
                name=database_path,
                location_id=self.location_id,
                type_=firestore_admin_v1.types.Database.DatabaseType.FIRESTORE_NATIVE,
            )
            request = CreateDatabaseRequest(
                parent=parent, database=database, database_id=self.database_id
            )
            operation = self.admin_client.create_database(request=request)
            logger.info(
                "Waiting for Firestore database creation operation to complete..."
            )
            result = operation.result(timeout=300)  # 5 minutes timeout
        except Exception as e:
            logger.warning("Could not create database via Admin API", error=str(e))
            raise ExternalServiceError(
                f"Could not create database via Admin API: {str(e)}"
            )

    def setup(self):
        """Initialize Firestore database if needed."""
        try:
            db_result = None
            if not self._database_exists():
                db_result = self._create_database()
            return {
                "success": True,
                "message": "Firestore setup completed successfully",
                "project_id": self.project_id,
                "database_id": self.database_id,
                "database": db_result,
            }

        except Exception as e:
            logger.error("Error setting up Firestore", error=str(e))
            return {
                "success": False,
                "message": f"Error setting up Firestore: {str(e)}",
            }

    def delete_all_documents(self, collection_name, batch_size=500, max_workers=10):
        """Delete all documents in collection using parallel batch processing."""
        try:
            collection_ref = self.client.collection(collection_name)
            deleted_count = 0
            delete_lock = threading.Lock()

            def delete_batch(doc_refs: List):
                """Delete a batch of document references."""
                nonlocal deleted_count
                if not doc_refs:
                    return 0

                batch = self.client.batch()
                for doc_ref in doc_refs:
                    batch.delete(doc_ref)

                batch.commit()

                with delete_lock:
                    deleted_count += len(doc_refs)

                return len(doc_refs)

            # Get all document references in larger chunks for better performance
            # We'll use a larger page size to reduce round trips
            page_size = batch_size * 4  # Fetch 4x batch size at once
            all_docs = []

            logger.info(
                f"Fetching all documents from collection '{collection_name}'..."
            )

            # Use select() to only fetch document references, not data
            docs_stream = collection_ref.select([]).limit(page_size).stream()

            # Collect all document references
            current_batch_refs = []
            batch_futures = []

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                for doc in docs_stream:
                    current_batch_refs.append(doc.reference)

                    # When we have a full batch, submit it for deletion
                    if len(current_batch_refs) >= batch_size:
                        future = executor.submit(
                            delete_batch, current_batch_refs.copy()
                        )
                        batch_futures.append(future)
                        current_batch_refs.clear()

                        # To avoid memory issues, wait for some batches to complete
                        # when we have too many pending
                        if len(batch_futures) >= max_workers * 2:
                            # Wait for the oldest batch to complete
                            completed_future = batch_futures.pop(0)
                            completed_future.result()

                # Submit the remaining documents
                if current_batch_refs:
                    future = executor.submit(delete_batch, current_batch_refs)
                    batch_futures.append(future)

                # Wait for all remaining batches to complete
                logger.info(
                    f"Waiting for {len(batch_futures)} deletion batches to complete..."
                )
                for future in concurrent.futures.as_completed(batch_futures):
                    try:
                        future.result()  # This will raise any exceptions that occurred
                    except Exception as e:
                        logger.error(f"Error in batch deletion: {e}")
                        raise

            if deleted_count == 0:
                logger.info(
                    f"Collection '{collection_name}' was already empty or doesn't exist"
                )
            else:
                logger.info(
                    f"Successfully deleted {deleted_count} documents from collection '{collection_name}' using parallel processing"
                )

            return deleted_count

        except Exception as e:
            logger.error(
                f"Failed to delete collection '{collection_name}'", error=str(e)
            )
            raise ExternalServiceError(
                f"Failed to delete collection '{collection_name}': {str(e)}"
            )

    def batch_write(self, collection, documents):
        """Write multiple documents to collection in batch."""
        if not documents:
            logger.warning("No documents to write")
            return

        batch = self.client.batch()
        for doc in documents:
            ref = self.client.collection(collection).document()
            batch.set(ref, doc)

        try:
            batch.commit()
            logger.info("Batch write completed successfully")
        except Exception as e:
            logger.error("Batch write failed", error=str(e))
            raise ExternalServiceError(f"Batch write failed: {str(e)}")

    def update_document_by_field(
        self, collection_name, field_name, field_value, update_fields
    ):
        """Update document by searching for field value, preserving other fields."""
        try:
            # Query for documents where field_name equals field_value
            docs = (
                self.client.collection(collection_name)
                .where(field_name, "==", field_value)
                .limit(1)
                .stream()
            )

            # Get the first (and should be only) matching document
            doc_found = False
            for doc in docs:
                # Update the found document
                doc.reference.update(update_fields)
                logger.info(
                    f"Successfully updated document with {field_name}='{field_value}' in collection {collection_name}"
                )
                doc_found = True
                break

            if not doc_found:
                logger.warning(
                    f"No document found with {field_name}='{field_value}' in collection {collection_name}"
                )
                raise ExternalServiceError(
                    f"No document found with {field_name}='{field_value}' in collection {collection_name}"
                )

        except Exception as e:
            logger.error(
                f"Failed to update document with {field_name}='{field_value}' in collection {collection_name}",
                error=str(e),
            )
            raise ExternalServiceError(
                f"Failed to update document with {field_name}='{field_value}': {str(e)}"
            )

    def update_document(self, collection_name, document_id, update_fields):
        """
        Update specific fields in a Firestore document, preserving all other existing fields.
        If the document doesn't exist, it will be created with only the provided fields.

        Args:
            collection_name: Name of the collection
            document_id: ID of the document to update
            update_fields: Dictionary of fields to update
        """
        try:
            doc_ref = self.client.collection(collection_name).document(document_id)

            # Check if document exists first
            doc = doc_ref.get()
            if doc.exists:
                # Document exists, use update() to preserve other fields
                doc_ref.update(update_fields)
                logger.info(
                    f"Successfully updated existing document {document_id} in collection {collection_name}"
                )
            else:
                # Document doesn't exist, create it with set()
                doc_ref.set(update_fields)
                logger.info(
                    f"Successfully created new document {document_id} in collection {collection_name}"
                )
        except Exception as e:
            logger.error(
                f"Failed to update document {document_id} in collection {collection_name}",
                error=str(e),
            )
            raise ExternalServiceError(
                f"Failed to update document {document_id}: {str(e)}"
            )
