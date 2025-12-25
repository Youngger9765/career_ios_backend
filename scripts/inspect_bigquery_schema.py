#!/usr/bin/env python3
"""Script to inspect BigQuery table schema

Usage:
    poetry run python scripts/inspect_bigquery_schema.py
"""
import os
import sys

from app.services.gbq_service import gbq_service

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def inspect_schema():
    """Inspect current BigQuery table schema"""
    try:
        table_ref = gbq_service._get_table_ref()
        print(f"\n{'='*80}")
        print(f"Inspecting BigQuery table: {table_ref}")
        print(f"{'='*80}\n")

        # Get table
        table = gbq_service.client.get_table(table_ref)

        # Print schema
        print("Current table schema:")
        print(f"\n{'Field Name':<35} {'Type':<15} {'Mode':<10}")
        print("-" * 80)

        for field in table.schema:
            print(f"{field.name:<35} {field.field_type:<15} {field.mode:<10}")

        print(f"\n{'='*80}")
        print(f"Total fields: {len(table.schema)}")
        print(f"{'='*80}\n")

        # Print partitioning and clustering info
        if table.time_partitioning:
            print(
                f"Partitioning: {table.time_partitioning.type_} on field "
                f"'{table.time_partitioning.field}'"
            )
        if table.clustering_fields:
            print(f"Clustering: {', '.join(table.clustering_fields)}")

        print()

    except Exception as e:
        print(f"Error inspecting table: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    inspect_schema()
