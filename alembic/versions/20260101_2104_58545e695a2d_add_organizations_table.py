"""add_organizations_table

Revision ID: 58545e695a2d
Revises: 6b32af0c9441
Create Date: 2026-01-01 21:04:46.056783

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58545e695a2d"
down_revision: Union[str, None] = "6b32af0c9441"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "tenant_id",
            sa.String(),
            nullable=False,
            comment="Unique tenant identifier (e.g., school_abc, practice_xyz)",
        ),
        sa.Column(
            "name", sa.String(), nullable=False, comment="Organization display name"
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Organization description or notes",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
            comment="Whether organization is active",
        ),
        sa.Column(
            "counselor_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Cached count of active counselors",
        ),
        sa.Column(
            "client_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Cached count of active clients",
        ),
        sa.Column(
            "session_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Cached count of total sessions",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name=op.f("uq_organizations_tenant_id")),
    )

    # Create index on tenant_id for faster lookups
    op.create_index(
        op.f("ix_organizations_tenant_id"), "organizations", ["tenant_id"], unique=True
    )
    op.create_index(
        op.f("ix_organizations_is_active"), "organizations", ["is_active"], unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_organizations_is_active"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_tenant_id"), table_name="organizations")

    # Drop table
    op.drop_table("organizations")
