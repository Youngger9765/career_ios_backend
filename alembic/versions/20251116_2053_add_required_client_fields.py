"""add required client fields

Revision ID: 20251116_2053
Revises: 20251102_1127
Create Date: 2025-11-16 20:53:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251116_2053'
down_revision: Union[str, None] = '20251102_1127'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add required and optional fields to clients table"""

    # Add new required fields (nullable temporarily for existing data)
    op.add_column('clients', sa.Column('email', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('identity_option', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('current_status', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('phone', sa.String(), nullable=True))

    # Add optional fields
    op.add_column('clients', sa.Column('current_job', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('career_status', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('has_consultation_history', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('has_mental_health_history', sa.String(), nullable=True))

    # Create index on email
    op.create_index(op.f('ix_clients_email'), 'clients', ['email'], unique=False)

    # Update existing rows with default values for required fields
    op.execute("""
        UPDATE clients
        SET
            email = COALESCE(email, code || '@temp.example.com'),
            identity_option = COALESCE(identity_option, '其他'),
            current_status = COALESCE(current_status, '未填寫'),
            phone = COALESCE(phone, '未提供')
        WHERE email IS NULL OR identity_option IS NULL OR current_status IS NULL OR phone IS NULL
    """)

    # Now make gender and birth_date NOT NULL if they aren't already
    # (they should already be set based on your model, but this ensures it)
    op.alter_column('clients', 'gender',
                    existing_type=sa.String(),
                    nullable=False)
    op.alter_column('clients', 'birth_date',
                    existing_type=sa.Date(),
                    nullable=False)

    # Make the new required fields NOT NULL
    op.alter_column('clients', 'email',
                    existing_type=sa.String(),
                    nullable=False)
    op.alter_column('clients', 'identity_option',
                    existing_type=sa.String(),
                    nullable=False)
    op.alter_column('clients', 'current_status',
                    existing_type=sa.String(),
                    nullable=False)
    op.alter_column('clients', 'phone',
                    existing_type=sa.String(),
                    nullable=False)


def downgrade() -> None:
    """Remove required and optional fields from clients table"""

    # Drop index
    op.drop_index(op.f('ix_clients_email'), table_name='clients')

    # Drop all new columns
    op.drop_column('clients', 'has_mental_health_history')
    op.drop_column('clients', 'has_consultation_history')
    op.drop_column('clients', 'career_status')
    op.drop_column('clients', 'current_job')
    op.drop_column('clients', 'phone')
    op.drop_column('clients', 'current_status')
    op.drop_column('clients', 'identity_option')
    op.drop_column('clients', 'email')

    # Revert gender and birth_date to nullable (if they were before)
    op.alter_column('clients', 'gender',
                    existing_type=sa.String(),
                    nullable=True)
    op.alter_column('clients', 'birth_date',
                    existing_type=sa.Date(),
                    nullable=True)
