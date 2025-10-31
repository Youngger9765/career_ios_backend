"""enable_rls_on_all_tables

Revision ID: 251eba23af25
Revises: 4f0f21a16be0
Create Date: 2025-10-29 09:53:28.556832

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '251eba23af25'
down_revision: Union[str, None] = '4f0f21a16be0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable Row Level Security on all tables and create service_role policies."""

    # Tables that need RLS enabled
    tables = [
        'counselors',
        'cases',
        'document_quality_metrics',
        'evaluation_experiments',
        'evaluation_results',
        'evaluation_testsets',
        'jobs',
        'refresh_tokens',
        'reminders',
        'reports',
        'sessions',
        'users',
        'visitors',
    ]

    # Enable RLS on all tables
    for table in tables:
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;')

    # Create service_role full access policies for all tables
    for table in tables:
        op.execute(f"""
            CREATE POLICY "Service role full access on {table}"
            ON {table} FOR ALL
            USING (auth.role() = 'service_role');
        """)

    # Add specific authenticated user policies for counseling system

    # Counselors: Can read their own profile
    op.execute("""
        CREATE POLICY "Counselors read own profile"
        ON counselors FOR SELECT
        USING (auth.role() = 'authenticated' AND id = auth.uid());
    """)

    # Clients: Counselor can access their own clients
    op.execute("""
        CREATE POLICY "Counselors access own clients"
        ON clients FOR ALL
        USING (auth.role() = 'authenticated' AND counselor_id = auth.uid());
    """)

    # Sessions: Counselor can access their own sessions (via case)
    op.execute("""
        CREATE POLICY "Counselors access own sessions"
        ON sessions FOR ALL
        USING (
            auth.role() = 'authenticated' AND
            EXISTS (
                SELECT 1 FROM cases
                WHERE cases.id = sessions.case_id
                AND cases.counselor_id = auth.uid()
            )
        );
    """)

    # Reports: Counselor can access reports for their clients
    op.execute("""
        CREATE POLICY "Counselors access own reports"
        ON reports FOR ALL
        USING (
            auth.role() = 'authenticated' AND
            EXISTS (
                SELECT 1 FROM clients
                WHERE clients.id = reports.client_id
                AND clients.counselor_id = auth.uid()
            )
        );
    """)

    # Cases: Counselor can access their own cases
    op.execute("""
        CREATE POLICY "Counselors access own cases"
        ON cases FOR ALL
        USING (auth.role() = 'authenticated' AND counselor_id = auth.uid());
    """)

    # Jobs: Counselor can access jobs for their sessions
    op.execute("""
        CREATE POLICY "Counselors access own jobs"
        ON jobs FOR ALL
        USING (
            auth.role() = 'authenticated' AND
            EXISTS (
                SELECT 1 FROM sessions
                JOIN cases ON cases.id = sessions.case_id
                WHERE sessions.id = jobs.session_id
                AND cases.counselor_id = auth.uid()
            )
        );
    """)

    # Reminders: Counselor can access reminders for their cases
    op.execute("""
        CREATE POLICY "Counselors access own reminders"
        ON reminders FOR ALL
        USING (
            auth.role() = 'authenticated' AND
            EXISTS (
                SELECT 1 FROM cases
                WHERE cases.id = reminders.case_id
                AND cases.counselor_id = auth.uid()
            )
        );
    """)

    # Refresh tokens: Counselors can access their own tokens
    op.execute("""
        CREATE POLICY "Counselors access own refresh tokens"
        ON refresh_tokens FOR ALL
        USING (auth.role() = 'authenticated' AND counselor_id = auth.uid());
    """)

    # Evaluation tables: Authenticated users can read published results
    op.execute("""
        CREATE POLICY "Authenticated read evaluation experiments"
        ON evaluation_experiments FOR SELECT
        USING (auth.role() = 'authenticated');
    """)

    op.execute("""
        CREATE POLICY "Authenticated read evaluation results"
        ON evaluation_results FOR SELECT
        USING (auth.role() = 'authenticated');
    """)

    op.execute("""
        CREATE POLICY "Authenticated read evaluation testsets"
        ON evaluation_testsets FOR SELECT
        USING (auth.role() = 'authenticated');
    """)

    op.execute("""
        CREATE POLICY "Authenticated read document quality metrics"
        ON document_quality_metrics FOR SELECT
        USING (auth.role() = 'authenticated');
    """)


def downgrade() -> None:
    """Disable Row Level Security on all tables."""

    tables = [
        'counselors',
        'cases',
        'document_quality_metrics',
        'evaluation_experiments',
        'evaluation_results',
        'evaluation_testsets',
        'jobs',
        'refresh_tokens',
        'reminders',
        'reports',
        'sessions',
        'users',
        'visitors',
    ]

    # Drop all policies first
    for table in tables:
        op.execute(f'DROP POLICY IF EXISTS "Service role full access on {table}" ON {table};')

    # Drop specific policies
    op.execute('DROP POLICY IF EXISTS "Counselors read own profile" ON counselors;')
    op.execute('DROP POLICY IF EXISTS "Counselors access own clients" ON clients;')
    op.execute('DROP POLICY IF EXISTS "Counselors access own sessions" ON sessions;')
    op.execute('DROP POLICY IF EXISTS "Counselors access own reports" ON reports;')
    op.execute('DROP POLICY IF EXISTS "Counselors access own cases" ON cases;')
    op.execute('DROP POLICY IF EXISTS "Counselors access own jobs" ON jobs;')
    op.execute('DROP POLICY IF EXISTS "Counselors access own reminders" ON reminders;')
    op.execute('DROP POLICY IF EXISTS "Counselors access own refresh tokens" ON refresh_tokens;')
    op.execute('DROP POLICY IF EXISTS "Authenticated read evaluation experiments" ON evaluation_experiments;')
    op.execute('DROP POLICY IF EXISTS "Authenticated read evaluation results" ON evaluation_results;')
    op.execute('DROP POLICY IF EXISTS "Authenticated read evaluation testsets" ON evaluation_testsets;')
    op.execute('DROP POLICY IF EXISTS "Authenticated read document quality metrics" ON document_quality_metrics;')

    # Disable RLS on all tables
    for table in tables:
        op.execute(f'ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;')
