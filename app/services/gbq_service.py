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
        """Write realtime analysis result to BigQuery asynchronously

        Args:
            data: Analysis data containing:
                - id: UUID string
                - tenant_id: Tenant identifier (e.g., "island_parents")
                - session_id: Session ID (None for web version)
                - analyzed_at: Analysis timestamp
                - analysis_type: "emergency" | "practice"
                - safety_level: "green" | "yellow" | "red"
                - matched_suggestions: List of suggestion strings
                - transcript_segment: Analyzed transcript
                - api_response_time_ms: API response time in milliseconds
                - created_at: Record creation timestamp

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

            # Get timestamps with defaults
            start_time = data.get("start_time", analyzed_at)
            end_time = data.get("end_time", created_at)

            # Convert timestamps to ISO format
            start_time_str = (
                start_time.isoformat()
                if isinstance(start_time, datetime)
                else start_time
            )
            end_time_str = (
                end_time.isoformat() if isinstance(end_time, datetime) else end_time
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

            # Prepare comprehensive row for insertion
            row = {
                # IDs and metadata
                "id": data.get("id", str(uuid.uuid4())),
                "tenant_id": data.get("tenant_id", "island_parents"),
                "session_id": data.get("session_id"),
                "request_id": data.get("request_id"),
                # Timestamps
                "analyzed_at": analyzed_at_str,
                "start_time": start_time_str,
                "end_time": end_time_str,
                "created_at": created_at_str,
                # Analysis type and result
                "analysis_type": data.get("analysis_type"),
                "safety_level": data.get("safety_level"),
                "matched_suggestions": data.get("matched_suggestions", []),
                "analysis_result": serialize_json(
                    data.get("analysis_result")
                ),  # JSON field
                "analysis_reasoning": data.get("analysis_reasoning"),
                # Input data
                "transcript": data.get("transcript", ""),
                "time_range": data.get("time_range"),
                "speakers": serialize_json(data.get("speakers")),  # JSON field
                # Prompts
                "system_prompt": data.get("system_prompt"),
                "user_prompt": data.get("user_prompt"),
                "prompt_template": data.get("prompt_template"),
                # RAG information
                "rag_used": data.get("rag_used"),
                "rag_query": data.get("rag_query"),
                "rag_documents": serialize_json(
                    data.get("rag_documents")
                ),  # JSON field
                "rag_sources": data.get("rag_sources", []),
                "rag_top_k": data.get("rag_top_k"),
                "rag_similarity_threshold": data.get("rag_similarity_threshold"),
                "rag_search_time_ms": data.get("rag_search_time_ms"),
                # Model information
                "provider": data.get("provider"),
                "model_name": data.get("model_name"),
                "model_version": data.get("model_version"),
                # Timing breakdown
                "duration_ms": data.get("duration_ms"),
                "api_response_time_ms": data.get("api_response_time_ms", 0),
                "llm_call_time_ms": data.get("llm_call_time_ms"),
                # LLM response
                "llm_raw_response": data.get("llm_raw_response"),
                # Token usage
                "prompt_tokens": data.get("prompt_tokens"),
                "completion_tokens": data.get("completion_tokens"),
                "total_tokens": data.get("total_tokens"),
                "cached_tokens": data.get("cached_tokens"),
                "estimated_cost_usd": data.get("estimated_cost_usd"),
                # Cache info
                "use_cache": data.get("use_cache"),
                "cache_hit": data.get("cache_hit"),
                "cache_key": data.get("cache_key"),
                "gemini_cache_ttl": data.get("gemini_cache_ttl"),
                # Mode
                "mode": data.get("mode"),
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

            # Define schema
            schema = [
                bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("session_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("analyzed_at", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("analysis_type", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("safety_level", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("matched_suggestions", "STRING", mode="REPEATED"),
                bigquery.SchemaField("transcript_segment", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("response_time_ms", "INT64", mode="REQUIRED"),
                bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
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


# Singleton instance
gbq_service = GBQService()
