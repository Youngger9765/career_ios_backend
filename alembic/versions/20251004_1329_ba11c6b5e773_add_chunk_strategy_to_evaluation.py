"""add_chunk_strategy_to_evaluation_experiments

Revision ID: ba11c6b5e773
Revises: a7a7449ea1b2
Create Date: 2025-10-04 13:29:03.528493

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba11c6b5e773'
down_revision: Union[str, None] = 'a7a7449ea1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add chunk_strategy column to evaluation_experiments table
    op.add_column('evaluation_experiments',
                  sa.Column('chunk_strategy', sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Remove chunk_strategy column
    op.drop_column('evaluation_experiments', 'chunk_strategy')
