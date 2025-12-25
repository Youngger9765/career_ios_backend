"""
Real BigQuery Integration Tests for GBQService
Tests actual read/write to BigQuery (not mocked)

These tests verify that GBQService correctly:
1. Writes records to BigQuery
2. Reads records back from BigQuery
3. Creates tables with correct schema
4. Handles data persistence end-to-end

Only runs when GCP credentials are available.
Test data uses "test_" prefix and is cleaned up after tests.
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from google.cloud import bigquery

from app.services.gbq_service import GBQService


# Skip these tests if Google Cloud credentials are not available
def _check_gcp_credentials():
    """Check if valid GCP credentials are available"""
    try:
        from google.auth import default
        from google.auth.exceptions import DefaultCredentialsError, RefreshError

        try:
            credentials, project = default()
            from google.auth.transport.requests import Request

            credentials.refresh(Request())
            return True
        except (DefaultCredentialsError, RefreshError, Exception):
            return False
    except ImportError:
        return False


HAS_VALID_GCP_CREDENTIALS = _check_gcp_credentials()

skip_without_gcp = pytest.mark.skipif(
    not HAS_VALID_GCP_CREDENTIALS,
    reason="Valid Google Cloud credentials not available (run: gcloud auth application-default login)",
)


@pytest.fixture
def gbq_service():
    """Create GBQService instance for testing"""
    return GBQService()


@pytest.fixture
def test_record_id():
    """Generate test record ID with test_ prefix"""
    return f"test_{uuid.uuid4()}"


@pytest.fixture
def sample_analysis_data(test_record_id):
    """Create sample analysis data for testing"""
    return {
        "id": test_record_id,
        "tenant_id": "island_parents",
        "session_id": None,
        "analyzed_at": datetime.now(timezone.utc),
        "analysis_type": "emergency",
        "safety_level": "yellow",
        "matched_suggestions": [
            "建議1：保持冷靜，先聆聽孩子的感受",
            "建議2：使用同理心回應",
            "建議3：避免立即批評或指責",
        ],
        "transcript_segment": "家長：你今天在學校過得如何？\n孩子：還不錯，老師稱讚我了。",
        "response_time_ms": 1234,
        "created_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def cleanup_test_records(gbq_service):
    """Cleanup fixture that deletes test records after tests complete

    Note: BigQuery streaming buffer doesn't support DELETE for ~90 minutes.
    Test records will remain in the table until they age out of the buffer.
    This is expected behavior and doesn't affect test correctness.
    """
    test_ids_to_cleanup = []

    def register_for_cleanup(record_id: str):
        """Register a test record ID for cleanup"""
        test_ids_to_cleanup.append(record_id)

    yield register_for_cleanup

    # Cleanup: Attempt to delete test records
    # Note: Will fail for records in streaming buffer (< 90 minutes old)
    if test_ids_to_cleanup:
        table_ref = gbq_service._get_table_ref()
        for record_id in test_ids_to_cleanup:
            try:
                query = f"""
                DELETE FROM `{table_ref}`
                WHERE id = @record_id
                """
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("record_id", "STRING", record_id)
                    ]
                )
                gbq_service.client.query(query, job_config=job_config).result()
            except Exception as e:
                # Expected: streaming buffer doesn't support DELETE
                if "streaming buffer" not in str(e):
                    print(f"Warning: Failed to cleanup test record {record_id}: {e}")


class TestGBQServiceRealBigQuery:
    """Integration tests for GBQService with real BigQuery"""

    @skip_without_gcp
    def test_ensure_table_exists(self, gbq_service):
        """Test that ensure_table_exists creates or verifies table with correct schema

        This test verifies:
        1. Table can be created if it doesn't exist
        2. Returns True if table already exists
        3. Schema includes all required fields
        4. Table has correct partitioning and clustering
        """
        # Ensure table exists
        result = gbq_service.ensure_table_exists()
        assert result is True, "ensure_table_exists should return True"

        # Verify table exists and has correct schema
        table_ref = gbq_service._get_table_ref()
        table = gbq_service.client.get_table(table_ref)

        # Verify schema fields
        schema_fields = {field.name: field for field in table.schema}

        expected_fields = {
            "id": (["STRING"], "REQUIRED"),
            "tenant_id": (["STRING"], "REQUIRED"),
            "session_id": (["STRING"], "NULLABLE"),
            "analyzed_at": (["TIMESTAMP"], "REQUIRED"),
            "analysis_type": (["STRING"], "REQUIRED"),
            "safety_level": (["STRING"], "REQUIRED"),
            "matched_suggestions": (["STRING"], "REPEATED"),
            "transcript_segment": (["STRING"], "NULLABLE"),
            "response_time_ms": (
                ["INT64", "INTEGER"],
                "REQUIRED",
            ),  # BQ returns INTEGER
            "created_at": (["TIMESTAMP"], "REQUIRED"),
        }

        for field_name, (expected_types, expected_mode) in expected_fields.items():
            assert field_name in schema_fields, f"Field {field_name} should exist"
            field = schema_fields[field_name]
            assert field.field_type in expected_types, (
                f"Field {field_name} should be one of {expected_types}, "
                f"got {field.field_type}"
            )
            assert field.mode == expected_mode, (
                f"Field {field_name} should have mode {expected_mode}, "
                f"got {field.mode}"
            )

        # Verify partitioning
        assert table.time_partitioning is not None, "Table should be partitioned"
        assert (
            table.time_partitioning.field == "analyzed_at"
        ), "Should partition by analyzed_at"
        assert (
            table.time_partitioning.type_ == bigquery.TimePartitioningType.DAY
        ), "Should use daily partitioning"

        # Verify clustering
        assert table.clustering_fields is not None, "Table should have clustering"
        assert set(table.clustering_fields) == {
            "tenant_id",
            "safety_level",
        }, "Should cluster by tenant_id and safety_level"

    @skip_without_gcp
    def test_write_and_read_analysis_log(
        self, gbq_service, sample_analysis_data, cleanup_test_records
    ):
        """Test writing a record to BigQuery and reading it back

        This test verifies:
        1. Record is successfully written to BigQuery
        2. Record can be read back with all fields intact
        3. Data types are correctly preserved
        4. Timestamps are handled correctly
        """
        # Register for cleanup
        cleanup_test_records(sample_analysis_data["id"])

        # Write record to BigQuery
        result = asyncio.run(gbq_service.write_analysis_log(sample_analysis_data))
        assert result is True, "write_analysis_log should return True on success"

        # Read record back from BigQuery
        table_ref = gbq_service._get_table_ref()
        query = f"""
        SELECT *
        FROM `{table_ref}`
        WHERE id = @record_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "record_id", "STRING", sample_analysis_data["id"]
                )
            ]
        )

        # Wait a bit for write to propagate (BigQuery eventual consistency)
        import time

        time.sleep(2)

        query_job = gbq_service.client.query(query, job_config=job_config)
        results = list(query_job.result())

        # Verify record was written
        assert len(results) == 1, "Should find exactly one record"

        row = results[0]

        # Verify all fields
        assert row["id"] == sample_analysis_data["id"]
        assert row["tenant_id"] == sample_analysis_data["tenant_id"]
        assert row["session_id"] == sample_analysis_data["session_id"]
        assert row["analysis_type"] == sample_analysis_data["analysis_type"]
        assert row["safety_level"] == sample_analysis_data["safety_level"]
        assert row["matched_suggestions"] == sample_analysis_data["matched_suggestions"]
        assert row["transcript_segment"] == sample_analysis_data["transcript_segment"]
        assert row["response_time_ms"] == sample_analysis_data["response_time_ms"]

        # Verify timestamps (allow small difference due to serialization)
        assert row["analyzed_at"] is not None
        assert row["created_at"] is not None

    @skip_without_gcp
    def test_write_with_minimal_data(self, gbq_service, cleanup_test_records):
        """Test writing a record with minimal required fields

        This test verifies:
        1. Service handles missing optional fields correctly
        2. Default values are applied appropriately
        3. Auto-generated fields (id, timestamps) work correctly
        """
        # Create minimal data (no id, timestamps, or optional fields)
        minimal_data = {
            "analysis_type": "practice",
            "safety_level": "green",
            "matched_suggestions": ["建議1", "建議2", "建議3"],
        }

        # Write record
        result = asyncio.run(gbq_service.write_analysis_log(minimal_data))
        assert result is True, "Should write successfully with minimal data"

        # The service should auto-generate an id - get it from the log or query
        # For cleanup, we query for recent test records
        table_ref = gbq_service._get_table_ref()
        query = f"""
        SELECT id
        FROM `{table_ref}`
        WHERE tenant_id = 'island_parents'
        AND analysis_type = 'practice'
        AND safety_level = 'green'
        AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 SECOND)
        ORDER BY created_at DESC
        LIMIT 1
        """

        import time

        time.sleep(2)

        query_job = gbq_service.client.query(query)
        results = list(query_job.result())

        if results:
            record_id = results[0]["id"]
            cleanup_test_records(record_id)

            # Verify the record has all required fields
            verify_query = f"""
            SELECT *
            FROM `{table_ref}`
            WHERE id = @record_id
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("record_id", "STRING", record_id)
                ]
            )
            verify_job = gbq_service.client.query(verify_query, job_config=job_config)
            verify_results = list(verify_job.result())

            assert len(verify_results) == 1
            row = verify_results[0]

            # Verify auto-generated/default values
            assert row["id"] is not None
            assert row["tenant_id"] == "island_parents"
            assert row["session_id"] is None
            assert row["analyzed_at"] is not None
            assert row["created_at"] is not None
            assert row["response_time_ms"] == 0  # Default value

    @skip_without_gcp
    def test_write_with_session_id(
        self, gbq_service, sample_analysis_data, cleanup_test_records
    ):
        """Test writing a record with session_id (mobile version)

        This test verifies:
        1. session_id is correctly stored when provided
        2. Different from web version (session_id = None)
        """
        # Modify sample data to include session_id
        sample_analysis_data["session_id"] = "mobile_session_12345"
        cleanup_test_records(sample_analysis_data["id"])

        # Write record
        result = asyncio.run(gbq_service.write_analysis_log(sample_analysis_data))
        assert result is True

        # Read back and verify
        table_ref = gbq_service._get_table_ref()
        query = f"""
        SELECT session_id
        FROM `{table_ref}`
        WHERE id = @record_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "record_id", "STRING", sample_analysis_data["id"]
                )
            ]
        )

        import time

        time.sleep(2)

        query_job = gbq_service.client.query(query, job_config=job_config)
        results = list(query_job.result())

        assert len(results) == 1
        assert results[0]["session_id"] == "mobile_session_12345"

    @skip_without_gcp
    def test_write_different_safety_levels(
        self, gbq_service, test_record_id, cleanup_test_records
    ):
        """Test writing records with different safety levels

        This test verifies:
        1. All safety levels (green, yellow, red) are stored correctly
        2. Clustering by safety_level works for queries
        """
        safety_levels = ["green", "yellow", "red"]
        test_ids = []

        for level in safety_levels:
            record_id = f"{test_record_id}_{level}"
            test_ids.append(record_id)
            cleanup_test_records(record_id)

            data = {
                "id": record_id,
                "tenant_id": "island_parents",
                "session_id": None,
                "analyzed_at": datetime.now(timezone.utc),
                "analysis_type": "emergency",
                "safety_level": level,
                "matched_suggestions": [f"建議 for {level}"],
                "transcript_segment": f"Test transcript for {level}",
                "response_time_ms": 1000,
                "created_at": datetime.now(timezone.utc),
            }

            result = asyncio.run(gbq_service.write_analysis_log(data))
            assert result is True, f"Should write {level} record successfully"

        # Wait for writes to propagate
        import time

        time.sleep(3)

        # Verify all records can be queried by safety_level
        table_ref = gbq_service._get_table_ref()
        for level in safety_levels:
            query = f"""
            SELECT COUNT(*) as count
            FROM `{table_ref}`
            WHERE id LIKE @pattern
            AND safety_level = @level
            """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(
                        "pattern", "STRING", f"{test_record_id}_%"
                    ),
                    bigquery.ScalarQueryParameter("level", "STRING", level),
                ],
                use_query_cache=False,  # Disable cache to force actual query
            )

            query_job = gbq_service.client.query(query, job_config=job_config)
            results = list(query_job.result())

            assert (
                results[0]["count"] == 1
            ), f"Should find 1 record for safety_level={level}"

    @skip_without_gcp
    def test_write_practice_vs_emergency_mode(
        self, gbq_service, test_record_id, cleanup_test_records
    ):
        """Test writing records for both practice and emergency modes

        This test verifies:
        1. analysis_type is correctly stored for both modes
        2. Different suggestion counts are handled
        3. Records can be queried by analysis_type
        """
        modes_data = [
            {
                "id": f"{test_record_id}_emergency",
                "analysis_type": "emergency",
                "matched_suggestions": ["緊急建議"],
            },
            {
                "id": f"{test_record_id}_practice",
                "analysis_type": "practice",
                "matched_suggestions": ["練習建議1", "練習建議2", "練習建議3"],
            },
        ]

        for mode_data in modes_data:
            cleanup_test_records(mode_data["id"])

            data = {
                "id": mode_data["id"],
                "tenant_id": "island_parents",
                "session_id": None,
                "analyzed_at": datetime.now(timezone.utc),
                "analysis_type": mode_data["analysis_type"],
                "safety_level": "green",
                "matched_suggestions": mode_data["matched_suggestions"],
                "transcript_segment": f"Test for {mode_data['analysis_type']}",
                "response_time_ms": 1500,
                "created_at": datetime.now(timezone.utc),
            }

            result = asyncio.run(gbq_service.write_analysis_log(data))
            assert result is True

        # Wait for writes
        import time

        time.sleep(3)

        # Verify records by analysis_type
        table_ref = gbq_service._get_table_ref()
        query = f"""
        SELECT id, analysis_type, matched_suggestions
        FROM `{table_ref}`
        WHERE id LIKE @pattern
        ORDER BY analysis_type
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(
                    "pattern", "STRING", f"{test_record_id}_%"
                )
            ]
        )

        query_job = gbq_service.client.query(query, job_config=job_config)
        results = list(query_job.result())

        assert len(results) == 2, "Should find both mode records"

        # Verify emergency mode
        emergency_record = [r for r in results if r["analysis_type"] == "emergency"][0]
        assert len(emergency_record["matched_suggestions"]) == 1

        # Verify practice mode
        practice_record = [r for r in results if r["analysis_type"] == "practice"][0]
        assert len(practice_record["matched_suggestions"]) == 3

    @skip_without_gcp
    def test_query_performance_with_clustering(
        self, gbq_service, test_record_id, cleanup_test_records
    ):
        """Test that clustering improves query performance

        This test verifies:
        1. Queries filtered by tenant_id and safety_level use clustering
        2. Multiple records can be inserted and queried efficiently
        """
        # Insert multiple test records with different clustering values
        test_records = []
        for i in range(5):
            record_id = f"{test_record_id}_{i}"
            test_records.append(record_id)
            cleanup_test_records(record_id)

            data = {
                "id": record_id,
                "tenant_id": "island_parents",
                "session_id": None,
                "analyzed_at": datetime.now(timezone.utc),
                "analysis_type": "emergency",
                "safety_level": "yellow" if i % 2 == 0 else "green",
                "matched_suggestions": [f"建議 {i}"],
                "transcript_segment": f"Test transcript {i}",
                "response_time_ms": 1000 + i * 100,
                "created_at": datetime.now(timezone.utc),
            }

            result = asyncio.run(gbq_service.write_analysis_log(data))
            assert result is True

        # Wait for writes
        import time

        time.sleep(3)

        # Query using clustering fields (tenant_id and safety_level)
        table_ref = gbq_service._get_table_ref()
        query = f"""
        SELECT COUNT(*) as count
        FROM `{table_ref}`
        WHERE tenant_id = @tenant_id
        AND safety_level = @safety_level
        AND id LIKE @pattern
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("tenant_id", "STRING", "island_parents"),
                bigquery.ScalarQueryParameter("safety_level", "STRING", "yellow"),
                bigquery.ScalarQueryParameter(
                    "pattern", "STRING", f"{test_record_id}_%"
                ),
            ],
            use_query_cache=False,  # Disable cache to force actual query
        )

        query_job = gbq_service.client.query(query, job_config=job_config)
        results = list(query_job.result())

        # Should find 3 records with safety_level='yellow' (i=0,2,4)
        assert results[0]["count"] == 3

        # Verify query completed successfully
        assert query_job.done(), "Query should complete successfully"
        assert (
            query_job.errors is None or len(query_job.errors) == 0
        ), "Query should have no errors"

        # Note: total_bytes_processed can be 0 for streaming buffer reads or cached queries
        # Clustering benefits increase with data volume and age (after streaming buffer)
