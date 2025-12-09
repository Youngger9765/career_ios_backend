"""rag_initial_schema

Revision ID: 90d014280e06
Revises:
Create Date: 2025-11-18 15:24:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "90d014280e06"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ============================================================================
    # RAG MODELS - Document processing and retrieval tables
    # ============================================================================

    # datasources table
    op.create_table(
        "datasources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_datasources_id"), "datasources", ["id"], unique=False)

    # documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("datasource_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("text_length", sa.Integer(), nullable=True),
        sa.Column("meta_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["datasource_id"], ["datasources.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_documents_datasource_id"), "documents", ["datasource_id"], unique=False
    )
    op.create_index(op.f("ix_documents_id"), "documents", ["id"], unique=False)

    # chunks table
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doc_id", sa.Integer(), nullable=False),
        sa.Column("chunk_strategy", sa.String(length=100), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("meta_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["doc_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chunks_chunk_strategy"), "chunks", ["chunk_strategy"], unique=False
    )
    op.create_index(op.f("ix_chunks_doc_id"), "chunks", ["doc_id"], unique=False)
    op.create_index(op.f("ix_chunks_id"), "chunks", ["id"], unique=False)

    # embeddings table
    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id"),
    )
    op.create_index(
        op.f("ix_embeddings_chunk_id"), "embeddings", ["chunk_id"], unique=True
    )
    op.create_index(op.f("ix_embeddings_id"), "embeddings", ["id"], unique=False)

    # collections table
    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_collections_id"), "collections", ["id"], unique=False)

    # collection_items table
    op.create_table(
        "collection_items",
        sa.Column("collection_id", sa.Integer(), nullable=False),
        sa.Column("doc_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["collections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["doc_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("collection_id", "doc_id"),
    )
    op.create_index(
        op.f("ix_collection_items_doc_id"), "collection_items", ["doc_id"], unique=False
    )

    # agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("active_version_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_agents_id"), "agents", ["id"], unique=False)
    op.create_index(op.f("ix_agents_slug"), "agents", ["slug"], unique=True)
    op.create_index(op.f("ix_agents_status"), "agents", ["status"], unique=False)

    # agent_versions table
    op.create_table(
        "agent_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=50), nullable=True),
        sa.Column("config_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_versions_agent_id"), "agent_versions", ["agent_id"], unique=False
    )
    op.create_index(
        op.f("ix_agent_versions_id"), "agent_versions", ["id"], unique=False
    )

    # Add foreign key for agents.active_version_id
    op.create_foreign_key(
        "fk_agents_active_version",
        "agents",
        "agent_versions",
        ["active_version_id"],
        ["id"],
    )

    # chat_logs table
    op.create_table(
        "chat_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("version_id", sa.Integer(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column(
            "citations_json", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["version_id"], ["agent_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_logs_agent_id"), "chat_logs", ["agent_id"], unique=False
    )
    op.create_index(
        op.f("ix_chat_logs_created_at"), "chat_logs", ["created_at"], unique=False
    )
    op.create_index(op.f("ix_chat_logs_id"), "chat_logs", ["id"], unique=False)

    # evaluation_experiments table
    op.create_table(
        "evaluation_experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("experiment_type", sa.String(length=50), nullable=False),
        sa.Column("chunking_method", sa.String(length=50), nullable=True),
        sa.Column("chunk_size", sa.Integer(), nullable=True),
        sa.Column("chunk_overlap", sa.Integer(), nullable=True),
        sa.Column("chunk_strategy", sa.String(length=100), nullable=True),
        sa.Column("config_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("instruction_version", sa.String(length=50), nullable=True),
        sa.Column("instruction_template", sa.Text(), nullable=True),
        sa.Column("instruction_hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("mlflow_run_id", sa.String(length=255), nullable=True),
        sa.Column("mlflow_experiment_id", sa.String(length=255), nullable=True),
        sa.Column("total_queries", sa.Integer(), nullable=True),
        sa.Column("avg_faithfulness", sa.Float(), nullable=True),
        sa.Column("avg_answer_relevancy", sa.Float(), nullable=True),
        sa.Column("avg_context_recall", sa.Float(), nullable=True),
        sa.Column("avg_context_precision", sa.Float(), nullable=True),
        sa.Column("avg_latency_ms", sa.Float(), nullable=True),
        sa.Column("total_cost", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # evaluation_results table
    op.create_table(
        "evaluation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("contexts", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("ground_truth", sa.Text(), nullable=True),
        sa.Column("faithfulness", sa.Float(), nullable=True),
        sa.Column("answer_relevancy", sa.Float(), nullable=True),
        sa.Column("context_recall", sa.Float(), nullable=True),
        sa.Column("context_precision", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("retrieval_latency_ms", sa.Float(), nullable=True),
        sa.Column("generation_latency_ms", sa.Float(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column(
            "metadata_json", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["evaluation_experiments.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # evaluation_testsets table
    op.create_table(
        "evaluation_testsets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("test_cases", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("total_cases", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # document_quality_metrics table
    op.create_table(
        "document_quality_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("content_accuracy", sa.Float(), nullable=True),
        sa.Column("structural_score", sa.Float(), nullable=True),
        sa.Column("expertise_depth", sa.Float(), nullable=True),
        sa.Column("readability_score", sa.Float(), nullable=True),
        sa.Column(
            "topic_coverage", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "knowledge_depth", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("evaluated_by", sa.String(length=100), nullable=True),
        sa.Column("evaluation_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # pipeline_runs table
    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("steps_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pipeline_runs_id"), "pipeline_runs", ["id"], unique=False)
    op.create_index(
        op.f("ix_pipeline_runs_status"), "pipeline_runs", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_pipeline_runs_target_id"), "pipeline_runs", ["target_id"], unique=False
    )

    # ============================================================================
    # Enable Row Level Security (RLS) on all RAG tables
    # ============================================================================

    # RAG tables are shared resources or inherit access via FK relationships
    # Enable RLS and create permissive policies for application-level access control

    rag_tables = [
        "datasources",
        "documents",
        "chunks",
        "embeddings",
        "collections",
        "collection_items",
        "agents",
        "agent_versions",
        "chat_logs",
        "evaluation_experiments",
        "evaluation_results",
        "evaluation_testsets",
        "document_quality_metrics",
        "pipeline_runs",
    ]

    for table in rag_tables:
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # Create permissive policy (access controlled at application level)
        op.execute(
            f"""
            CREATE POLICY allow_authenticated_access ON {table}
            FOR ALL
            USING (true)
            WITH CHECK (true)
        """
        )


def downgrade() -> None:
    # Drop all RAG tables in reverse order
    op.drop_index(op.f("ix_pipeline_runs_target_id"), table_name="pipeline_runs")
    op.drop_index(op.f("ix_pipeline_runs_status"), table_name="pipeline_runs")
    op.drop_index(op.f("ix_pipeline_runs_id"), table_name="pipeline_runs")
    op.drop_table("pipeline_runs")

    op.drop_table("document_quality_metrics")
    op.drop_table("evaluation_testsets")
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_experiments")

    op.drop_index(op.f("ix_chat_logs_id"), table_name="chat_logs")
    op.drop_index(op.f("ix_chat_logs_created_at"), table_name="chat_logs")
    op.drop_index(op.f("ix_chat_logs_agent_id"), table_name="chat_logs")
    op.drop_table("chat_logs")

    op.drop_constraint("fk_agents_active_version", "agents", type_="foreignkey")

    op.drop_index(op.f("ix_agent_versions_id"), table_name="agent_versions")
    op.drop_index(op.f("ix_agent_versions_agent_id"), table_name="agent_versions")
    op.drop_table("agent_versions")

    op.drop_index(op.f("ix_agents_status"), table_name="agents")
    op.drop_index(op.f("ix_agents_slug"), table_name="agents")
    op.drop_index(op.f("ix_agents_id"), table_name="agents")
    op.drop_table("agents")

    op.drop_index(op.f("ix_collection_items_doc_id"), table_name="collection_items")
    op.drop_table("collection_items")

    op.drop_index(op.f("ix_collections_id"), table_name="collections")
    op.drop_table("collections")

    op.drop_index(op.f("ix_embeddings_id"), table_name="embeddings")
    op.drop_index(op.f("ix_embeddings_chunk_id"), table_name="embeddings")
    op.drop_table("embeddings")

    op.drop_index(op.f("ix_chunks_id"), table_name="chunks")
    op.drop_index(op.f("ix_chunks_doc_id"), table_name="chunks")
    op.drop_index(op.f("ix_chunks_chunk_strategy"), table_name="chunks")
    op.drop_table("chunks")

    op.drop_index(op.f("ix_documents_id"), table_name="documents")
    op.drop_index(op.f("ix_documents_datasource_id"), table_name="documents")
    op.drop_table("documents")

    op.drop_index(op.f("ix_datasources_id"), table_name="datasources")
    op.drop_table("datasources")

    # Drop pgvector extension
    op.execute("DROP EXTENSION IF EXISTS vector")
