"""add_session_scenario_fields

Revision ID: 81a6fb1d8fd5
Revises: 72492c85fc27
Create Date: 2026-01-03 20:59:02.658611

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "81a6fb1d8fd5"
down_revision: Union[str, None] = "72492c85fc27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add scenario fields to sessions table for Island Parents
    op.add_column(
        "sessions", sa.Column("scenario", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "sessions", sa.Column("scenario_description", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("sessions", "scenario_description")
    op.drop_column("sessions", "scenario")
