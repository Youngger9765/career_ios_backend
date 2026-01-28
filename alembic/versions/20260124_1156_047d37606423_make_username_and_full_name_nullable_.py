"""make_username_and_full_name_nullable_for_simplified_registration

Revision ID: 047d37606423
Revises: add_session_mode
Create Date: 2026-01-24 11:56:32.114466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '047d37606423'
down_revision: Union[str, None] = 'add_session_mode'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Make username and full_name nullable for simplified registration.
    
    This allows users to register with only email and password,
    and set username/full_name later via profile update.
    """
    # Alter username column to allow NULL
    op.alter_column(
        "counselors",
        "username",
        existing_type=sa.String(),
        nullable=True,
        existing_nullable=False,
    )
    
    # Alter full_name column to allow NULL
    op.alter_column(
        "counselors",
        "full_name",
        existing_type=sa.String(),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    """
    Restore NOT NULL constraint on username and full_name.
    
    WARNING: This will fail if there are any NULL values in these columns.
    You may need to update existing records before downgrading.
    """
    # Restore NOT NULL constraint on username
    op.alter_column(
        "counselors",
        "username",
        existing_type=sa.String(),
        nullable=False,
        existing_nullable=True,
    )
    
    # Restore NOT NULL constraint on full_name
    op.alter_column(
        "counselors",
        "full_name",
        existing_type=sa.String(),
        nullable=False,
        existing_nullable=True,
    )
