"""drop username unique constraint

Revision ID: 8b5a73721106
Revises: 4a8c177a78f7
Create Date: 2025-12-29 19:26:00.347371

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8b5a73721106"
down_revision: Union[str, None] = "4a8c177a78f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop unique constraint on username column to allow duplicates
    # SQLite: Drop and recreate table without unique constraint (handled by SQLAlchemy)
    # PostgreSQL: Drop the named constraint

    # For PostgreSQL
    with op.batch_alter_table("counselors", schema=None) as batch_op:
        batch_op.drop_constraint("counselors_username_key", type_="unique")


def downgrade() -> None:
    # Re-add unique constraint on username column
    with op.batch_alter_table("counselors", schema=None) as batch_op:
        batch_op.create_unique_constraint("counselors_username_key", ["username"])
