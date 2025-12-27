"""
BigQuery Service for Realtime Analysis Persistence
Handles asynchronous writes to BigQuery for analysis results logging.
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from google.cloud import bigquery

logger = logging.getLogger(__name__)


class GBQService:
    """Service for writing realtime analysis results to BigQuery"""

    def __init__(self):
        self.project_id = os.getenv("GCS_PROJECT", "groovy-iris-473015-h3")
        self.dataset_id = os.getenv("REALTIME_DATASET_ID", "realtime_logs")
        self.table_id = os.getenv("REALTIME_TABLE_ID", "realtime_analysis_logs")
        self._client: Optional[bigquery.Client] = None  # Lazy initialization

    @property
    def client(self) -> bigquery.Client:
        """Lazy-load BigQuery client to avoid authentication errors in CI/testing"""
        if self._client is None:
            self._client = bigquery.Client(project=self.project_id)
        return self._client

    def _get_table_ref(self) -> str:
        """Get fully qualified table reference"""
        return f"{self.project_id}.{self.dataset_id}.{self.table_id}"

    async def write_analysis_log(self, data: Dict[str, Any]) -> bool:
        """Write session analysis log to BigQuery asynchronously

        Args:
            data: Analysis data containing (aligned with SessionAnalysisLog model):
                Core identifiers:
                - id: UUID string
                - session_id: Session UUID
                - counselor_id: Counselor UUID
                - tenant_id: Tenant identifier (default: "island_parents")

                Timestamps:
                - created_at: Record creation timestamp
                - updated_at: Last update timestamp (optional)
                - deleted_at: Soft delete timestamp (optional)
                - analyzed_at: Analysis timestamp

                Analysis metadata:
                - analysis_type: Type of analysis performed
                - transcript_segment: Transcript segment analyzed
                - result_data: Analysis results (JSON)

                Safety assessment:
                - safety_level: "green" | "yellow" | "red"
                - severity: Severity level if applicable
                - display_text: Display text for UI
                - action_suggestion: Suggested actions
                - risk_indicators: List of risk indicators (JSON)

                RAG information:
                - rag_documents: RAG documents used (JSON)
                - rag_sources: RAG source references (JSON)

                Technical metrics:
                - transcript_length: Character count
                - duration_seconds: Duration in seconds
                - model_used: AI model used

                Token usage:
                - token_usage: Token usage details (JSON)
                - prompt_tokens: Prompt tokens
                - completion_tokens: Completion tokens
                - total_tokens: Total tokens
                - cached_tokens: Cached tokens

                Cost:
                - estimated_cost_usd: Estimated cost in USD

        Returns:
            bool: True if write successful, False otherwise

        Raises:
            No exceptions raised - all errors are caught and logged
        """
        try:
            # Get timestamps with defaults
            analyzed_at = data.get("analyzed_at", datetime.now(timezone.utc))
            created_at = data.get("created_at", datetime.now(timezone.utc))

            # Convert datetime to ISO format string for JSON serialization
            analyzed_at_str = (
                analyzed_at.isoformat()
                if isinstance(analyzed_at, datetime)
                else analyzed_at
            )
            created_at_str = (
                created_at.isoformat()
                if isinstance(created_at, datetime)
                else created_at
            )

            # Serialize JSON fields (BigQuery JSON type expects JSON strings)
            import json as json_module

            def serialize_json(value):
                """Serialize dict/list to JSON string for BigQuery JSON fields"""
                if value is None:
                    return None
                if isinstance(value, (dict, list)):
                    return json_module.dumps(value, ensure_ascii=False)
                return value

            # Get optional timestamps
            updated_at = data.get("updated_at")
            deleted_at = data.get("deleted_at")

            updated_at_str = (
                (
                    updated_at.isoformat()
                    if isinstance(updated_at, datetime)
                    else updated_at
                )
                if updated_at
                else None
            )

            deleted_at_str = (
                (
                    deleted_at.isoformat()
                    if isinstance(deleted_at, datetime)
                    else deleted_at
                )
                if deleted_at
                else None
            )

            # Prepare row for insertion (aligned with SessionAnalysisLog schema)
            row = {
                # Core identifiers
                "id": data.get("id", str(uuid.uuid4())),
                "session_id": data.get("session_id"),
                "counselor_id": data.get("counselor_id"),
                "tenant_id": data.get("tenant_id", "island_parents"),
                # Timestamps
                "created_at": created_at_str,
                "updated_at": updated_at_str,
                "deleted_at": deleted_at_str,
                "analyzed_at": analyzed_at_str,
                # Analysis metadata
                "analysis_type": data.get("analysis_type"),
                "transcript_segment": data.get("transcript_segment"),
                "result_data": serialize_json(data.get("result_data")),
                # Safety assessment
                "safety_level": data.get("safety_level"),
                "severity": data.get("severity"),
                "display_text": data.get("display_text"),
                "action_suggestion": data.get("action_suggestion"),
                "risk_indicators": serialize_json(data.get("risk_indicators")),
                # RAG information
                "rag_documents": serialize_json(data.get("rag_documents")),
                "rag_sources": serialize_json(data.get("rag_sources")),
                # Technical metrics
                "transcript_length": data.get("transcript_length"),
                "duration_seconds": data.get("duration_seconds"),
                "model_name": data.get("model_name"),
                # Token usage
                "token_usage": serialize_json(data.get("token_usage")),
                "prompt_tokens": data.get("prompt_tokens"),
                "completion_tokens": data.get("completion_tokens"),
                "total_tokens": data.get("total_tokens"),
                "cached_tokens": data.get("cached_tokens"),
                # Cost
                "estimated_cost_usd": data.get("estimated_cost_usd"),
            }

            # Insert row into BigQuery
            table_ref = self._get_table_ref()
            errors = self.client.insert_rows_json(table_ref, [row])

            if errors:
                logger.error(f"BigQuery insert failed for table {table_ref}: {errors}")
                return False

            logger.info(
                f"Successfully wrote realtime analysis log to BigQuery: "
                f"id={row['id']}, safety_level={row['safety_level']}, "
                f"type={row['analysis_type']}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to write to BigQuery (table: {self._get_table_ref()}): {str(e)}",
                exc_info=True,
            )
            return False

    def ensure_dataset_exists(self) -> bool:
        """Ensure the BigQuery dataset exists

        Returns:
            bool: True if dataset exists or was created, False on error
        """
        try:
            dataset_ref = f"{self.project_id}.{self.dataset_id}"

            # Check if dataset exists
            try:
                self.client.get_dataset(dataset_ref)
                logger.info(f"BigQuery dataset {dataset_ref} already exists")
                return True
            except Exception:
                # Dataset doesn't exist, create it
                pass

            # Create dataset
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"  # Set location
            dataset.description = "Realtime analysis logs for career counseling"

            dataset = self.client.create_dataset(dataset, timeout=30)
            logger.info(f"Created BigQuery dataset {dataset_ref}")
            return True

        except Exception as e:
            logger.error(f"Failed to create BigQuery dataset: {str(e)}", exc_info=True)
            return False

    def ensure_table_exists(self) -> bool:
        """Ensure the BigQuery table exists with correct schema

        Returns:
            bool: True if table exists or was created, False on error
        """
        try:
            # First ensure dataset exists
            if not self.ensure_dataset_exists():
                logger.error("Failed to ensure dataset exists")
                return False

            table_ref = self._get_table_ref()

            # Check if table exists
            try:
                self.client.get_table(table_ref)
                logger.info(f"BigQuery table {table_ref} already exists")
                return True
            except Exception:
                # Table doesn't exist, create it
                pass

            # Define schema (fully aligned with SessionAnalysisLog model)
            schema = [
                # Core identifiers
                bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("session_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("counselor_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
                # Timestamps
                bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("updated_at", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("deleted_at", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("analyzed_at", "TIMESTAMP", mode="REQUIRED"),
                # Analysis metadata
                bigquery.SchemaField("analysis_type", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("transcript_segment", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("result_data", "JSON", mode="NULLABLE"),
                # Safety assessment
                bigquery.SchemaField("safety_level", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("severity", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("display_text", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("action_suggestion", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("risk_indicators", "JSON", mode="NULLABLE"),
                # RAG information
                bigquery.SchemaField("rag_documents", "JSON", mode="NULLABLE"),
                bigquery.SchemaField("rag_sources", "JSON", mode="NULLABLE"),
                # Technical metrics
                bigquery.SchemaField("transcript_length", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("duration_seconds", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("model_name", "STRING", mode="NULLABLE"),
                # Token usage
                bigquery.SchemaField("token_usage", "JSON", mode="NULLABLE"),
                bigquery.SchemaField("prompt_tokens", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("completion_tokens", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("total_tokens", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("cached_tokens", "INT64", mode="NULLABLE"),
                # Cost
                bigquery.SchemaField("estimated_cost_usd", "FLOAT64", mode="NULLABLE"),
            ]

            # Create table with partitioning and clustering
            table = bigquery.Table(table_ref, schema=schema)

            # Partition by analyzed_at (daily)
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="analyzed_at",
            )

            # Cluster by tenant_id and safety_level for query performance
            table.clustering_fields = ["tenant_id", "safety_level"]

            # Create table
            table = self.client.create_table(table)
            logger.info(
                f"Created BigQuery table {table_ref} with partitioning and clustering"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to create BigQuery table: {str(e)}", exc_info=True)
            return False

    def recreate_table(self) -> bool:
        """Delete and recreate the BigQuery table with updated schema

        WARNING: This will DELETE all existing data!
        Only use for testing or migrations.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import time

            table_ref = self._get_table_ref()

            # Try to delete existing table
            try:
                self.client.delete_table(table_ref)
                logger.info(f"Deleted existing BigQuery table: {table_ref}")
                # Wait for deletion to propagate (BigQuery eventual consistency)
                time.sleep(3)
            except Exception as e:
                logger.info(f"No existing table to delete: {e}")

            # Create new table with updated schema
            result = self.ensure_table_exists()

            if result:
                # Wait for table creation to fully propagate
                time.sleep(5)
                logger.info("Table recreation completed, waiting for propagation")

            return result

        except Exception as e:
            logger.error(f"Failed to recreate BigQuery table: {str(e)}", exc_info=True)
            return False


# Singleton instance
gbq_service = GBQService()
