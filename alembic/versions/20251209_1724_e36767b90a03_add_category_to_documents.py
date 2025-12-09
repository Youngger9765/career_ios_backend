"""add category to documents

Revision ID: e36767b90a03
Revises: 2a680123fbbc
Create Date: 2025-12-09 17:24:00.000000

"""
from typing import Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e36767b90a03"
down_revision: Union[str, None] = "2a680123fbbc"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    # Add category column to documents table
    # Using IF NOT EXISTS for idempotency (safe to run even if column exists)
    op.execute(
        """
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS category VARCHAR DEFAULT 'general'
    """
    )


def downgrade() -> None:
    # Remove category column from documents table
    # Using IF EXISTS for idempotency
    op.execute(
        """
        ALTER TABLE documents
        DROP COLUMN IF EXISTS category
    """
    )
