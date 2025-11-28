"""add session name field

Revision ID: add_session_name
Revises: 81cbbd9cf05e
Create Date: 2025-11-29 01:20:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_session_name"
down_revision: Union[str, None] = "81cbbd9cf05e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add name field to sessions table for naming consultation sessions"""
    # Add name column to sessions table (optional field, max 255 chars)
    op.add_column(
        "sessions",
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=True,
            comment="Optional session name for easier identification",
        ),
    )


def downgrade() -> None:
    """Remove name field from sessions table"""
    # Remove name column from sessions table
    op.drop_column("sessions", "name")
