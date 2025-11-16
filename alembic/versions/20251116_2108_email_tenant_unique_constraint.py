"""email tenant unique constraint

Revision ID: 20251116_2108
Revises: 20251116_2053
Create Date: 2025-11-16 21:08:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251116_2108'
down_revision: Union[str, None] = '20251116_2053'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Change counselor email from globally unique to unique per tenant

    This allows the same email to exist across different tenants
    (email + tenant_id) becomes the unique combination
    """

    # Drop the existing unique constraint on email
    op.drop_constraint('counselors_email_key', 'counselors', type_='unique')

    # Create new unique constraint on (email, tenant_id) combination
    op.create_unique_constraint(
        'uq_counselor_email_tenant',
        'counselors',
        ['email', 'tenant_id']
    )


def downgrade() -> None:
    """
    Revert back to globally unique email

    WARNING: This will fail if there are duplicate emails across tenants
    """

    # Drop the combined unique constraint
    op.drop_constraint('uq_counselor_email_tenant', 'counselors', type_='unique')

    # Restore unique constraint on email alone
    op.create_unique_constraint('counselors_email_key', 'counselors', ['email'])
