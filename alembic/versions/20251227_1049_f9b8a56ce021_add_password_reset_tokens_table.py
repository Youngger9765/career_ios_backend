"""add password reset tokens table

Revision ID: f9b8a56ce021
Revises: 5ae92c306158
Create Date: 2025-12-27 10:49:20.684707

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9b8a56ce021"
down_revision: Union[str, None] = "5ae92c306158"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("request_ip", sa.String(), nullable=True),
        sa.Column("used_ip", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_password_reset_tokens_token"),
        "password_reset_tokens",
        ["token"],
        unique=True,
    )
    op.create_index(
        op.f("ix_password_reset_tokens_email"),
        "password_reset_tokens",
        ["email"],
        unique=False,
    )
    op.create_index(
        op.f("ix_password_reset_tokens_tenant_id"),
        "password_reset_tokens",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_password_reset_tokens_tenant_id"), table_name="password_reset_tokens"
    )
    op.drop_index(
        op.f("ix_password_reset_tokens_email"), table_name="password_reset_tokens"
    )
    op.drop_index(
        op.f("ix_password_reset_tokens_token"), table_name="password_reset_tokens"
    )
    op.drop_table("password_reset_tokens")
