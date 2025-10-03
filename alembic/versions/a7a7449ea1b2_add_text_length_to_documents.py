"""Add text_length to documents

Revision ID: a7a7449ea1b2
Revises: d90dfbb1ef85
Create Date: 2025-10-03 20:02:00.214460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7a7449ea1b2'
down_revision: Union[str, None] = 'd90dfbb1ef85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('text_length', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'text_length')
