"""
BigQuery Service for Realtime Analysis Persistence
Handles asynchronous writes to BigQuery for analysis results logging.
"""
import json
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
            data: Complete analysis data with full observability metadata including:
                - Basic identification (id, tenant_id, session_id, timestamps)
                - Complete transcript and speakers (NO truncation)
                - Prompt information (system_prompt, user_prompt, prompt_template)
                - RAG information (usage, query, documents, sources, parameters)
                - Model information (provider, name, version)
                - Timing breakdown (start, end, duration, RAG time, LLM time)
                - Analysis results (type, level, suggestions, reasoning)
                - LLM response (raw response, structured result)
                - Token usage (prompt, completion, cached, cost)
                - Cache information (usage, hit, key, TTL)
                - Request context (mode, request_id)

        Returns:
            bool: True if write successful, False otherwise

        Raises:
            No exceptions raised - all errors are caught and logged
        """
        try:
            # Ensure table exists before writing
            if not self.ensure_table_exists():
                logger.error("Failed to ensure table exists, cannot write to BigQuery")
                return False

            # Helper function to serialize datetime objects
            def serialize_datetime(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return obj

            # Helper function to ensure JSON-serializable objects for BigQuery
            def ensure_json_serializable(obj):
                """Convert Python dicts/lists to JSON strings for BigQuery JSON fields

                BigQuery JSON type fields require JSON **strings**, not Python dicts.
                This converts Python objects to JSON strings using json.dumps().
                """
                if obj is None:
                    return None
                if isinstance(obj, (dict, list)):
                    # CRITICAL: BigQuery JSON fields MUST be JSON strings
                    return json.dumps(obj, default=str)
                return obj

            # Get timestamps with defaults
            analyzed_at = data.get("analyzed_at", datetime.now(timezone.utc))
            created_at = data.get("created_at", datetime.now(timezone.utc))
            start_time = data.get("start_time", analyzed_at)
            end_time = data.get("end_time", analyzed_at)

            # Prepare row for insertion with ALL metadata fields
            row = {
                # Basic identification
                "id": data.get("id", str(uuid.uuid4())),
                "tenant_id": data.get("tenant_id", "island_parents"),
                "session_id": data.get("session_id"),
                "analyzed_at": serialize_datetime(analyzed_at),
                "created_at": serialize_datetime(created_at),
                # Complete transcript (NO truncation!)
                "transcript": data.get("transcript"),
                "time_range": data.get("time_range"),
                "speakers": ensure_json_serializable(
                    data.get("speakers")
                ),  # JSON field
                # Prompt information (complete observability)
                "system_prompt": data.get("system_prompt"),
                "user_prompt": data.get("user_prompt"),
                "prompt_template": data.get("prompt_template"),
                # RAG information (expanded)
                "rag_used": data.get("rag_used", False),
                "rag_query": data.get("rag_query"),
                "rag_documents": ensure_json_serializable(
                    data.get("rag_documents")
                ),  # JSON field
                "rag_sources": data.get("rag_sources", []),
                "rag_top_k": data.get("rag_top_k"),
                "rag_similarity_threshold": data.get("rag_similarity_threshold"),
                # Model information
                "provider": data.get("provider"),
                "model_name": data.get("model_name"),
                "model_version": data.get("model_version"),
                # Timing & performance (detailed breakdown)
                "start_time": serialize_datetime(start_time),
                "end_time": serialize_datetime(end_time),
                "duration_ms": data.get("duration_ms", 0),
                "api_response_time_ms": data.get("api_response_time_ms", 0),
                "rag_search_time_ms": data.get("rag_search_time_ms", 0),
                "llm_call_time_ms": data.get("llm_call_time_ms", 0),
                # Analysis results
                "analysis_type": data.get("analysis_type"),
                "safety_level": data.get("safety_level"),
                "matched_suggestions": data.get("matched_suggestions", []),
                # LLM response (complete observability)
                "llm_raw_response": data.get("llm_raw_response"),
                "analysis_result": ensure_json_serializable(
                    data.get("analysis_result")
                ),  # JSON field
                "analysis_reasoning": data.get("analysis_reasoning"),
                # Token usage (expanded)
                "prompt_tokens": data.get("prompt_tokens", 0),
                "completion_tokens": data.get("completion_tokens", 0),
                "total_tokens": data.get("total_tokens", 0),
                "cached_tokens": data.get("cached_tokens", 0),
                "estimated_cost_usd": float(
                    data.get("estimated_cost_usd", 0.0)
                ),  # Explicit float conversion
                # Cache information (expanded)
                "use_cache": data.get("use_cache", False),
                "cache_hit": data.get("cache_hit", False),
                "cache_key": data.get("cache_key"),
                "gemini_cache_ttl": data.get("gemini_cache_ttl"),
                # Request context
                "mode": data.get("mode"),
                "request_id": data.get("request_id"),
            }

            # Remove None values for JSON/REPEATED fields to avoid BigQuery errors
            # BigQuery doesn't like None for JSON fields
            # Keep None for explicitly nullable fields
            nullable_fields = {
                "session_id",  # session_id can be None for web version
                "rag_query",
                "rag_top_k",
                "rag_similarity_threshold",  # RAG fields can be None
                "model_version",
                "analysis_reasoning",  # Optional fields
                "cache_key",  # Cache fields can be None
            }

            # Filter out None values for JSON fields (speakers, rag_documents, analysis_result)
            json_fields = {"speakers", "rag_documents", "analysis_result"}
            row = {
                k: v
                for k, v in row.items()
                if v is not None or k in nullable_fields or k not in json_fields
            }

            # Insert row into BigQuery
            table_ref = self._get_table_ref()
            errors = self.client.insert_rows_json(table_ref, [row])

            if errors:
                logger.error(f"BigQuery insert failed for table {table_ref}: {errors}")
                return False

            logger.info(
                f"Successfully wrote complete analysis log to BigQuery: "
                f"id={row['id']}, safety_level={row['safety_level']}, "
                f"type={row['analysis_type']}, provider={row['provider']}"
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

        Supports automatic schema migration:
        - Creates table if it doesn't exist
        - Adds missing fields to existing tables
        - Preserves existing data and schema

        Returns:
            bool: True if table exists or was created/updated, False on error
        """
        try:
            # First ensure dataset exists
            if not self.ensure_dataset_exists():
                logger.error("Failed to ensure dataset exists")
                return False

            table_ref = self._get_table_ref()

            # Define complete schema with ALL fields for full observability
            new_schema = [
                # Basic identification
                bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("tenant_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("session_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("analyzed_at", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
                # Complete transcript (NO truncation!)
                bigquery.SchemaField("transcript", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("time_range", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("speakers", "JSON", mode="NULLABLE"),
                # Prompt information (complete observability)
                bigquery.SchemaField("system_prompt", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("user_prompt", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("prompt_template", "STRING", mode="NULLABLE"),
                # RAG information (expanded)
                bigquery.SchemaField("rag_used", "BOOLEAN", mode="NULLABLE"),
                bigquery.SchemaField("rag_query", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("rag_documents", "JSON", mode="NULLABLE"),
                bigquery.SchemaField("rag_sources", "STRING", mode="REPEATED"),
                bigquery.SchemaField("rag_top_k", "INT64", mode="NULLABLE"),
                bigquery.SchemaField(
                    "rag_similarity_threshold", "FLOAT64", mode="NULLABLE"
                ),
                # Model information
                bigquery.SchemaField("provider", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("model_name", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("model_version", "STRING", mode="NULLABLE"),
                # Timing & performance (detailed breakdown)
                bigquery.SchemaField("start_time", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("end_time", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("duration_ms", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("api_response_time_ms", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("rag_search_time_ms", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("llm_call_time_ms", "INT64", mode="NULLABLE"),
                # Analysis results
                bigquery.SchemaField("analysis_type", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("safety_level", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("matched_suggestions", "STRING", mode="REPEATED"),
                # LLM response (complete observability)
                bigquery.SchemaField("llm_raw_response", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("analysis_result", "JSON", mode="NULLABLE"),
                bigquery.SchemaField("analysis_reasoning", "STRING", mode="NULLABLE"),
                # Token usage (expanded)
                bigquery.SchemaField("prompt_tokens", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("completion_tokens", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("total_tokens", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("cached_tokens", "INT64", mode="NULLABLE"),
                bigquery.SchemaField("estimated_cost_usd", "FLOAT64", mode="NULLABLE"),
                # Cache information (expanded)
                bigquery.SchemaField("use_cache", "BOOLEAN", mode="NULLABLE"),
                bigquery.SchemaField("cache_hit", "BOOLEAN", mode="NULLABLE"),
                bigquery.SchemaField("cache_key", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("gemini_cache_ttl", "INT64", mode="NULLABLE"),
                # Request context
                bigquery.SchemaField("mode", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("request_id", "STRING", mode="NULLABLE"),
            ]

            # Check if table exists
            try:
                existing_table = self.client.get_table(table_ref)
                logger.info(f"Table {table_ref} exists, checking for schema updates")

                # Get existing field names
                existing_fields = {field.name for field in existing_table.schema}
                new_field_names = {field.name for field in new_schema}

                # Find missing fields
                missing_fields = new_field_names - existing_fields

                if missing_fields:
                    logger.info(
                        f"Schema migration: Adding {len(missing_fields)} missing fields to table: {missing_fields}"
                    )

                    # Add missing fields to existing schema
                    updated_schema = list(existing_table.schema)
                    for field in new_schema:
                        if field.name in missing_fields:
                            # Ensure new fields are NULLABLE (BigQuery limitation)
                            if field.mode == "REQUIRED":
                                logger.warning(
                                    f"Converting REQUIRED field '{field.name}' to NULLABLE "
                                    f"for schema migration (BigQuery limitation)"
                                )
                                field = bigquery.SchemaField(
                                    field.name,
                                    field.field_type,
                                    mode="NULLABLE",
                                    description=field.description,
                                )
                            updated_schema.append(field)

                    # Update table schema
                    existing_table.schema = updated_schema
                    self.client.update_table(existing_table, ["schema"])
                    logger.info(
                        f"Successfully migrated table schema with {len(missing_fields)} new fields"
                    )
                else:
                    logger.info("Table schema is up to date, no migration needed")

                return True

            except Exception as get_error:
                # Table doesn't exist, create it
                logger.info(
                    f"Table {table_ref} does not exist (Error: {get_error}), creating new table"
                )

                # Create table with partitioning and clustering
                table = bigquery.Table(table_ref, schema=new_schema)

                # Partition by analyzed_at (daily)
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field="analyzed_at",
                )

                # Cluster by tenant_id, safety_level, and provider for query performance
                table.clustering_fields = ["tenant_id", "safety_level", "provider"]

                # Create table
                table = self.client.create_table(table)
                logger.info(
                    f"Created BigQuery table {table_ref} with partitioning and clustering"
                )
                return True

        except Exception as e:
            logger.error(
                f"Failed to ensure BigQuery table exists: {str(e)}", exc_info=True
            )
            return False


# Singleton instance
gbq_service = GBQService()
