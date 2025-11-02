"""add markdown fields to reports

Revision ID: 20251102_1127
Revises: d1fdb8fced5e
Create Date: 2025-11-02 11:27:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251102_1127'
down_revision: Union[str, None] = 'd1fdb8fced5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add markdown fields to reports table"""
    op.add_column('reports', sa.Column('content_markdown', sa.Text(), nullable=True))
    op.add_column('reports', sa.Column('edited_content_markdown', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove markdown fields from reports table"""
    op.drop_column('reports', 'edited_content_markdown')
    op.drop_column('reports', 'content_markdown')
