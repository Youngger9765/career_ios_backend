"""add email_verified to counselors

Revision ID: 9496531fd27a
Revises: a477d966c694
Create Date: 2026-01-31 20:33:56.463381

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9496531fd27a'
down_revision: Union[str, None] = 'a477d966c694'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add email_verified column to counselors table
    op.add_column(
        'counselors',
        sa.Column(
            'email_verified',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
            comment='Email verification status'
        )
    )


def downgrade() -> None:
    # Remove email_verified column from counselors table
    op.drop_column('counselors', 'email_verified')
