"""console_initial_schema

Revision ID: d7c037c2c1d9
Revises: 90d014280e06
Create Date: 2025-11-18 15:24:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd7c037c2c1d9'
down_revision: Union[str, None] = '90d014280e06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================================
    # CONSOLE MODELS - Counseling system tables
    # ============================================================================

    # counselors table
    op.create_table(
        'counselors',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('COUNSELOR', 'SUPERVISOR', 'ADMIN', name='counselorrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email', 'tenant_id', name='uq_counselor_email_tenant'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_counselors_email'), 'counselors', ['email'], unique=False)
    op.create_index(op.f('ix_counselors_tenant_id'), 'counselors', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_counselors_username'), 'counselors', ['username'], unique=True)

    # clients table
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('nickname', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('gender', sa.String(), nullable=False),
        sa.Column('birth_date', sa.Date(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('identity_option', sa.String(), nullable=False),
        sa.Column('current_status', sa.String(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('education', sa.String(), nullable=True),
        sa.Column('current_job', sa.String(), nullable=True),
        sa.Column('career_status', sa.String(), nullable=True),
        sa.Column('occupation', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('has_consultation_history', sa.String(), nullable=True),
        sa.Column('has_mental_health_history', sa.String(), nullable=True),
        sa.Column('economic_status', sa.String(), nullable=True),
        sa.Column('family_relations', sa.Text(), nullable=True),
        sa.Column('other_info', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('counselor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['counselor_id'], ['counselors.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'code', name='uix_tenant_client_code')
    )
    op.create_index(op.f('ix_clients_code'), 'clients', ['code'], unique=False)
    op.create_index(op.f('ix_clients_email'), 'clients', ['email'], unique=False)
    op.create_index(op.f('ix_clients_tenant_id'), 'clients', ['tenant_id'], unique=False)

    # cases table
    op.create_table(
        'cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('case_number', sa.String(), nullable=False),
        sa.Column('counselor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'SUSPENDED', 'REFERRED', name='casestatus'), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('goals', sa.Text(), nullable=True),
        sa.Column('problem_description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['counselor_id'], ['counselors.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'case_number', name='uix_tenant_case_number')
    )
    op.create_index(op.f('ix_cases_case_number'), 'cases', ['case_number'], unique=False)
    op.create_index(op.f('ix_cases_tenant_id'), 'cases', ['tenant_id'], unique=False)

    # sessions table
    op.create_table(
        'sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('session_number', sa.Integer(), nullable=False),
        sa.Column('session_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('room_number', sa.String(), nullable=True),
        sa.Column('audio_path', sa.String(), nullable=True),
        sa.Column('transcript_text', sa.Text(), nullable=True),
        sa.Column('transcript_sanitized', sa.Text(), nullable=True),
        sa.Column('source_type', sa.String(length=10), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('key_points', sa.Text(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('reflection', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('recordings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sessions_tenant_id'), 'sessions', ['tenant_id'], unique=False)

    # reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('PROCESSING', 'DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED', 'FAILED', 'ARCHIVED', name='reportstatus'), nullable=False),
        sa.Column('mode', sa.String(), nullable=True),
        sa.Column('content_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('content_markdown', sa.Text(), nullable=True),
        sa.Column('edited_content_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('edited_content_markdown', sa.Text(), nullable=True),
        sa.Column('edited_at', sa.String(), nullable=True),
        sa.Column('edit_count', sa.Integer(), nullable=True),
        sa.Column('citations_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('agent_id', sa.Integer(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('analysis', sa.Text(), nullable=True),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('action_items', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ai_model', sa.String(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('quality_grade', sa.String(), nullable=True),
        sa.Column('quality_strengths', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('quality_weaknesses', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('reviewed_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['counselors.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['counselors.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_tenant_id'), 'reports', ['tenant_id'], unique=False)

    # jobs table
    op.create_table(
        'jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_type', sa.Enum('AUDIO_UPLOAD', 'TRANSCRIPTION', 'ANONYMIZATION', 'REPORT_GENERATION', name='jobtype'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', name='jobstatus'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('input_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('job_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # reminders table
    op.create_table(
        'reminders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reminder_type', sa.Enum('FOLLOW_UP', 'APPOINTMENT', 'TASK', 'REVIEW', name='remindertype'), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'CANCELLED', 'SNOOZED', name='reminderstatus'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_sent', sa.Boolean(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('counselor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['counselor_id'], ['counselors.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    op.create_index(op.f('ix_refresh_tokens_tenant_id'), 'refresh_tokens', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_token'), 'refresh_tokens', ['token'], unique=True)

    # ============================================================================
    # Enable Row Level Security (RLS) on all Console tables
    # ============================================================================

    # Tables with tenant_id - strict tenant isolation
    tenant_tables = [
        'counselors',
        'clients',
        'cases',
        'sessions',
        'reports',
        'refresh_tokens',
    ]

    for table in tenant_tables:
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # Create tenant isolation policy
        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {table}
            FOR ALL
            USING (tenant_id = current_setting('app.current_tenant_id', true)::text)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::text)
        """)

    # Tables without tenant_id - inherit access via FK relationships
    non_tenant_tables = [
        'jobs',
        'reminders',
    ]

    for table in non_tenant_tables:
        # Enable RLS
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        # Create permissive policy (access controlled via parent FK)
        op.execute(f"""
            CREATE POLICY allow_authenticated_access ON {table}
            FOR ALL
            USING (true)
            WITH CHECK (true)
        """)


def downgrade() -> None:
    # Drop all Console tables in reverse order
    op.drop_index(op.f('ix_refresh_tokens_token'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_tenant_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')

    op.drop_table('reminders')
    op.drop_table('jobs')

    op.drop_index(op.f('ix_reports_tenant_id'), table_name='reports')
    op.drop_table('reports')

    op.drop_index(op.f('ix_sessions_tenant_id'), table_name='sessions')
    op.drop_table('sessions')

    op.drop_index(op.f('ix_cases_tenant_id'), table_name='cases')
    op.drop_index(op.f('ix_cases_case_number'), table_name='cases')
    op.drop_table('cases')

    op.drop_index(op.f('ix_clients_tenant_id'), table_name='clients')
    op.drop_index(op.f('ix_clients_email'), table_name='clients')
    op.drop_index(op.f('ix_clients_code'), table_name='clients')
    op.drop_table('clients')

    op.drop_index(op.f('ix_counselors_username'), table_name='counselors')
    op.drop_index(op.f('ix_counselors_tenant_id'), table_name='counselors')
    op.drop_index(op.f('ix_counselors_email'), table_name='counselors')
    op.drop_table('counselors')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS reminderstatus')
    op.execute('DROP TYPE IF EXISTS remindertype')
    op.execute('DROP TYPE IF EXISTS jobstatus')
    op.execute('DROP TYPE IF EXISTS jobtype')
    op.execute('DROP TYPE IF EXISTS reportstatus')
    op.execute('DROP TYPE IF EXISTS casestatus')
    op.execute('DROP TYPE IF EXISTS counselorrole')
