"""add_session_mode_column

Revision ID: add_session_mode
Revises: 81a6fb1d8fd5
Create Date: 2026-01-05 12:00:00.000000

Note: Column is named 'session_mode' instead of 'mode' to avoid conflict
with PostgreSQL's aggregate function 'mode()'.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_session_mode"
down_revision: Union[str, None] = "81a6fb1d8fd5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add session_mode column to sessions table for Island Parents
    # Named 'session_mode' to avoid PostgreSQL reserved word conflict with mode()
    op.add_column(
        "sessions", sa.Column("session_mode", sa.String(length=20), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("sessions", "session_mode")
