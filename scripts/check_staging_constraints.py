"""
Check counselors table constraints in staging database.
"""
from sqlalchemy import text

from app.core.database import engine


def check_constraints():
    """Check all constraints and indexes on counselors table"""

    constraint_query = text(
        """
        SELECT
            con.conname AS constraint_name,
            CASE con.contype
                WHEN 'u' THEN 'UNIQUE'
                WHEN 'p' THEN 'PRIMARY KEY'
                WHEN 'f' THEN 'FOREIGN KEY'
                WHEN 'c' THEN 'CHECK'
                ELSE con.contype::text
            END AS constraint_type,
            pg_get_constraintdef(con.oid) AS definition
        FROM pg_constraint con
        JOIN pg_class rel ON rel.oid = con.conrelid
        JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
        WHERE rel.relname = 'counselors'
        ORDER BY con.conname;
    """
    )

    index_query = text(
        """
        SELECT
            indexname,
            indexdef
        FROM pg_indexes
        WHERE tablename = 'counselors'
        ORDER BY indexname;
    """
    )

    print("=" * 80)
    print("COUNSELORS TABLE CONSTRAINTS")
    print("=" * 80)

    with engine.begin() as conn:
        # Check constraints
        result = conn.execute(constraint_query)
        constraints = result.fetchall()

        print("\n📋 Constraints:")
        print("-" * 80)
        for row in constraints:
            print(f"  • {row.constraint_name}")
            print(f"    Type: {row.constraint_type}")
            print(f"    Definition: {row.definition}")
            print()

        # Check indexes
        result = conn.execute(index_query)
        indexes = result.fetchall()

        print("\n📊 Indexes:")
        print("-" * 80)
        for row in indexes:
            print(f"  • {row.indexname}")
            print(f"    {row.indexdef}")
            print()

    print("=" * 80)


if __name__ == "__main__":
    check_constraints()
