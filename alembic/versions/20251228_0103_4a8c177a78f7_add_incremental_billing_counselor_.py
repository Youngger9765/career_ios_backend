"""Add incremental billing: counselor available_credits, creditlog polymorphic fields

Revision ID: 4a8c177a78f7
Revises: 02c909267dd6
Create Date: 2025-12-28 01:03:30.070124

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4a8c177a78f7"
down_revision: Union[str, None] = "02c909267dd6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # Part 1: Counselor Table - Simplify to available_credits only
    # ============================================================

    # 1. Add available_credits column (Float, default 1000.0)
    op.add_column(
        "counselors",
        sa.Column(
            "available_credits",
            sa.Float(),
            nullable=True,
            comment="Available credits (current balance)",
        ),
    )

    # 2. Migrate data: available_credits = total_credits - credits_used
    op.execute(
        """
        UPDATE counselors
        SET available_credits = COALESCE(total_credits, 0) - COALESCE(credits_used, 0)
    """
    )

    # 3. Make available_credits non-nullable after data migration
    op.alter_column(
        "counselors", "available_credits", nullable=False, server_default="1000.0"
    )

    # 4. Drop old columns
    op.drop_column("counselors", "total_credits")
    op.drop_column("counselors", "credits_used")

    # ============================================================
    # Part 2: CreditLog Table - Add polymorphic fields
    # ============================================================

    # 1. Add polymorphic association fields
    op.add_column(
        "credit_logs",
        sa.Column(
            "resource_type",
            sa.String(length=50),
            nullable=True,
            comment="Resource type: 'session', 'translation', 'ocr', 'report', etc.",
        ),
    )
    op.add_column(
        "credit_logs",
        sa.Column(
            "resource_id",
            sa.String(),
            nullable=True,
            comment="Resource ID (UUID as string, polymorphic)",
        ),
    )

    # 2. Migrate existing session_id to polymorphic fields
    op.execute(
        """
        UPDATE credit_logs
        SET resource_type = 'session',
            resource_id = session_id::text
        WHERE session_id IS NOT NULL
    """
    )

    # 3. Change credits_delta from Integer to Float
    op.alter_column(
        "credit_logs",
        "credits_delta",
        existing_type=sa.INTEGER(),
        type_=sa.Float(),
        existing_nullable=False,
    )

    # 4. Create indexes for polymorphic fields
    op.create_index("ix_credit_logs_resource_type", "credit_logs", ["resource_type"])
    op.create_index("ix_credit_logs_resource_id", "credit_logs", ["resource_id"])
    op.create_index(
        "ix_credit_logs_resource", "credit_logs", ["resource_type", "resource_id"]
    )

    # 5. Drop old session_id foreign key and column
    op.drop_constraint("credit_logs_session_id_fkey", "credit_logs", type_="foreignkey")
    op.drop_index("ix_credit_logs_session_id", table_name="credit_logs")
    op.drop_column("credit_logs", "session_id")


def downgrade() -> None:
    # ============================================================
    # Part 1: CreditLog Table - Restore session_id
    # ============================================================

    # 1. Restore session_id column
    op.add_column("credit_logs", sa.Column("session_id", sa.UUID(), nullable=True))

    # 2. Migrate polymorphic fields back to session_id
    op.execute(
        """
        UPDATE credit_logs
        SET session_id = resource_id::uuid
        WHERE resource_type = 'session' AND resource_id IS NOT NULL
    """
    )

    # 3. Restore foreign key and index
    op.create_index("ix_credit_logs_session_id", "credit_logs", ["session_id"])
    op.create_foreign_key(
        "credit_logs_session_id_fkey",
        "credit_logs",
        "sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 4. Drop polymorphic indexes and columns
    op.drop_index("ix_credit_logs_resource", table_name="credit_logs")
    op.drop_index("ix_credit_logs_resource_id", table_name="credit_logs")
    op.drop_index("ix_credit_logs_resource_type", table_name="credit_logs")
    op.drop_column("credit_logs", "resource_id")
    op.drop_column("credit_logs", "resource_type")

    # 5. Change credits_delta back to Integer
    op.alter_column(
        "credit_logs",
        "credits_delta",
        existing_type=sa.Float(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )

    # ============================================================
    # Part 2: Counselor Table - Restore total_credits and credits_used
    # ============================================================

    # 1. Add back total_credits and credits_used
    op.add_column(
        "counselors",
        sa.Column("total_credits", sa.INTEGER(), nullable=True, server_default="0"),
    )
    op.add_column(
        "counselors",
        sa.Column("credits_used", sa.INTEGER(), nullable=True, server_default="0"),
    )

    # 2. Migrate data back (best effort - assumes no credits were added/used during upgrade)
    # Note: This is lossy - we can only restore available_credits as total_credits, credits_used = 0
    op.execute(
        """
        UPDATE counselors
        SET total_credits = CAST(COALESCE(available_credits, 0) AS INTEGER),
            credits_used = 0
    """
    )

    # 3. Make columns non-nullable
    op.alter_column("counselors", "total_credits", nullable=False)
    op.alter_column("counselors", "credits_used", nullable=False)

    # 4. Drop available_credits
    op.drop_column("counselors", "available_credits")
