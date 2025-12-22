"""Add universal credit system (counselor credits, credit_rates, credit_logs)

Revision ID: 5ae92c306158
Revises: e36767b90a03
Create Date: 2025-12-20 18:29:49.657962

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5ae92c306158"
down_revision: Union[str, None] = "e36767b90a03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add credit system fields to counselors table
    op.add_column(
        "counselors",
        sa.Column("phone", sa.String(), nullable=True, comment="Contact phone number"),
    )
    op.add_column(
        "counselors",
        sa.Column(
            "total_credits",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Total credits purchased/added",
        ),
    )
    op.add_column(
        "counselors",
        sa.Column(
            "credits_used",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Credits consumed/used",
        ),
    )
    op.add_column(
        "counselors",
        sa.Column(
            "subscription_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Subscription expiry date",
        ),
    )

    # Create credit_rates table
    op.create_table(
        "credit_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "rule_name",
            sa.String(50),
            nullable=False,
            comment="Rule identifier (e.g., voice_call, text_session)",
        ),
        sa.Column(
            "calculation_method",
            sa.String(20),
            nullable=False,
            server_default="per_second",
            comment="Calculation method: per_second, per_minute, tiered",
        ),
        sa.Column(
            "rate_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="JSON configuration for rate calculation",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="Version number for this rule",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Is this version active",
        ),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this rate becomes effective",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rule_name", "version", name="uq_credit_rate_rule_version"),
    )
    op.create_index("ix_credit_rates_rule_name", "credit_rates", ["rule_name"])
    op.create_index("ix_credit_rates_is_active", "credit_rates", ["is_active"])
    op.create_index(
        "ix_credit_rates_active_lookup",
        "credit_rates",
        ["rule_name", "is_active", "version"],
    )

    # Create credit_logs table
    op.create_table(
        "credit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "counselor_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Counselor who owns this transaction",
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Related session (if applicable)",
        ),
        sa.Column(
            "credits_delta",
            sa.Integer(),
            nullable=False,
            comment="Credit change (positive = added, negative = used)",
        ),
        sa.Column(
            "transaction_type",
            sa.String(20),
            nullable=False,
            comment="Type: purchase, usage, admin_adjustment, refund",
        ),
        sa.Column(
            "raw_data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Raw data (e.g., duration_seconds for usage)",
        ),
        sa.Column(
            "rate_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Rate configuration used for this transaction",
        ),
        sa.Column(
            "calculation_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Detailed calculation breakdown",
        ),
        sa.ForeignKeyConstraint(
            ["counselor_id"], ["counselors.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_logs_counselor_id", "credit_logs", ["counselor_id"])
    op.create_index("ix_credit_logs_session_id", "credit_logs", ["session_id"])
    op.create_index(
        "ix_credit_logs_transaction_type", "credit_logs", ["transaction_type"]
    )
    op.create_index(
        "ix_credit_logs_counselor_type",
        "credit_logs",
        ["counselor_id", "transaction_type"],
    )
    op.create_index("ix_credit_logs_created_at", "credit_logs", ["created_at"])


def downgrade() -> None:
    # Drop credit_logs table
    op.drop_index("ix_credit_logs_created_at", table_name="credit_logs")
    op.drop_index("ix_credit_logs_counselor_type", table_name="credit_logs")
    op.drop_index("ix_credit_logs_transaction_type", table_name="credit_logs")
    op.drop_index("ix_credit_logs_session_id", table_name="credit_logs")
    op.drop_index("ix_credit_logs_counselor_id", table_name="credit_logs")
    op.drop_table("credit_logs")

    # Drop credit_rates table
    op.drop_index("ix_credit_rates_active_lookup", table_name="credit_rates")
    op.drop_index("ix_credit_rates_is_active", table_name="credit_rates")
    op.drop_index("ix_credit_rates_rule_name", table_name="credit_rates")
    op.drop_table("credit_rates")

    # Remove credit fields from counselors table
    op.drop_column("counselors", "subscription_expires_at")
    op.drop_column("counselors", "credits_used")
    op.drop_column("counselors", "total_credits")
    op.drop_column("counselors", "phone")
