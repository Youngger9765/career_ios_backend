# Incremental Billing System - Executive Summary

**Version:** 1.0
**Status:** Documentation Complete, Ready for Implementation
**Date:** 2025-12-28

---

## Quick Start

**What:** Incremental billing system with ceiling rounding for fair, accurate credit consumption tracking

**Why:** Prevent overcharging, enable real-time billing, maintain complete audit trail

**How:**
- Ceiling rounding: `ceil(duration_seconds / 60) * 1.0 credits`
- Incremental billing: Only charge NEW minutes since last billing
- Dual-write pattern: CreditLog (truth) + SessionUsage (cache)

---

## Documentation Structure

### Core Documents (3 files)

1. **INCREMENTAL_BILLING_PRD.md** (Technical Specification)
   - Executive summary and business goals
   - Database schema changes (3 models)
   - Billing logic design (incremental formula)
   - Feature metadata (polymorphic associations)
   - Migration plan (4 phases)
   - Risk mitigation and rollback plans
   - GBQ schema alignment details

2. **INCREMENTAL_BILLING_TEST_PLAN.md** (Testing Strategy)
   - Test strategy (57 tests total)
   - Existing tests to update (23 tests)
   - New tests to create (34 tests)
   - Performance benchmarks (< 3s target)
   - Data integrity validation
   - Implementation checklist with commands
   - Rollback procedures

3. **INCREMENTAL_BILLING_SUMMARY.md** (This Document)
   - Quick overview for stakeholders
   - Key decisions and rationale
   - Implementation timeline
   - Success criteria

### Migration SQL

**File:** `migrations/incremental_billing_migration.sql`
- Phase 1: Add new fields (backward compatible)
- Phase 2: Migrate data (idempotent)
- Phase 3: Create indexes (3 indexes)
- Phase 4: Drop old fields (optional, after verification)

---

## Key Design Decisions

### 1. Simplified Counselor Model

**BEFORE (Error-Prone):**
```python
total_credits: int      # Total purchased
credits_used: int       # Total consumed
available = total_credits - credits_used  # Calculated
```

**AFTER (Single Source of Truth):**
```python
available_credits: int  # Current balance (direct)
```

**Benefits:**
- Eliminates sync issues
- Simpler model (2 fields → 1 field)
- Better performance (no calculation)
- CreditLog provides full history

### 2. Dual-Write Pattern

**CreditLog (Truth):**
- Authoritative transaction history
- Complete audit trail
- Supports all resource types

**SessionUsage.credits_deducted (Cache):**
- Fast session totals
- No joins required
- Denormalized for performance

**Consistency:**
- Periodic verification job
- Auto-repair (trust CreditLog)
- Transaction-wrapped updates

### 3. Polymorphic Associations

**OLD (Rigid):**
```python
session_id: UUID  # Only sessions
```

**NEW (Flexible):**
```python
resource_type: str | null    # 'session', 'translation', 'ocr'
resource_id: str | null      # UUID as string (polymorphic)
```

**Benefits:**
- Future-proof (all features)
- Queryable (indexed)
- Flexible (null for purchases)

---

## Implementation Timeline

### Phase 1: Schema Migration (1 day, no downtime)
- Add new fields to 3 tables
- Migrate existing data
- Create 3 indexes
- Add 3 constraints
- Verify data integrity

**Success:** All counselors have valid `available_credits >= 0`

### Phase 2: Code Implementation (1 week)
- Update 23 existing tests
- Create 34+ new tests
- Implement dual-write logic
- Deploy with feature flag OFF
- Run full test suite (57 tests)

**Success:** All tests pass, no errors in staging

### Phase 3: Enable Dual-Write (1 week, gradual)
- Day 1: 10% traffic
- Day 3: 50% traffic
- Day 7: 100% traffic
- Monitor consistency and performance

**Success:**
- 0 inconsistencies
- P95 latency < 3s
- 0 billing errors

### Phase 4: Deprecate Old Fields (1 month later)
- Monitor production for 30 days
- Remove code references
- Drop old columns
- Final verification

**Success:** Stable for 30+ days, no errors

---

## Success Metrics

### Functional
- 100% billing accuracy (manual audit: 100 sessions)
- 0 negative balance errors
- 0 double-billing incidents
- 100% consistency (SessionUsage ↔ CreditLog)

### Performance
- P95 analyze-partial < 3s
- P99 analyze-partial < 5s
- Database operations < 50ms
- GBQ writes < 1s (background)

### Quality
- 57+ tests pass (100%)
- 95% overall coverage
- 100% critical path coverage
- 0 production errors

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Dual-write inconsistency | High | Low | Transaction wrapper, consistency checks |
| Performance degradation | Medium | Low | Indexes, background tasks, gradual rollout |
| Negative balance | High | Low | DB constraint, validation, rollback |
| GBQ write failure | Low | Medium | Retry logic, monitoring, non-blocking |
| Migration data loss | High | Low | Backup, dry-run, staged rollout |

---

## Quick Reference

### Run Tests
```bash
# All integration tests
poetry run pytest tests/integration/ -v

# Specific billing tests
poetry run pytest tests/integration/test_incremental_billing.py -v

# Full suite with coverage
poetry run pytest tests/ -v --cov=app --cov-report=html
```

### Verify Consistency
```sql
-- Check for inconsistencies
SELECT * FROM verify_credit_log_consistency();
```

### Rollback (if needed)
```bash
# Phase 3 rollback: disable feature flag
ENABLE_CREDIT_LOG_DUAL_WRITE=false

# Phase 1 rollback: run migration rollback SQL
psql -f migrations/incremental_billing_migration.sql --rollback
```

---

## Key Features

1. **Incremental Billing:** Only charge for NEW minutes (prevent double billing)
2. **Ceiling Rounding:** `ceil(30/60) = 1`, `ceil(61/60) = 2`
3. **Dual-Write:** CreditLog (truth) + SessionUsage (cache)
4. **Polymorphic:** Support session, translation, OCR, reports
5. **Consistency Checks:** Periodic verification + auto-repair
6. **Feature Flags:** Gradual rollout (10% → 50% → 100%)

---

## Billing Logic Example

```python
# Timeline
# 0s → 30s: Analysis 1 → ceil(30/60) = 1 minute → 1 credit
# 30s → 90s: Analysis 2 → ceil(90/60) = 2 minutes → 1 NEW credit (2 - 1)
# 90s → 185s: Analysis 3 → ceil(185/60) = 4 minutes → 2 NEW credits (4 - 2)

# Total credits deducted: 1 + 1 + 2 = 4 credits for 185 seconds
```

---

## GBQ Schema Alignment

**Status:** ✅ Complete (43/43 required fields aligned)

**Migration:** `314916418112_add_gbq_fields_to_session_analysis_log`

**Field Mappings:**
- `transcript_segment` → `transcript`
- `model_used` → `model_name`
- `result_data` → `analysis_result`

**Data Flow:**
1. Analysis service returns `_metadata`
2. PostgreSQL saves all fields (no transformation)
3. GBQ write maps 1:1 (direct mapping)

**Benefits:**
- No data transformation needed
- Complete observability
- Performance debugging
- Cost tracking

---

## Next Steps

### Immediate (Week 1)
1. Review PRD with team
2. Review Test Plan with QA
3. Approve design decisions
4. Backup production database
5. Execute Phase 1 migration

### Short-term (Week 2-4)
6. Execute Phase 2 (code implementation)
7. Update existing tests (23 tests)
8. Create new tests (34 tests)
9. Deploy to staging
10. Execute Phase 3 (gradual rollout)

### Long-term (Month 2+)
11. Monitor for 30 days
12. Execute Phase 4 (deprecate old fields)
13. Continuous optimization

---

## FAQ

**Q: Why not use total_credits and credits_used?**
A: Dual accounting is error-prone. Single `available_credits` is simpler, more reliable. CreditLog provides audit trail.

**Q: What if CreditLog and SessionUsage get out of sync?**
A: Periodic consistency check detects and auto-repairs (trusts CreditLog as authoritative).

**Q: Why polymorphic associations?**
A: More flexible (supports future features), queryable (indexed), follows best practices.

**Q: What if migration fails?**
A: Run rollback plan (included in migration SQL). All changes are transaction-wrapped.

**Q: What if performance degrades?**
A: Indexes optimize queries, background tasks handle GBQ, gradual rollout allows monitoring. Rollback available.

---

## Glossary

| Term | Definition |
|------|------------|
| **Incremental Billing** | Charge only for NEW minutes, not all minutes |
| **Ceiling Rounding** | Round up to nearest minute: `ceil(30/60) = 1` |
| **Dual-Write** | Update both SessionUsage (cache) and CreditLog (truth) |
| **Polymorphic Association** | Single resource_type/resource_id references multiple tables |
| **Single Source of Truth** | One authoritative data source (CreditLog) |
| **Denormalized Cache** | Redundant data for performance (SessionUsage) |
| **Feature Flag** | Toggle to enable/disable dual-write (gradual rollout) |
| **Consistency Check** | Verify SessionUsage matches CreditLog (auto-repair) |

---

**Document Status:** ✅ Complete and Ready for Implementation
**Next Step:** Team Review → Approve → Begin Phase 1 Migration

**For detailed information:**
- Technical design → See `INCREMENTAL_BILLING_PRD.md`
- Testing strategy → See `INCREMENTAL_BILLING_TEST_PLAN.md`
- Database migration → See `migrations/incremental_billing_migration.sql`
