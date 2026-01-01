#!/usr/bin/env python3
"""
Fix alembic_version table by removing orphaned revision 58545e695a2d

This script removes the organization management migration revision that was
deleted from codebase but still exists in the database.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text  # noqa: E402

from app.core.config import settings  # noqa: E402


def fix_alembic_version():
    """Remove orphaned revision 58545e695a2d and set to correct revision"""
    # Use DATABASE_URL_DIRECT for direct connection
    database_url = (
        os.getenv("DATABASE_URL_DIRECT")
        or os.getenv("DATABASE_URL")
        or settings.DATABASE_URL
    )

    print("🔧 Connecting to database to fix alembic_version table...")
    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check current revision
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        current_revision = result.scalar()
        print(f"📊 Current database revision: {current_revision}")

        if current_revision == "58545e695a2d":
            print("⚠️  Found orphaned revision 58545e695a2d (organization management)")
            print("🔄 Updating to correct revision: 6b32af0c9441")

            # Update to correct revision (latest migration in codebase)
            conn.execute(
                text("UPDATE alembic_version SET version_num = :new_revision"),
                {"new_revision": "6b32af0c9441"},
            )
            conn.commit()

            print("✅ Successfully updated alembic_version to 6b32af0c9441")
        else:
            print("✅ Database revision is correct, no fix needed")


if __name__ == "__main__":
    try:
        fix_alembic_version()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error fixing alembic_version: {e}")
        sys.exit(1)
