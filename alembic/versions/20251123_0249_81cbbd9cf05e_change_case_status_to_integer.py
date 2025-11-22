"""change_case_status_to_integer

Revision ID: 81cbbd9cf05e
Revises: d7c037c2c1d9
Create Date: 2025-11-23 02:49:06.794386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '81cbbd9cf05e'
down_revision: Union[str, None] = 'd7c037c2c1d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Convert Case.status from ENUM/String to Integer
    Mapping:
    - 'ACTIVE' → 0 (NOT_STARTED)
    - 'COMPLETED' → 2 (COMPLETED)
    - 'SUSPENDED' → 1 (IN_PROGRESS)
    - 'REFERRED' → 2 (COMPLETED)
    """
    # Create a temporary integer column
    op.add_column('cases', sa.Column('status_new', sa.Integer(), nullable=True))

    # Migrate data from old enum status to new integer status
    # Note: The status column is currently a PostgreSQL ENUM or Integer
    op.execute("""
        UPDATE cases
        SET status_new = CASE status::text
            WHEN 'ACTIVE' THEN 0
            WHEN 'NOT_STARTED' THEN 0
            WHEN 'IN_PROGRESS' THEN 1
            WHEN 'COMPLETED' THEN 2
            WHEN 'SUSPENDED' THEN 1
            WHEN 'REFERRED' THEN 2
            WHEN '0' THEN 0
            WHEN '1' THEN 1
            WHEN '2' THEN 2
            ELSE 0  -- Default to NOT_STARTED
        END
    """)

    # Drop old status column
    op.drop_column('cases', 'status')

    # Rename new column to status
    op.alter_column('cases', 'status_new', new_column_name='status')

    # Set NOT NULL constraint and default
    op.alter_column('cases', 'status', nullable=False, server_default='0')


def downgrade() -> None:
    """
    Revert Case.status from Integer back to ENUM/String
    """
    # Create temporary string column
    op.add_column('cases', sa.Column('status_old', sa.String(), nullable=True))

    # Migrate data back from integer to string
    op.execute("""
        UPDATE cases
        SET status_old = CASE
            WHEN status = 0 THEN 'NOT_STARTED'
            WHEN status = 1 THEN 'IN_PROGRESS'
            WHEN status = 2 THEN 'COMPLETED'
            ELSE 'NOT_STARTED'
        END
    """)

    # Drop integer status column
    op.drop_column('cases', 'status')

    # Rename old column back to status
    op.alter_column('cases', 'status_old', new_column_name='status')
