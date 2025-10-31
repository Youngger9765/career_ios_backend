"""ensure_reportstatus_enum

Revision ID: bc4b22d2cb16
Revises: c6001e48c0ff
Create Date: 2025-10-30 00:46:02.408248

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc4b22d2cb16'
down_revision: Union[str, None] = 'c6001e48c0ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create reportstatus enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE reportstatus AS ENUM (
                'processing',
                'draft',
                'pending_review',
                'approved',
                'rejected',
                'failed',
                'archived'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)


def downgrade() -> None:
    # Don't drop the enum in downgrade to avoid breaking existing data
    pass
