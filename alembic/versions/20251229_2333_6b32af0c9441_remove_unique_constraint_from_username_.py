"""remove_unique_constraint_from_username_index

Revision ID: 6b32af0c9441
Revises: 4a8c177a78f7
Create Date: 2025-12-29 23:33:13.442786

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6b32af0c9441"
down_revision: Union[str, None] = "4a8c177a78f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove UNIQUE constraint from ix_counselors_username index.

    This allows the same username to exist across different tenants,
    which is required for multi-tenant isolation.
    """
    # Drop the existing UNIQUE index
    op.drop_index("ix_counselors_username", table_name="counselors")

    # Recreate as a non-unique index
    op.create_index("ix_counselors_username", "counselors", ["username"], unique=False)


def downgrade() -> None:
    """
    Restore UNIQUE constraint to ix_counselors_username index.

    WARNING: This will fail if there are duplicate usernames across tenants.
    """
    # Drop the non-unique index
    op.drop_index("ix_counselors_username", table_name="counselors")

    # Recreate as a UNIQUE index
    op.create_index("ix_counselors_username", "counselors", ["username"], unique=True)
