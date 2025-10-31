#!/bin/bash
# Check Row Level Security (RLS) status for all tables in Supabase database
# Usage: ./scripts/check_rls.sh [DATABASE_URL]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Use provided DATABASE_URL or fall back to environment variable
DB_URL="${1:-${DATABASE_URL}}"

if [ -z "$DB_URL" ]; then
    echo -e "${RED}❌ ERROR: DATABASE_URL not provided${NC}"
    echo "Usage: $0 [DATABASE_URL]"
    echo "Or set DATABASE_URL environment variable"
    exit 1
fi

echo "🔍 Checking RLS status for all tables..."
echo "================================================"

# Check RLS status
RESULT=$(psql "$DB_URL" -t -c "
SELECT
    tablename,
    CASE WHEN rowsecurity THEN 'Enabled' ELSE 'Disabled' END as rls_status,
    (SELECT COUNT(*) FROM pg_policies WHERE pg_policies.tablename = pg_tables.tablename) as policy_count
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename <> 'alembic_version'
ORDER BY tablename;
")

# Find tables without RLS
TABLES_WITHOUT_RLS=$(psql "$DB_URL" -t -c "
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
    AND NOT rowsecurity
    AND tablename <> 'alembic_version'
ORDER BY tablename;
" | xargs)

# Find tables without policies
TABLES_WITHOUT_POLICIES=$(psql "$DB_URL" -t -c "
SELECT t.tablename
FROM pg_tables t
LEFT JOIN (
    SELECT tablename, COUNT(*) as policy_count
    FROM pg_policies
    GROUP BY tablename
) p ON t.tablename = p.tablename
WHERE t.schemaname = 'public'
    AND t.tablename <> 'alembic_version'
    AND (p.policy_count IS NULL OR p.policy_count = 0)
ORDER BY t.tablename;
" | xargs)

# Display results
echo "$RESULT" | while IFS='|' read -r table rls policies; do
    table=$(echo "$table" | xargs)
    rls=$(echo "$rls" | xargs)
    policies=$(echo "$policies" | xargs)

    if [ "$rls" = "Enabled" ] && [ "$policies" -gt 0 ]; then
        echo -e "${GREEN}✅${NC} $table: RLS=$rls, Policies=$policies"
    elif [ "$rls" = "Enabled" ]; then
        echo -e "${YELLOW}⚠️${NC}  $table: RLS=$rls, Policies=$policies (WARNING: No policies!)"
    else
        echo -e "${RED}❌${NC} $table: RLS=$rls, Policies=$policies"
    fi
done

echo "================================================"

# Summary
if [ -n "$TABLES_WITHOUT_RLS" ]; then
    echo -e "${RED}❌ CRITICAL: Tables without RLS enabled:${NC}"
    echo "$TABLES_WITHOUT_RLS"
    exit 1
fi

if [ -n "$TABLES_WITHOUT_POLICIES" ]; then
    echo -e "${YELLOW}⚠️  WARNING: Tables without policies:${NC}"
    echo "$TABLES_WITHOUT_POLICIES"
    echo -e "${YELLOW}These tables have RLS enabled but no policies, which means NO ONE can access them!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All tables have RLS enabled with policies!${NC}"
exit 0
