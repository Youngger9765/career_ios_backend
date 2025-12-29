# Incremental Billing System - Product Requirements Document

**Version**: 1.0
**Last Updated**: 2025-12-28
**Status**: Implementation Complete

---

## 1. Executive Summary

### Problem Statement

The iOS backend system requires a fair, accurate, and auditable credit billing mechanism for session analysis that:

- Prevents overcharging users during incomplete or interrupted sessions
- Accurately bills based on actual usage with minute-level granularity
- Maintains complete transaction history for compliance and debugging
- Supports real-time incremental billing during active sessions

### Solution: Incremental Billing with Ceiling Rounding

**Core Formula**: `credits_to_deduct = ceil(duration_seconds / 60) * 1.0`

- **Rate**: 1 credit = 1 minute
- **Rounding**: Ceiling rounding (`math.ceil`) - any partial minute counts as full minute
- **Billing Strategy**: Incremental - only charge for NEW minutes since last billing
- **Protection**: Session interruptions won't cause credit loss (already billed incrementally)

### Key Benefits

1. **Fair Pricing**: Users only pay for time used, rounded to nearest minute
2. **Interruption Protection**: Credits deducted incrementally, not all at session end
3. **Complete Audit Trail**: Every transaction logged with detailed metadata
4. **Real-time Tracking**: Credits deducted during session, not after completion
5. **Multi-resource Support**: Extensible to translation, OCR, report generation

### Feature Overview
Implement an incremental billing system with ceiling rounding for accurate, fair, and auditable credit consumption tracking across all services (sessions, translations, OCR, reports, etc.).

### Business Goals
- **Fair Billing**: Only charge for actual usage with transparent minute-based incremental billing
- **Accurate Tracking**: Ceiling rounding ensures users pay for the minute they're in (not fractions)
- **Auditability**: Complete transaction history via CreditLog for compliance and debugging
- **Scalability**: Polymorphic associations support multiple resource types beyond sessions

### Key Decisions

#### 1. Simplified Counselor Model (Single Source of Truth)
```python
# BEFORE (Dual accounting - error-prone)
total_credits: int      # Total purchased
credits_used: int       # Total consumed
available = total_credits - credits_used  # Calculated property

# AFTER (Single source of truth)
available_credits: int  # Current balance (direct, simple, reliable)
```

**Rationale:**
- Eliminates calculation inconsistencies
- Simpler data model (1 field vs 3 fields)
- Performance: No calculation overhead
- CreditLog provides full history for auditing

#### 2. CreditLog Dual-Write Pattern
```python
# SessionUsage: Fast query cache (session-specific)
credits_deducted: Decimal  # Cache for quick session totals

# CreditLog: Single Source of Truth (authoritative)
credits_delta: int  # ALL transactions logged here
resource_type: str  # Polymorphic: 'session', 'translation', 'ocr'
resource_id: str    # Polymorphic resource ID
```

**Rationale:**
- CreditLog: Authoritative transaction history (audit trail)
- SessionUsage.credits_deducted: Denormalized cache (performance)
- Periodic verification jobs ensure consistency
- Supports multiple resource types (not just sessions)

#### 3. Polymorphic Associations
```python
# Instead of session_id only (rigid)
resource_type: str | null    # 'session', 'translation', 'ocr', 'report'
resource_id: str | null      # UUID as string (polymorphic)

# Examples
CreditLog(resource_type='session', resource_id='uuid-123')
CreditLog(resource_type='translation', resource_id='uuid-456')
CreditLog(resource_type='purchase', resource_type=null, resource_id=null)
```

**Rationale:**
- Future-proof: Supports all billable features
- Flexible: Purchase transactions have no resource (null values)
- Queryable: Index on (resource_type, resource_id) for fast lookups

---

## Technical Design

### Database Schema Changes

#### 1. Counselor Model (Simplified)

**Migration Steps:**
```sql
-- Add new field
ALTER TABLE counselors
ADD COLUMN available_credits INTEGER NOT NULL DEFAULT 0
COMMENT 'Available credits (current balance)';

-- Migrate data (one-time)
UPDATE counselors
SET available_credits = COALESCE(total_credits, 0) - COALESCE(credits_used, 0);

-- Drop old fields (after migration verified)
ALTER TABLE counselors DROP COLUMN total_credits;
ALTER TABLE counselors DROP COLUMN credits_used;
```

**Before:**
| Field | Type | Nullable | Comment |
|-------|------|----------|---------|
| total_credits | INTEGER | No | Total credits purchased |
| credits_used | INTEGER | No | Credits consumed |

**After:**
| Field | Type | Nullable | Comment |
|-------|------|----------|---------|
| available_credits | INTEGER | No | Current balance (default 0) |

**Benefits:**
- Eliminates sync issues between total_credits and credits_used
- Reduces storage (2 fields → 1 field)
- Simpler business logic (no calculation)

#### 2. SessionUsage Model (Add Incremental Billing Tracking)

**New Field:**
```sql
ALTER TABLE session_usages
ADD COLUMN last_billed_minutes INTEGER NOT NULL DEFAULT 0
COMMENT 'Last billed minutes (for incremental billing with ceiling rounding)';
```

| Field | Type | Nullable | Default | Comment |
|-------|------|----------|---------|---------|
| last_billed_minutes | INTEGER | No | 0 | Track last billed minutes for incremental billing |

**Rationale:**
- Prevents duplicate billing in the same minute
- Enables incremental charging (only bill for NEW minutes)
- Essential for ceiling rounding (math.ceil(duration_seconds / 60))

#### 3. CreditLog Model (Add Polymorphic Fields)

**Schema Changes:**
```sql
-- Add polymorphic fields
ALTER TABLE credit_logs
ADD COLUMN resource_type VARCHAR(50) NULL
COMMENT 'Resource type: session, translation, ocr, report';

ALTER TABLE credit_logs
ADD COLUMN resource_id VARCHAR NULL
COMMENT 'Resource ID (UUID as string, polymorphic)';

-- Create indexes for performance
CREATE INDEX ix_credit_logs_resource ON credit_logs(resource_type, resource_id);
CREATE INDEX ix_credit_logs_counselor_type ON credit_logs(counselor_id, transaction_type);
CREATE INDEX ix_credit_logs_created_at ON credit_logs(created_at);

-- Drop old session_id (not yet in production, safe to drop)
ALTER TABLE credit_logs DROP COLUMN session_id;
```

**New Schema:**
| Field | Type | Nullable | Comment |
|-------|------|----------|---------|
| counselor_id | UUID | No | Owner of this transaction |
| credits_delta | INTEGER | No | Credit change (+ or -) |
| transaction_type | VARCHAR(20) | No | purchase, usage, admin_adjustment, refund |
| resource_type | VARCHAR(50) | Yes | session, translation, ocr, report (null for purchases) |
| resource_id | VARCHAR | Yes | UUID as string (polymorphic, null for purchases) |
| raw_data | JSON | Yes | Feature-specific metadata |
| rate_snapshot | JSON | Yes | Rate configuration used |
| calculation_details | JSON | Yes | Detailed calculation breakdown |

**Rationale:**
- `resource_type` + `resource_id`: Polymorphic associations (flexible)
- `nullable=True`: Purchase transactions have no resource
- Index on `(resource_type, resource_id)`: Fast resource-specific queries
- `session_id` removed: Use polymorphic pattern instead

---

### NULL Field Analysis

Complete analysis of nullable fields for data integrity:

| Model | Field | Nullable | Justification | Risk | Mitigation |
|-------|-------|----------|---------------|------|------------|
| **Counselor** |
| | available_credits | No | Always has a balance (default 0) | None | Default value enforced |
| **SessionUsage** |
| | start_time | Yes | In-progress sessions may not have started yet | Medium | Should set on first analysis |
| | end_time | Yes | In-progress sessions have no end | None | Valid use case |
| | last_billed_minutes | No | Default to 0 for new sessions | None | Default value enforced |
| | duration_seconds | Yes | Calculated field (may be null if no start/end) | Low | Calculated property |
| | analysis_count | Yes | Default to 0 | Low | Default value recommended |
| | total_tokens | Yes | Default to 0 | Low | Default value recommended |
| | credits_deducted | No | Always tracked (default 0) | None | Default value enforced |
| **CreditLog** |
| | resource_type | Yes | Purchase transactions have no resource | None | Valid for 'purchase' type |
| | resource_id | Yes | Purchase transactions have no resource | None | Valid for 'purchase' type |
| | raw_data | Yes | May not apply to all transaction types | None | Optional metadata |
| | rate_snapshot | Yes | May not apply to admin adjustments | None | Optional metadata |
| | calculation_details | Yes | May not apply to purchases | None | Optional metadata |

**Recommendations:**
1. ✅ **Required (NOT NULL)**: available_credits, last_billed_minutes, credits_deducted
2. ⚠️ **Review**: SessionUsage.start_time should be NOT NULL (always set on creation)
3. ✅ **Valid NULL**: end_time (in-progress), resource_type/resource_id (purchases)

---

### Index Strategy

Optimized indexes for common query patterns:

```sql
-- CreditLog indexes (NEW)
CREATE INDEX ix_credit_logs_resource
ON credit_logs(resource_type, resource_id);
-- Query: "Show all credit logs for session X"
-- Query: "Show all translation costs"

CREATE INDEX ix_credit_logs_counselor_type
ON credit_logs(counselor_id, transaction_type);
-- Query: "Show all purchases for counselor Y"
-- Query: "Show all usage transactions for counselor Z"

CREATE INDEX ix_credit_logs_created_at
ON credit_logs(created_at);
-- Query: "Show transactions in date range"
-- Query: "Show recent activity"

-- SessionUsage indexes (EXISTING - verify)
CREATE INDEX ix_session_usages_counselor_status
ON session_usages(counselor_id, status);
-- Query: "Show all in-progress sessions for counselor"
-- Query: "Show completed sessions for billing"
```

**Performance Impact:**
- Index size: ~10KB per 1000 records
- Query speedup: 100x+ for filtered queries
- Write overhead: <5% (acceptable for read-heavy workload)

---

## Billing Logic Design

### Incremental Billing Formula

```python
# Calculate current minutes (ceiling rounding)
current_minutes = math.ceil(duration_seconds / 60)

# Get already billed minutes
already_billed = session_usage.last_billed_minutes

# Calculate NEW minutes only
new_minutes = current_minutes - already_billed

if new_minutes > 0:
    # Deduct credits
    credits_to_deduct = new_minutes * 1.0  # 1 credit = 1 minute
    counselor.available_credits -= credits_to_deduct
    session_usage.last_billed_minutes = current_minutes
    session_usage.credits_deducted += Decimal(str(credits_to_deduct))

    # Dual-write to CreditLog (authoritative)
    CreditLog.create(
        counselor_id=counselor_id,
        credits_delta=-credits_to_deduct,
        transaction_type='usage',
        resource_type='session',
        resource_id=str(session_id),
        raw_data={
            'feature': 'session_analysis',
            'duration_seconds': duration_seconds,
            'current_minutes': current_minutes,
            'incremental_minutes': new_minutes
        }
    )
```

**Key Features:**
1. **Ceiling Rounding**: `math.ceil(30/60) = 1` (user pays for minute they're in)
2. **Incremental Billing**: Only charge for NEW minutes (prevent double billing)
3. **Dual-Write**: Update both SessionUsage (cache) and CreditLog (truth)
4. **Metadata**: Store feature-specific details in raw_data for debugging

### Dual-Write Pattern

**Why Dual-Write?**
- **CreditLog**: Authoritative source (Single Source of Truth)
- **SessionUsage.credits_deducted**: Denormalized cache (performance)
- **Consistency**: Periodic verification job ensures sync

**Implementation:**
```python
# Transaction wrapper (atomic)
with db.begin():
    # 1. Update counselor balance
    counselor.available_credits -= credits_to_deduct

    # 2. Update session usage (cache)
    session_usage.credits_deducted += Decimal(str(credits_to_deduct))
    session_usage.last_billed_minutes = current_minutes

    # 3. Create credit log (truth)
    credit_log = CreditLog(
        counselor_id=counselor_id,
        credits_delta=-credits_to_deduct,
        transaction_type='usage',
        resource_type='session',
        resource_id=str(session_id),
        raw_data={...}
    )
    db.add(credit_log)

    db.commit()  # All or nothing
```

**Consistency Verification:**
```python
# Periodic job (run daily)
def verify_credit_consistency():
    for session in SessionUsage.query.all():
        # Sum all credit logs for this session
        credit_log_sum = db.query(
            func.sum(CreditLog.credits_delta)
        ).filter(
            CreditLog.resource_type == 'session',
            CreditLog.resource_id == str(session.session_id)
        ).scalar()

        # Compare with cached value
        if abs(session.credits_deducted + credit_log_sum) > 0.01:
            # Inconsistency detected - log and repair
            logger.error(f"Inconsistency: session {session.id}")
            # Auto-repair: trust CreditLog
            session.credits_deducted = abs(credit_log_sum)
```

---

## Feature Metadata Design

Different features store different metadata in CreditLog.raw_data:

### Session Analysis
```json
{
  "feature": "session_analysis",
  "duration_seconds": 185,
  "current_minutes": 4,
  "incremental_minutes": 2,
  "analysis_count": 3,
  "model_name": "gemini-1.5-flash-002"
}
```

### Translation (Future)
```json
{
  "feature": "translation",
  "source_lang": "en",
  "target_lang": "zh-TW",
  "characters": 1000,
  "rate_per_100_chars": 0.5,
  "model_name": "google-translate"
}
```

### OCR (Future)
```json
{
  "feature": "ocr",
  "pages": 5,
  "resolution": 300,
  "rate_per_page": 1.0,
  "model_name": "google-vision"
}
```

### Report Generation (Future)
```json
{
  "feature": "report_generation",
  "report_type": "session_summary",
  "sections": 5,
  "rate_per_report": 10.0,
  "model_name": "gemini-1.5-flash-002"
}
```

**Queryable Patterns:**
```sql
-- All session analysis costs
SELECT * FROM credit_logs
WHERE raw_data->>'feature' = 'session_analysis';

-- All translation costs for Chinese
SELECT * FROM credit_logs
WHERE raw_data->>'feature' = 'translation'
AND raw_data->>'target_lang' = 'zh-TW';

-- High-resolution OCR usage
SELECT * FROM credit_logs
WHERE raw_data->>'feature' = 'ocr'
AND CAST(raw_data->>'resolution' AS INTEGER) >= 300;
```

---

## Data Integrity Rules

### Database Constraints

1. **Counselor Balance:**
   ```sql
   ALTER TABLE counselors
   ADD CONSTRAINT chk_available_credits_positive
   CHECK (available_credits >= 0);
   ```

2. **CreditLog Delta:**
   ```sql
   ALTER TABLE credit_logs
   ADD CONSTRAINT chk_credits_delta_nonzero
   CHECK (credits_delta != 0);
   ```

3. **Polymorphic Consistency:**
   ```sql
   ALTER TABLE credit_logs
   ADD CONSTRAINT chk_resource_consistency
   CHECK (
       (resource_type IS NULL AND resource_id IS NULL) OR
       (resource_type IS NOT NULL AND resource_id IS NOT NULL)
   );
   ```

### Validation Checklist

#### Database Validation
- [ ] All SessionUsage records have valid counselor_id
- [ ] All SessionUsage.credits_deducted >= 0
- [ ] All SessionUsage.last_billed_minutes >= 0
- [ ] All CreditLog records have valid counselor_id
- [ ] All CreditLog.credits_delta != 0
- [ ] All CreditLog with resource_type have resource_id (and vice versa)
- [ ] Counselor.available_credits >= 0 (no negative balance)

#### Consistency Checks
- [ ] sum(CreditLog) per session == SessionUsage.credits_deducted
- [ ] sum(all CreditLog) per counselor == (initial - Counselor.available_credits)
- [ ] SessionUsage.duration_seconds / 60 (ceiling) == last_billed_minutes

#### GBQ Validation
- [ ] All SessionAnalysisLog in DB also in GBQ
- [ ] Field names match (transcript, analysis_result, model_name)
- [ ] No NULL values for required fields in GBQ

---

## Performance Benchmarks

### Target Performance

| Operation | Target | Measurement |
|-----------|--------|-------------|
| analyze-partial (with dual-write) | < 3s | Response time |
| Database INSERT (SessionUsage + CreditLog) | < 50ms | Query time |
| GBQ background write | < 1s | Background task time |
| Consistency check (per session) | < 10ms | Query time |
| Consistency check (all sessions) | < 1s | Batch query time |

### Optimization Strategies

1. **Database:**
   - Indexes on (resource_type, resource_id), (counselor_id, transaction_type)
   - Connection pooling (max 20 connections)
   - Batch inserts for GBQ (chunk size: 1000 records)

2. **Application:**
   - Background tasks for GBQ writes (non-blocking)
   - Caching for counselor balance checks (Redis, TTL 60s)
   - Async consistency verification (scheduled job)

3. **Monitoring:**
   - Track P95/P99 latency for analyze-partial
   - Alert if response time > 5s
   - Alert on consistency check failures

---

## Migration Plan

### Phase 1: Schema Migration (No Code Changes)
**Duration:** 1 day
**Downtime:** None

```sql
-- Step 1: Add new fields (backward compatible)
ALTER TABLE counselors ADD COLUMN available_credits INTEGER NOT NULL DEFAULT 0;
ALTER TABLE credit_logs ADD COLUMN resource_type VARCHAR(50) NULL;
ALTER TABLE credit_logs ADD COLUMN resource_id VARCHAR NULL;

-- Step 2: Migrate data
UPDATE counselors
SET available_credits = COALESCE(total_credits, 0) - COALESCE(credits_used, 0);

-- Step 3: Create indexes
CREATE INDEX ix_credit_logs_resource ON credit_logs(resource_type, resource_id);
CREATE INDEX ix_credit_logs_counselor_type ON credit_logs(counselor_id, transaction_type);

-- Step 4: Verify data
SELECT COUNT(*) FROM counselors WHERE available_credits < 0; -- Should be 0
```

**Verification:**
- [ ] All counselors have valid available_credits
- [ ] Indexes created successfully
- [ ] No performance degradation

### Phase 2: Deploy Code (Feature Flag OFF)
**Duration:** 2 hours
**Downtime:** None

```python
# Feature flag (default OFF)
ENABLE_CREDIT_LOG_DUAL_WRITE = os.getenv('ENABLE_CREDIT_LOG_DUAL_WRITE', 'false') == 'true'

# Code with feature flag
if ENABLE_CREDIT_LOG_DUAL_WRITE:
    # New dual-write logic
    create_credit_log(...)
else:
    # Old logic (deprecated)
    update_counselor_credits(...)
```

**Verification:**
- [ ] Deploy to staging
- [ ] Run integration tests (106+ tests)
- [ ] No errors in logs
- [ ] Feature flag OFF in production

### Phase 3: Enable Dual-Write (Gradual Rollout)
**Duration:** 1 week
**Downtime:** None

```python
# Day 1: 10% traffic
ENABLE_CREDIT_LOG_DUAL_WRITE = random.random() < 0.10

# Day 3: 50% traffic (if no errors)
ENABLE_CREDIT_LOG_DUAL_WRITE = random.random() < 0.50

# Day 7: 100% traffic (if no errors)
ENABLE_CREDIT_LOG_DUAL_WRITE = True
```

**Verification at each step:**
- [ ] Run consistency check
- [ ] Verify CreditLog records created
- [ ] Check error rates
- [ ] Monitor response time (< 3s)

### Phase 4: Deprecate Old Fields
**Duration:** 1 month (waiting period)
**Downtime:** None

```sql
-- After 1 month of successful dual-write
-- Step 1: Remove code references
# Remove all usage of total_credits, credits_used

-- Step 2: Drop columns
ALTER TABLE counselors DROP COLUMN total_credits;
ALTER TABLE counselors DROP COLUMN credits_used;

-- Step 3: Drop old indexes (if any)
DROP INDEX IF EXISTS ix_counselors_credits_used;
```

**Verification:**
- [ ] No code references to old fields
- [ ] All tests pass
- [ ] Production stable for 1 month

---

## Risk Mitigation

### Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Dual-write inconsistency** | High | Low | Transaction wrapper, consistency checks, rollback on error |
| **Performance degradation** | Medium | Low | Indexes, background tasks, benchmarks, gradual rollout |
| **Negative balance** | High | Low | DB constraint, validation checks, transaction rollback |
| **GBQ write failure** | Low | Medium | Retry logic (3 attempts), monitoring alerts, fallback to logs |
| **Migration data loss** | High | Low | Backup before migration, dry-run test, staged rollout |
| **Inconsistent polymorphic data** | Medium | Low | DB constraint, validation on insert, periodic verification |

### Rollback Plan

**If Phase 3 fails (dual-write issues):**
```python
# Immediate rollback
ENABLE_CREDIT_LOG_DUAL_WRITE = False

# Cleanup bad data (if any)
DELETE FROM credit_logs WHERE created_at > '2025-12-28 00:00:00';

# Restore from backup (if needed)
pg_restore -d career_ios_db backup_20251228.dump
```

**If Phase 4 fails (dropped columns needed):**
```sql
-- Restore columns
ALTER TABLE counselors ADD COLUMN total_credits INTEGER;
ALTER TABLE counselors ADD COLUMN credits_used INTEGER;

-- Rebuild data from CreditLog
UPDATE counselors SET
  total_credits = (SELECT SUM(credits_delta) FROM credit_logs
                   WHERE counselor_id = counselors.id
                   AND credits_delta > 0),
  credits_used = (SELECT ABS(SUM(credits_delta)) FROM credit_logs
                  WHERE counselor_id = counselors.id
                  AND credits_delta < 0);
```

---

## Success Metrics

### Functional Metrics
- [ ] 100% of sessions billed correctly (manual audit sample: 100 sessions)
- [ ] 0 negative balance errors
- [ ] 0 double-billing incidents
- [ ] 100% consistency between SessionUsage and CreditLog

### Performance Metrics
- [ ] P95 analyze-partial latency < 3s
- [ ] P99 analyze-partial latency < 5s
- [ ] Database query time < 50ms
- [ ] GBQ write time < 1s (background)

### Quality Metrics
- [ ] 106+ integration tests pass
- [ ] 0 production errors related to billing
- [ ] 100% test coverage for billing logic
- [ ] 0 data inconsistency alerts

---

## Open Questions & Decisions Needed

1. **Q:** Should we support fractional credits (e.g., 0.5 credits)?
   **A:** No, current design uses integers for simplicity. Can add Decimal later if needed.

2. **Q:** How to handle refunds?
   **A:** Create CreditLog with positive credits_delta, transaction_type='refund', resource_type=null.

3. **Q:** Should we archive old CreditLog records?
   **A:** No immediate need. Monitor table size. Consider partitioning if > 10M records.

4. **Q:** What if GBQ write fails permanently?
   **A:** Log error, send alert, continue (GBQ is for analytics, not critical path).

---

## Appendices

### A. Database Schema Diagrams

```
Counselor
├── id (UUID, PK)
├── available_credits (INTEGER, NOT NULL, DEFAULT 0)
└── [other fields...]

SessionUsage
├── id (UUID, PK)
├── session_id (UUID, FK → sessions.id, UNIQUE)
├── counselor_id (UUID, FK → counselors.id)
├── credits_deducted (DECIMAL, NOT NULL, DEFAULT 0)
├── last_billed_minutes (INTEGER, NOT NULL, DEFAULT 0)
└── [other fields...]

CreditLog
├── id (UUID, PK)
├── counselor_id (UUID, FK → counselors.id, NOT NULL)
├── credits_delta (INTEGER, NOT NULL, != 0)
├── transaction_type (VARCHAR(20), NOT NULL)
├── resource_type (VARCHAR(50), NULL)  # Polymorphic
├── resource_id (VARCHAR, NULL)        # Polymorphic
├── raw_data (JSON, NULL)
├── rate_snapshot (JSON, NULL)
└── [other fields...]
```

### B. API Changes

**No breaking changes.** All changes are backward compatible:
- Existing `analyze-partial` API continues to work
- Internal billing logic updated (transparent to clients)
- Response format unchanged

### C. Testing Strategy

See: `INCREMENTAL_BILLING_TEST_PLAN.md` for comprehensive test plan.

### D. GBQ Schema Alignment

**SessionAnalysisLog ↔ GBQ Complete Field Mapping**

Migration: `314916418112_add_gbq_fields_to_session_analysis_log`
Status: ✅ Complete alignment with GBQ schema (43 required fields)

**Field Name Mappings:**
- `transcript_segment` (PostgreSQL) → `transcript` (GBQ)
- `model_used` (PostgreSQL) → `model_name` (GBQ)
- `result_data` (PostgreSQL) → `analysis_result` (GBQ)

**Data Flow:**
1. Analysis service returns complete `_metadata` in result
2. PostgreSQL saves all fields directly to SessionAnalysisLog
3. GBQ write maps fields 1:1 (no transformation needed)

**Benefits:**
- ✅ No data transformation required (direct mapping)
- ✅ Complete observability (all metadata tracked)
- ✅ Performance debugging (timing breakdown: RAG, LLM, API)
- ✅ Cost tracking (token usage + estimated cost)

---

**Document Status:** ✅ Ready for Implementation
**Next Steps:** Review PRD → Approve → Begin Phase 1 Migration
