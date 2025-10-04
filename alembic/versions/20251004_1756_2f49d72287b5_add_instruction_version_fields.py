"""add_instruction_version_fields_to_evaluation_experiments

Revision ID: 2f49d72287b5
Revises: ba11c6b5e773
Create Date: 2025-10-04 17:56:19.779193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f49d72287b5'
down_revision: Union[str, None] = 'ba11c6b5e773'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add instruction versioning fields to evaluation_experiments
    op.add_column('evaluation_experiments', sa.Column('instruction_version', sa.String(length=50), nullable=True))
    op.add_column('evaluation_experiments', sa.Column('instruction_template', sa.Text(), nullable=True))
    op.add_column('evaluation_experiments', sa.Column('instruction_hash', sa.String(length=64), nullable=True))


def downgrade() -> None:
    # Remove instruction versioning fields
    op.drop_column('evaluation_experiments', 'instruction_hash')
    op.drop_column('evaluation_experiments', 'instruction_template')
    op.drop_column('evaluation_experiments', 'instruction_version')
