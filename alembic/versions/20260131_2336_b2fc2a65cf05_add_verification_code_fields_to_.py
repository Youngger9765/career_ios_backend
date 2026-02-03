"""add verification code fields to password_reset_tokens

Revision ID: b2fc2a65cf05
Revises: 9496531fd27a
Create Date: 2026-01-31 23:36:16.286016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2fc2a65cf05'
down_revision: Union[str, None] = '9496531fd27a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for verification code system
    op.add_column('password_reset_tokens', sa.Column('verification_code', sa.String(length=6), nullable=True))
    op.add_column('password_reset_tokens', sa.Column('verify_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('password_reset_tokens', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('password_reset_tokens', sa.Column('code_expires_at', sa.DateTime(timezone=True), nullable=True))

    # Add index on verification_code for faster lookups
    op.create_index('ix_password_reset_tokens_verification_code', 'password_reset_tokens', ['verification_code'])


def downgrade() -> None:
    op.drop_index('ix_password_reset_tokens_verification_code', table_name='password_reset_tokens')
    op.drop_column('password_reset_tokens', 'code_expires_at')
    op.drop_column('password_reset_tokens', 'locked_until')
    op.drop_column('password_reset_tokens', 'verify_attempts')
    op.drop_column('password_reset_tokens', 'verification_code')
