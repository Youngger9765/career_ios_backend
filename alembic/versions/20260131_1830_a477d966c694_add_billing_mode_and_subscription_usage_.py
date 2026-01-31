"""add billing mode and subscription usage tracking

Revision ID: a477d966c694
Revises: 047d37606423
Create Date: 2026-01-31 18:30:20.032081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a477d966c694'
down_revision: Union[str, None] = '047d37606423'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type
    billing_mode_enum = postgresql.ENUM('prepaid', 'subscription', name='billingmode')
    billing_mode_enum.create(op.get_bind())

    # Add billing_mode column (default to prepaid for existing users)
    op.add_column('counselors', sa.Column(
        'billing_mode',
        sa.Enum('prepaid', 'subscription', name='billingmode'),
        nullable=False,
        server_default='prepaid',
        comment='Billing mode: prepaid (credit-based) or subscription (time-limited)'
    ))
    op.create_index('ix_counselors_billing_mode', 'counselors', ['billing_mode'])

    # Add subscription usage tracking columns
    op.add_column('counselors', sa.Column(
        'monthly_usage_limit_minutes',
        sa.Integer(),
        nullable=True,
        server_default='360',
        comment='Monthly usage limit in minutes (subscription mode only), 6 hours = 360 min'
    ))
    op.add_column('counselors', sa.Column(
        'monthly_minutes_used',
        sa.Integer(),
        nullable=True,
        server_default='0',
        comment='Minutes used in current billing period (subscription mode only)'
    ))
    op.add_column('counselors', sa.Column(
        'usage_period_start',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='Start of current 30-day usage period (subscription mode only)'
    ))


def downgrade() -> None:
    op.drop_index('ix_counselors_billing_mode', 'counselors')
    op.drop_column('counselors', 'usage_period_start')
    op.drop_column('counselors', 'monthly_minutes_used')
    op.drop_column('counselors', 'monthly_usage_limit_minutes')
    op.drop_column('counselors', 'billing_mode')

    billing_mode_enum = postgresql.ENUM('prepaid', 'subscription', name='billingmode')
    billing_mode_enum.drop(op.get_bind())
