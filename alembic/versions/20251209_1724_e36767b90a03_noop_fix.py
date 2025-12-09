"""noop migration to fix staging alembic version

Revision ID: e36767b90a03
Revises: 2a680123fbbc
Create Date: 2025-12-09 17:24:00.000000

This is a no-op migration to fix the staging database alembic_version issue.
The category column already exists in the documents table.
"""
from typing import Union

# revision identifiers, used by Alembic.
revision: str = "e36767b90a03"
down_revision: Union[str, None] = "2a680123fbbc"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    # No-op: category column already exists
    pass


def downgrade() -> None:
    # No-op
    pass
