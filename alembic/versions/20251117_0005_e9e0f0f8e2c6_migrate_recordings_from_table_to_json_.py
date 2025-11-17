"""migrate recordings from table to json field in sessions

This migration:
1. Adds 'recordings' JSON column to sessions table
2. Migrates existing data from recordings table to sessions.recordings JSON field
3. Drops the recordings table

Revision ID: e9e0f0f8e2c6
Revises: 20251116_2108
Create Date: 2025-11-17 00:05:32.981552

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e9e0f0f8e2c6'
down_revision: Union[str, None] = '20251116_2108'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migrate recordings from separate table to JSON field in sessions
    """
    # Step 1: Add recordings JSON column to sessions table
    op.add_column('sessions', sa.Column('recordings', postgresql.JSON(astext_type=sa.Text()), nullable=True))

    # Step 2: Migrate data from recordings table to sessions.recordings
    # Use raw SQL to aggregate recordings into JSON array per session
    connection = op.get_bind()

    # Check if recordings table exists
    inspector = sa.inspect(connection)
    if 'recordings' in inspector.get_table_names():
        # Aggregate recordings by session_id into JSON array (transcript only)
        migration_sql = """
        UPDATE sessions
        SET recordings = (
            SELECT COALESCE(json_agg(
                json_build_object(
                    'segment_number', r.segment_number,
                    'start_time', to_char(r.start_time AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                    'end_time', to_char(r.end_time AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                    'transcript_text', r.transcript_text,
                    'transcript_sanitized', r.transcript_sanitized
                )
                ORDER BY r.segment_number
            ), '[]'::json)
            FROM recordings r
            WHERE r.session_id = sessions.id
        )
        WHERE EXISTS (
            SELECT 1 FROM recordings r WHERE r.session_id = sessions.id
        )
        """
        connection.execute(sa.text(migration_sql))

        # Step 3: Set empty array for sessions without recordings
        connection.execute(
            sa.text("UPDATE sessions SET recordings = '[]'::json WHERE recordings IS NULL")
        )

        # Step 4: Drop recordings table
        op.drop_table('recordings')
    else:
        # If recordings table doesn't exist, just set default empty array
        connection.execute(
            sa.text("UPDATE sessions SET recordings = '[]'::json WHERE recordings IS NULL")
        )


def downgrade() -> None:
    """
    Restore recordings table from JSON field in sessions
    """
    # Step 1: Recreate recordings table
    op.create_table(
        'recordings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('segment_number', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('audio_path', sa.String(), nullable=True),
        sa.Column('audio_format', sa.String(length=10), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('transcript_text', sa.Text(), nullable=True),
        sa.Column('transcript_sanitized', sa.Text(), nullable=True),
        sa.Column('transcription_status', sa.String(length=20), server_default='pending', nullable=True),
        sa.Column('transcription_error', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
    )
    op.create_index(op.f('ix_recordings_session_id'), 'recordings', ['session_id'], unique=False)
    op.create_index(op.f('ix_recordings_tenant_id'), 'recordings', ['tenant_id'], unique=False)

    # Step 2: Migrate data back from sessions.recordings JSON to recordings table
    connection = op.get_bind()

    # Extract recordings from JSON and insert into recordings table (transcript only)
    migration_sql = """
    INSERT INTO recordings (
        id, session_id, tenant_id, segment_number, start_time, end_time,
        transcript_text, transcript_sanitized
    )
    SELECT
        gen_random_uuid(),
        s.id,
        s.tenant_id,
        (rec->>'segment_number')::integer,
        (rec->>'start_time')::timestamp with time zone,
        (rec->>'end_time')::timestamp with time zone,
        rec->>'transcript_text',
        rec->>'transcript_sanitized'
    FROM sessions s
    CROSS JOIN json_array_elements(s.recordings::json) AS rec
    WHERE s.recordings IS NOT NULL
      AND json_array_length(s.recordings::json) > 0
    """
    connection.execute(sa.text(migration_sql))

    # Step 3: Drop recordings column from sessions
    op.drop_column('sessions', 'recordings')
