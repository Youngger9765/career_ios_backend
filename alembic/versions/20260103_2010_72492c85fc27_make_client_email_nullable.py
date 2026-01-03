"""make_client_email_nullable

Revision ID: 72492c85fc27
Revises: 6b32af0c9441
Create Date: 2026-01-03 20:10:23.243861

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "72492c85fc27"
down_revision: Union[str, None] = "6b32af0c9441"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make email column nullable for Island Parents (親子版)
    op.alter_column("clients", "email", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    # Revert: make email column NOT NULL again
    op.alter_column("clients", "email", existing_type=sa.String(), nullable=False)
