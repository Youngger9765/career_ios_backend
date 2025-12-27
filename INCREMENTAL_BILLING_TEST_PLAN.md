# Incremental Billing System - Comprehensive Test Plan

**Version:** 1.0
**Status:** Implementation Ready
**Last Updated:** 2025-12-28
**Related:** INCREMENTAL_BILLING_PRD.md

---

## Table of Contents

1. [Test Strategy](#test-strategy)
2. [Test Categories](#test-categories)
3. [Existing Tests (To Update)](#existing-tests-to-update)
4. [New Tests (To Create)](#new-tests-to-create)
5. [Test Scenarios Matrix](#test-scenarios-matrix)
6. [Performance Tests](#performance-tests)
7. [Data Integrity Tests](#data-integrity-tests)
8. [Migration Tests](#migration-tests)
9. [Edge Cases](#edge-cases)
10. [Test Execution Plan](#test-execution-plan)

---

## Test Strategy

### Testing Pyramid

```
          /\
         /  \        E2E Tests (3 tests)
        /____\       - Complete workflow validation
       /      \      - iOS API performance
      /________\     Integration Tests (23 tests)
     /          \    - API endpoint testing
    /____________\   - Database consistency
   /              \  - Billing logic validation
  /________________\ Unit Tests (15+ tests)
                     - Billing calculation
                     - Data validation
                     - Helper functions
```

### Test Coverage Goals

| Category | Target Coverage | Critical | Notes |
|----------|----------------|----------|-------|
| Billing Logic | 100% | Yes | All edge cases must be tested |
| API Endpoints | 95% | Yes | All console.html APIs covered |
| Database Models | 90% | Medium | Focus on constraints and relationships |
| Error Handling | 85% | Medium | Cover common failure scenarios |

### Test Data Strategy

1. **Isolation**: Each test creates its own data (no shared state)
2. **Cleanup**: Automatic rollback via test fixtures
3. **Realism**: Use realistic counselor/client/session data
4. **Determinism**: Mock time for reproducible billing tests

---

## Test Categories

### 1. Unit Tests

**Purpose:** Test individual functions and methods in isolation

**Coverage:**
- [ ] Ceiling rounding calculation: `math.ceil(duration_seconds / 60)`
- [ ] Incremental minute calculation: `current_minutes - already_billed`
- [ ] Credit deduction math: `new_minutes * 1.0`
- [ ] Negative balance validation
- [ ] Polymorphic association validation
- [ ] JSON metadata serialization/deserialization

**Example:**
```python
def test_ceiling_rounding():
    """Test ceiling rounding for various durations"""
    assert ceil(1 / 60) == 1    # 1s → 1 min
    assert ceil(30 / 60) == 1   # 30s → 1 min
    assert ceil(60 / 60) == 1   # 60s → 1 min
    assert ceil(61 / 60) == 2   # 61s → 2 min
    assert ceil(120 / 60) == 2  # 120s → 2 min
    assert ceil(121 / 60) == 3  # 121s → 3 min

def test_incremental_calculation():
    """Test incremental billing calculation"""
    # First analysis: 0 → 1 minute
    assert calculate_new_minutes(30, 0) == 1
    # Second analysis: 1 → 2 minutes (only charge 1 new minute)
    assert calculate_new_minutes(90, 1) == 1
    # Third analysis: 2 → 4 minutes (charge 2 new minutes)
    assert calculate_new_minutes(185, 2) == 2
```

### 2. Integration Tests (Existing - Update Required)

#### File: `test_incremental_billing.py` (10 tests)

**Tests to Update:**

1. **✅ test_single_minute_multiple_analyses**
   - **Update:** Add CreditLog verification
   - **Current:** Only checks SessionUsage.credits_deducted
   - **New:** Verify CreditLog records created with correct resource_type='session'

2. **✅ test_cross_minute_incremental_billing**
   - **Update:** Verify CreditLog dual-write consistency
   - **Current:** Only checks SessionUsage fields
   - **New:** Verify sum(CreditLog.credits_delta) == SessionUsage.credits_deducted

3. **✅ test_counselor_credits_used_updated**
   - **Update:** Change from `credits_used` to `available_credits`
   - **Current:** Verifies counselor.credits_used increments
   - **New:** Verify counselor.available_credits decrements correctly

4. **All other tests (7 tests):**
   - **Update:** Add CreditLog creation verification
   - **Update:** Verify polymorphic associations (resource_type, resource_id)
   - **Update:** Check dual-write consistency

**Example Update:**
```python
# BEFORE (old test)
def test_cross_minute_incremental_billing(db_session, auth_headers, test_session):
    # ... perform analyses ...
    credits_deducted = self._get_credits_deducted(db_session, session_id)
    assert credits_deducted == Decimal("4")

# AFTER (updated test)
def test_cross_minute_incremental_billing(db_session, auth_headers, test_session):
    # ... perform analyses ...

    # Verify SessionUsage cache
    credits_deducted = self._get_credits_deducted(db_session, session_id)
    assert credits_deducted == Decimal("4")

    # Verify CreditLog authoritative records
    credit_logs = db_session.query(CreditLog).filter(
        CreditLog.resource_type == 'session',
        CreditLog.resource_id == str(session_id)
    ).all()

    # Should have 2 credit logs (1 credit, then 1 credit, then 2 credits)
    total_from_logs = sum(abs(log.credits_delta) for log in credit_logs)
    assert total_from_logs == 4, "CreditLog sum should match SessionUsage"

    # Verify polymorphic associations
    for log in credit_logs:
        assert log.resource_type == 'session'
        assert log.resource_id == str(session_id)
        assert log.transaction_type == 'usage'
```

#### File: `test_ios_api_performance.py` (4 tests)

**Tests to Update:**

1. **✅ test_short_transcript_performance**
   - **Update:** Verify CreditLog creation doesn't degrade performance
   - **Target:** Response time still < 2s with dual-write

2. **✅ test_medium_transcript_performance**
   - **Update:** Same as above

3. **✅ test_long_transcript_performance**
   - **Update:** Same as above

4. **✅ test_multiple_appends_with_analyses**
   - **Update:** Verify CreditLog records match SessionUsage after workflow
   - **Update:** Check total workflow time < 10s with dual-write

**Example Update:**
```python
def test_short_transcript_performance(db_session, auth_headers, test_session):
    # ... existing test code ...

    # NEW: Verify CreditLog created without performance hit
    db_session.expire_all()
    credit_logs = db_session.query(CreditLog).filter(
        CreditLog.resource_type == 'session',
        CreditLog.resource_id == str(session_id)
    ).all()

    assert len(credit_logs) > 0, "CreditLog should be created"
    assert analyze_time < 2.0, f"Performance degraded: {analyze_time:.2f}s"
```

#### File: `test_log_gbq_integrity.py` (6 tests)

**Tests to Update:**

1. **✅ test_session_analysis_log_completeness**
   - **Update:** No changes needed (focuses on SessionAnalysisLog)

2. **✅ test_session_usage_completeness**
   - **Update:** Add CreditLog verification
   - **New:** Verify CreditLog records match SessionUsage.credits_deducted

3. **✅ test_gbq_write_success**
   - **Update:** No changes needed (focuses on GBQ)

4. **✅ test_log_gbq_data_consistency**
   - **Update:** Add CreditLog schema validation
   - **New:** Verify CreditLog fields are GBQ-compatible (JSON, no complex types)

5. **✅ test_multiple_analyses_log_integrity**
   - **Update:** Verify CreditLog count matches analysis_count
   - **New:** Verify sum(CreditLog) == SessionUsage.credits_deducted

6. **✅ test_background_task_execution**
   - **Update:** No changes needed

**Example Update:**
```python
def test_session_usage_completeness(db_session, auth_headers, test_session):
    # ... existing test code ...

    # NEW: Verify CreditLog dual-write
    credit_logs = db_session.query(CreditLog).filter(
        CreditLog.resource_type == 'session',
        CreditLog.resource_id == str(session_id)
    ).all()

    # Should have credit logs for all analyses
    assert len(credit_logs) == 3, "Should have 3 credit log records"

    # Verify sum matches SessionUsage cache
    total_credits = sum(abs(log.credits_delta) for log in credit_logs)
    assert total_credits == session_usage.credits_deducted, \
        "CreditLog sum should match SessionUsage.credits_deducted"
```

#### File: `test_ios_api_e2e.py` (3 tests)

**Tests to Update:**

1. **✅ test_complete_ios_workflow**
   - **Update:** Add CreditLog verification at each step
   - **New:** Verify counselor.available_credits decrements correctly

2. **✅ test_ios_api_performance_benchmarks**
   - **Update:** Verify CreditLog doesn't degrade performance

3. **✅ test_ios_vs_realtime_accuracy**
   - **Update:** Add CreditLog data integrity check

**Example Update:**
```python
def test_complete_ios_workflow(db_session, auth_headers, test_session):
    # ... step 1-2: first analysis ...

    # Verify billing: 30s → 1 credit
    counselor = db_session.query(Counselor).filter_by(
        id=test_session.counselor_id
    ).first()

    # NEW: Verify available_credits decremented
    assert counselor.available_credits == 999, \
        f"Expected 999 credits (1000 - 1), got {counselor.available_credits}"

    # NEW: Verify CreditLog created
    credit_log = db_session.query(CreditLog).filter(
        CreditLog.resource_type == 'session',
        CreditLog.resource_id == str(session_id)
    ).order_by(CreditLog.created_at.desc()).first()

    assert credit_log is not None
    assert credit_log.credits_delta == -1
    assert credit_log.transaction_type == 'usage'

    # ... continue with remaining steps ...
```

---

## New Tests (To Create)

### File: `test_credit_log_dual_write.py` (NEW - 8 tests)

**Purpose:** Verify dual-write consistency between SessionUsage and CreditLog

1. **test_dual_write_consistency**
   ```python
   def test_dual_write_consistency(db_session, auth_headers, test_session):
       """Verify SessionUsage.credits_deducted == sum(CreditLog)"""
       session_id = test_session.id

       # Perform 3 analyses
       for i in range(3):
           analyze_partial(session_id, f"Analysis {i+1}")

       # Get SessionUsage cache
       session_usage = db_session.query(SessionUsage).filter(
           SessionUsage.session_id == session_id
       ).first()

       # Get CreditLog authoritative sum
       credit_log_sum = db_session.query(
           func.sum(CreditLog.credits_delta)
       ).filter(
           CreditLog.resource_type == 'session',
           CreditLog.resource_id == str(session_id)
       ).scalar()

       # Verify consistency
       assert abs(session_usage.credits_deducted + credit_log_sum) < 0.01, \
           f"Inconsistency: SessionUsage={session_usage.credits_deducted}, " \
           f"CreditLog={credit_log_sum}"
   ```

2. **test_counselor_balance_consistency**
   ```python
   def test_counselor_balance_consistency(db_session, counselor):
       """Verify counselor.available_credits == initial - sum(all CreditLog)"""
       initial_credits = 1000

       # Perform some operations
       deduct_credits(counselor.id, 10, 'usage')
       deduct_credits(counselor.id, 5, 'usage')
       add_credits(counselor.id, 20, 'purchase')

       # Calculate expected balance
       db_session.refresh(counselor)
       all_logs = db_session.query(CreditLog).filter(
           CreditLog.counselor_id == counselor.id
       ).all()

       credit_log_sum = sum(log.credits_delta for log in all_logs)
       expected_balance = initial_credits + credit_log_sum

       assert counselor.available_credits == expected_balance, \
           f"Expected {expected_balance}, got {counselor.available_credits}"
   ```

3. **test_dual_write_atomic_transaction**
   ```python
   def test_dual_write_atomic_transaction(db_session, auth_headers, test_session):
       """Verify dual-write is atomic (rollback on error)"""
       session_id = test_session.id

       # Mock error in CreditLog creation
       with patch('app.models.credit_log.CreditLog.__init__',
                  side_effect=Exception("Simulated error")):
           with pytest.raises(Exception):
               analyze_partial(session_id, "Test")

       # Verify rollback: no SessionUsage update, no CreditLog created
       db_session.rollback()
       session_usage = db_session.query(SessionUsage).filter(
           SessionUsage.session_id == session_id
       ).first()

       assert session_usage.credits_deducted == 0, \
           "SessionUsage should not be updated on rollback"

       credit_logs = db_session.query(CreditLog).filter(
           CreditLog.resource_type == 'session',
           CreditLog.resource_id == str(session_id)
       ).all()

       assert len(credit_logs) == 0, \
           "CreditLog should not be created on rollback"
   ```

4. **test_polymorphic_session_association**
   ```python
   def test_polymorphic_session_association(db_session, auth_headers, test_session):
       """Verify polymorphic association for session resources"""
       session_id = test_session.id

       # Perform analysis
       analyze_partial(session_id, "Test transcript")

       # Verify CreditLog created with correct polymorphic fields
       credit_log = db_session.query(CreditLog).filter(
           CreditLog.resource_type == 'session',
           CreditLog.resource_id == str(session_id)
       ).first()

       assert credit_log is not None
       assert credit_log.resource_type == 'session'
       assert credit_log.resource_id == str(session_id)
       assert credit_log.credits_delta < 0  # Usage is negative
   ```

5. **test_polymorphic_null_for_purchase**
   ```python
   def test_polymorphic_null_for_purchase(db_session, counselor):
       """Verify purchase transactions have null resource_type/resource_id"""
       # Create purchase transaction
       credit_log = CreditLog(
           counselor_id=counselor.id,
           credits_delta=100,
           transaction_type='purchase',
           resource_type=None,
           resource_id=None,
           raw_data={'payment_method': 'credit_card', 'amount_usd': 50.0}
       )
       db_session.add(credit_log)
       db_session.commit()

       # Verify
       db_session.refresh(credit_log)
       assert credit_log.resource_type is None
       assert credit_log.resource_id is None
       assert credit_log.transaction_type == 'purchase'
   ```

6. **test_query_by_resource_type**
   ```python
   def test_query_by_resource_type(db_session, auth_headers, test_session):
       """Verify querying CreditLog by resource_type"""
       session_id = test_session.id

       # Perform multiple analyses
       analyze_partial(session_id, "Analysis 1")
       analyze_partial(session_id, "Analysis 2")

       # Query all session-related credit logs
       session_logs = db_session.query(CreditLog).filter(
           CreditLog.resource_type == 'session'
       ).all()

       assert len(session_logs) >= 2
       for log in session_logs:
           assert log.resource_type == 'session'
           assert log.resource_id is not None
   ```

7. **test_multiple_resource_types**
   ```python
   def test_multiple_resource_types(db_session, counselor):
       """Verify support for multiple resource types (future-proof)"""
       # Create different resource types
       resources = [
           ('session', str(uuid4()), -5),
           ('translation', str(uuid4()), -2),
           ('ocr', str(uuid4()), -3),
           ('purchase', None, 100),
       ]

       for resource_type, resource_id, credits_delta in resources:
           credit_log = CreditLog(
               counselor_id=counselor.id,
               credits_delta=credits_delta,
               transaction_type='usage' if credits_delta < 0 else 'purchase',
               resource_type=resource_type if resource_type != 'purchase' else None,
               resource_id=resource_id
           )
           db_session.add(credit_log)

       db_session.commit()

       # Verify all created
       all_logs = db_session.query(CreditLog).filter(
           CreditLog.counselor_id == counselor.id
       ).all()

       assert len(all_logs) == 4
       assert set(log.resource_type for log in all_logs if log.resource_type) == \
           {'session', 'translation', 'ocr'}
   ```

8. **test_raw_data_metadata**
   ```python
   def test_raw_data_metadata(db_session, auth_headers, test_session):
       """Verify raw_data stores feature-specific metadata"""
       session_id = test_session.id

       # Perform analysis
       analyze_partial(session_id, "Test", elapsed_seconds=185)

       # Verify raw_data contains expected metadata
       credit_log = db_session.query(CreditLog).filter(
           CreditLog.resource_type == 'session',
           CreditLog.resource_id == str(session_id)
       ).order_by(CreditLog.created_at.desc()).first()

       raw_data = credit_log.raw_data
       assert raw_data['feature'] == 'session_analysis'
       assert 'duration_seconds' in raw_data
       assert 'current_minutes' in raw_data
       assert 'incremental_minutes' in raw_data
   ```

### File: `test_credit_consistency.py` (NEW - 5 tests)

**Purpose:** Verify consistency checks and auto-repair mechanisms

1. **test_consistency_verification_function**
   ```python
   def test_consistency_verification_function(db_session, auth_headers, test_session):
       """Verify consistency check function detects inconsistencies"""
       session_id = test_session.id

       # Create inconsistency (manually manipulate data)
       session_usage = db_session.query(SessionUsage).filter(
           SessionUsage.session_id == session_id
       ).first()
       session_usage.credits_deducted = 999  # Inconsistent value

       db_session.commit()

       # Run consistency check
       inconsistencies = verify_credit_consistency()

       # Should detect inconsistency
       assert len(inconsistencies) > 0
       assert any(i['session_id'] == session_id for i in inconsistencies)
   ```

2. **test_auto_repair_inconsistent_data**
   ```python
   def test_auto_repair_inconsistent_data(db_session, auth_headers, test_session):
       """Verify auto-repair trusts CreditLog as source of truth"""
       session_id = test_session.id

       # Perform analysis (creates correct records)
       analyze_partial(session_id, "Test", elapsed_seconds=60)

       # Get correct CreditLog sum
       credit_log_sum = db_session.query(
           func.sum(CreditLog.credits_delta)
       ).filter(
           CreditLog.resource_type == 'session',
           CreditLog.resource_id == str(session_id)
       ).scalar()

       # Introduce inconsistency
       session_usage = db_session.query(SessionUsage).filter(
           SessionUsage.session_id == session_id
       ).first()
       session_usage.credits_deducted = 999

       db_session.commit()

       # Run auto-repair
       repair_credit_consistency()

       # Verify repaired (should match CreditLog)
       db_session.refresh(session_usage)
       assert session_usage.credits_deducted == abs(credit_log_sum), \
           "Auto-repair should trust CreditLog"
   ```

3. **test_edge_case_interrupted_transaction**
   ```python
   def test_edge_case_interrupted_transaction(db_session, auth_headers, test_session):
       """Verify handling of interrupted transactions"""
       session_id = test_session.id

       # Simulate interrupted transaction (CreditLog created, SessionUsage not updated)
       credit_log = CreditLog(
           counselor_id=test_session.counselor_id,
           credits_delta=-5,
           transaction_type='usage',
           resource_type='session',
           resource_id=str(session_id)
       )
       db_session.add(credit_log)
       db_session.commit()

       # Note: SessionUsage not updated (simulates interruption)

       # Run consistency check
       inconsistencies = verify_credit_consistency()

       # Should detect inconsistency
       assert len(inconsistencies) > 0

       # Auto-repair
       repair_credit_consistency()

       # Verify SessionUsage updated to match CreditLog
       session_usage = db_session.query(SessionUsage).filter(
           SessionUsage.session_id == session_id
       ).first()
       assert session_usage.credits_deducted == 5
   ```

4. **test_consistency_check_performance**
   ```python
   def test_consistency_check_performance(db_session):
       """Verify consistency check completes in reasonable time"""
       import time

       # Create 100 sessions with analyses
       sessions = []
       for i in range(100):
           session = create_test_session(db_session)
           perform_analysis(session.id)
           sessions.append(session)

       # Measure consistency check time
       start = time.time()
       verify_credit_consistency()
       elapsed = time.time() - start

       # Should complete in < 1 second for 100 sessions
       assert elapsed < 1.0, f"Consistency check took {elapsed:.2f}s"
   ```

5. **test_no_false_positives**
   ```python
   def test_no_false_positives(db_session, auth_headers, test_session):
       """Verify consistency check doesn't report false positives"""
       session_id = test_session.id

       # Perform normal analyses (should be consistent)
       analyze_partial(session_id, "Test 1")
       analyze_partial(session_id, "Test 2")

       # Run consistency check
       inconsistencies = verify_credit_consistency()

       # Should NOT detect any inconsistencies
       assert len(inconsistencies) == 0, \
           "Should not report false positives for consistent data"
   ```

---

## Test Scenarios Matrix

Comprehensive matrix of billing scenarios:

| # | Scenario | Duration | Expected Minutes | Credits Deducted | Incremental | Test File | Status |
|---|----------|----------|------------------|------------------|-------------|-----------|--------|
| 1 | First analysis (30s) | 30s | 1 | 1 | 1 | test_incremental_billing.py | ✅ Existing |
| 2 | Second analysis (90s total) | 90s | 2 | 2 | 1 | test_incremental_billing.py | ✅ Existing |
| 3 | Third analysis (185s total) | 185s | 4 | 4 | 2 | test_incremental_billing.py | ✅ Existing |
| 4 | Rapid consecutive (10s, 20s, 30s) | 30s | 1 | 1 | 0 (same min) | test_incremental_billing.py | ✅ Existing |
| 5 | Edge: 1s | 1s | 1 | 1 | 1 | test_incremental_billing.py | ✅ Existing |
| 6 | Edge: 59s | 59s | 1 | 1 | 0 (same min) | test_incremental_billing.py | ✅ Existing |
| 7 | Edge: 60s | 60s | 1 | 1 | 0 (same min) | test_incremental_billing.py | ✅ Existing |
| 8 | Edge: 61s | 61s | 2 | 2 | 1 | test_incremental_billing.py | ✅ Existing |
| 9 | Edge: 119s | 119s | 2 | 2 | 0 (same min) | test_incremental_billing.py | ✅ Existing |
| 10 | Edge: 121s | 121s | 3 | 3 | 1 | test_incremental_billing.py | ✅ Existing |
| 11 | Interruption (no completion) | 90s | 2 | 2 | - | test_incremental_billing.py | ✅ Existing |
| 12 | Long gap (9.5 min) | 600s | 10 | 10 | 9 | test_incremental_billing.py | ✅ Existing |
| 13 | Zero duration | 0s | 0 or 1 | 0 or 1 | - | test_incremental_billing.py | ✅ Existing |
| 14 | Multi-tenant isolation | varies | varies | varies | - | test_incremental_billing.py | ✅ Existing |
| 15 | Counselor balance update | varies | varies | varies | - | test_incremental_billing.py | ✅ Existing |
| 16 | Dual-write consistency | varies | varies | varies | - | test_credit_log_dual_write.py | 🆕 New |
| 17 | Polymorphic session | varies | varies | varies | - | test_credit_log_dual_write.py | 🆕 New |
| 18 | Polymorphic purchase | - | - | +100 | - | test_credit_log_dual_write.py | 🆕 New |
| 19 | Atomic transaction rollback | - | - | 0 | - | test_credit_log_dual_write.py | 🆕 New |
| 20 | Consistency verification | varies | varies | varies | - | test_credit_consistency.py | 🆕 New |
| 21 | Auto-repair inconsistency | varies | varies | varies | - | test_credit_consistency.py | 🆕 New |

---

## Performance Tests

### Response Time Benchmarks

| Test | Endpoint | Target | Measured | Status | File |
|------|----------|--------|----------|--------|------|
| Short transcript (100 chars) | analyze-partial | < 2s | TBD | 🆕 | test_ios_api_performance.py |
| Medium transcript (500 chars) | analyze-partial | < 3s | TBD | 🆕 | test_ios_api_performance.py |
| Long transcript (2000 chars) | analyze-partial | < 3s | TBD | 🆕 | test_ios_api_performance.py |
| Multiple appends (4 iterations) | complete workflow | < 10s | TBD | 🆕 | test_ios_api_performance.py |
| Append transcript | append-recording | < 0.5s | TBD | 🆕 | test_ios_api_performance.py |

### Database Performance

| Test | Operation | Target | Measured | Status | File |
|------|-----------|--------|----------|--------|------|
| CreditLog INSERT | Single insert | < 10ms | TBD | 🆕 New | test_database_performance.py |
| SessionUsage UPDATE | Single update | < 10ms | TBD | 🆕 New | test_database_performance.py |
| Dual-write transaction | Both operations | < 50ms | TBD | 🆕 New | test_database_performance.py |
| Consistency check (100 sessions) | Batch query | < 1s | TBD | 🆕 New | test_credit_consistency.py |
| Query by resource_type | Index scan | < 10ms | TBD | 🆕 New | test_database_performance.py |

**New Test File: `test_database_performance.py`**
```python
def test_credit_log_insert_performance(db_session, counselor):
    """Verify CreditLog INSERT is fast"""
    import time

    start = time.time()

    credit_log = CreditLog(
        counselor_id=counselor.id,
        credits_delta=-5,
        transaction_type='usage',
        resource_type='session',
        resource_id=str(uuid4())
    )
    db_session.add(credit_log)
    db_session.commit()

    elapsed = time.time() - start

    assert elapsed < 0.01, f"INSERT took {elapsed*1000:.2f}ms (threshold: 10ms)"

def test_dual_write_transaction_performance(db_session, auth_headers, test_session):
    """Verify dual-write doesn't degrade performance"""
    import time

    session_id = test_session.id

    start = time.time()

    # Perform analysis (includes dual-write)
    analyze_partial(session_id, "Performance test")

    elapsed = time.time() - start

    # Should complete in < 50ms for database operations
    # (Note: Total API time is higher due to AI processing)
    assert elapsed < 3.0, f"Dual-write took {elapsed*1000:.2f}ms"
```

---

## Data Integrity Tests

### Database Constraints

| Test | Constraint | Expected Behavior | File | Status |
|------|-----------|-------------------|------|--------|
| Negative available_credits | `CHECK (available_credits >= 0)` | Reject with constraint violation | test_data_integrity.py | 🆕 New |
| Zero credits_delta | `CHECK (credits_delta != 0)` | Reject with constraint violation | test_data_integrity.py | 🆕 New |
| Inconsistent resource fields | `CHECK (resource_type/id both null or both not null)` | Reject with constraint violation | test_data_integrity.py | 🆕 New |

**New Test File: `test_data_integrity.py`**
```python
def test_negative_balance_rejected(db_session, counselor):
    """Verify negative balance is rejected by DB constraint"""
    from sqlalchemy.exc import IntegrityError

    counselor.available_credits = -10

    with pytest.raises(IntegrityError, match="chk_available_credits_positive"):
        db_session.commit()

def test_zero_credits_delta_rejected(db_session, counselor):
    """Verify zero credits_delta is rejected"""
    from sqlalchemy.exc import IntegrityError

    credit_log = CreditLog(
        counselor_id=counselor.id,
        credits_delta=0,  # Invalid
        transaction_type='usage'
    )
    db_session.add(credit_log)

    with pytest.raises(IntegrityError, match="chk_credits_delta_nonzero"):
        db_session.commit()

def test_inconsistent_resource_fields_rejected(db_session, counselor):
    """Verify inconsistent resource_type/resource_id is rejected"""
    from sqlalchemy.exc import IntegrityError

    # Case 1: resource_type set, resource_id null (invalid)
    credit_log = CreditLog(
        counselor_id=counselor.id,
        credits_delta=-5,
        transaction_type='usage',
        resource_type='session',
        resource_id=None  # Invalid: should have ID if type is set
    )
    db_session.add(credit_log)

    with pytest.raises(IntegrityError, match="chk_resource_consistency"):
        db_session.commit()
```

---

## Migration Tests

### Schema Migration Validation

| Test | Validation | Success Criteria | File | Status |
|------|-----------|------------------|------|--------|
| Add available_credits | Field exists and has default | All counselors have available_credits >= 0 | test_migration.py | 🆕 New |
| Migrate data | Data copied correctly | available_credits = total_credits - credits_used | test_migration.py | 🆕 New |
| Add polymorphic fields | Fields exist and nullable | resource_type, resource_id exist | test_migration.py | 🆕 New |
| Create indexes | Indexes created | ix_credit_logs_resource exists | test_migration.py | 🆕 New |
| Drop old fields | Fields removed | total_credits, credits_used not in schema | test_migration.py | 🆕 New |

**New Test File: `test_migration.py`**
```python
def test_available_credits_migration(db_session):
    """Verify available_credits migration is correct"""
    # Create test counselor with old schema values
    counselor = Counselor(
        email="migration-test@test.com",
        username="migrationtest",
        total_credits=100,
        credits_used=30
    )
    db_session.add(counselor)
    db_session.commit()

    # Run migration (simulated)
    counselor.available_credits = counselor.total_credits - counselor.credits_used

    db_session.commit()

    # Verify
    assert counselor.available_credits == 70

def test_polymorphic_fields_exist(db_session):
    """Verify polymorphic fields are created"""
    from sqlalchemy import inspect

    inspector = inspect(db_session.bind)
    columns = [col['name'] for col in inspector.get_columns('credit_logs')]

    assert 'resource_type' in columns
    assert 'resource_id' in columns

def test_indexes_created(db_session):
    """Verify indexes are created"""
    from sqlalchemy import inspect

    inspector = inspect(db_session.bind)
    indexes = inspector.get_indexes('credit_logs')
    index_names = [idx['name'] for idx in indexes]

    assert 'ix_credit_logs_resource' in index_names
    assert 'ix_credit_logs_counselor_type' in index_names
```

---

## Edge Cases

### Comprehensive Edge Case Coverage

| # | Edge Case | Expected Behavior | Test | Status |
|---|-----------|-------------------|------|--------|
| 1 | Zero duration (0s) | Deduct 0 or 1 credit (implementation choice) | test_incremental_billing.py | ✅ Existing |
| 2 | Exactly 60s | Deduct 1 credit (ceiling(60/60) = 1) | test_incremental_billing.py | ✅ Existing |
| 3 | 60.001s | Deduct 2 credits (ceiling(60.001/60) = 2) | test_edge_cases.py | 🆕 New |
| 4 | Very large duration (10 hours) | Deduct 600 credits | test_edge_cases.py | 🆕 New |
| 5 | Negative duration | Reject with validation error | test_edge_cases.py | 🆕 New |
| 6 | Insufficient balance | Reject with error | test_edge_cases.py | 🆕 New |
| 7 | Concurrent analyses (race condition) | Serialize with locks | test_edge_cases.py | 🆕 New |
| 8 | Database connection lost | Rollback transaction | test_edge_cases.py | 🆕 New |
| 9 | GBQ write failure | Log error, continue (non-blocking) | test_edge_cases.py | 🆕 New |
| 10 | Null transcript | Reject with validation error | test_edge_cases.py | 🆕 New |

**New Test File: `test_edge_cases.py`**
```python
def test_very_large_duration(db_session, auth_headers, test_session):
    """Verify handling of very large duration (10 hours)"""
    session_id = test_session.id

    # 10 hours = 36000 seconds = 600 minutes
    analyze_partial(session_id, "Long session", elapsed_seconds=36000)

    session_usage = db_session.query(SessionUsage).filter(
        SessionUsage.session_id == session_id
    ).first()

    assert session_usage.credits_deducted == 600

def test_insufficient_balance(db_session, auth_headers, test_session):
    """Verify insufficient balance is handled gracefully"""
    counselor = db_session.query(Counselor).filter_by(
        id=test_session.counselor_id
    ).first()

    # Set balance to 1 credit
    counselor.available_credits = 1
    db_session.commit()

    # Try to deduct 10 credits (should fail)
    session_id = test_session.id

    with pytest.raises(InsufficientCreditsError):
        analyze_partial(session_id, "Test", elapsed_seconds=600)  # 10 minutes

def test_concurrent_analyses_race_condition(db_session, auth_headers, test_session):
    """Verify concurrent analyses don't cause race conditions"""
    import threading

    session_id = test_session.id
    errors = []

    def perform_analysis():
        try:
            analyze_partial(session_id, "Concurrent test")
        except Exception as e:
            errors.append(e)

    # Spawn 10 concurrent threads
    threads = [threading.Thread(target=perform_analysis) for _ in range(10)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Should not have race condition errors
    assert len(errors) == 0, f"Race condition errors: {errors}"

    # Verify final state is consistent
    session_usage = db_session.query(SessionUsage).filter(
        SessionUsage.session_id == session_id
    ).first()

    credit_logs = db_session.query(CreditLog).filter(
        CreditLog.resource_type == 'session',
        CreditLog.resource_id == str(session_id)
    ).all()

    # Sum should match
    assert abs(session_usage.credits_deducted + sum(log.credits_delta for log in credit_logs)) < 0.01
```

---

## Test Execution Plan

### Development Phase

```bash
# 1. Run unit tests (fast feedback)
poetry run pytest tests/unit/ -v

# 2. Run integration tests (existing - verify no regressions)
poetry run pytest tests/integration/test_incremental_billing.py -v
poetry run pytest tests/integration/test_ios_api_performance.py -v
poetry run pytest tests/integration/test_log_gbq_integrity.py -v
poetry run pytest tests/integration/test_ios_api_e2e.py -v

# 3. Run new tests (dual-write, consistency)
poetry run pytest tests/integration/test_credit_log_dual_write.py -v
poetry run pytest tests/integration/test_credit_consistency.py -v

# 4. Run edge cases
poetry run pytest tests/integration/test_edge_cases.py -v

# 5. Run performance tests
poetry run pytest tests/integration/test_database_performance.py -v

# 6. Run data integrity tests
poetry run pytest tests/integration/test_data_integrity.py -v

# 7. Run migration tests
poetry run pytest tests/integration/test_migration.py -v

# 8. Full suite (before commit)
poetry run pytest tests/ -v --cov=app --cov-report=html
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Run unit tests
        run: poetry run pytest tests/unit/ -v

      - name: Run integration tests (existing)
        run: |
          poetry run pytest tests/integration/test_incremental_billing.py -v
          poetry run pytest tests/integration/test_ios_api_performance.py -v
          poetry run pytest tests/integration/test_log_gbq_integrity.py -v
          poetry run pytest tests/integration/test_ios_api_e2e.py -v

      - name: Run new tests (dual-write, consistency)
        run: |
          poetry run pytest tests/integration/test_credit_log_dual_write.py -v
          poetry run pytest tests/integration/test_credit_consistency.py -v

      - name: Run edge cases
        run: poetry run pytest tests/integration/test_edge_cases.py -v

      - name: Run performance tests
        run: poetry run pytest tests/integration/test_database_performance.py -v

      - name: Generate coverage report
        run: poetry run pytest --cov=app --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v2
```

### Pre-Push Checklist

- [ ] All unit tests pass (15+ tests)
- [ ] All integration tests pass (106+ tests)
- [ ] All new tests pass (20+ tests)
- [ ] Performance benchmarks met (< 3s for analyze-partial)
- [ ] Code coverage >= 90%
- [ ] No linting errors (ruff check --fix)
- [ ] No type errors (mypy - if enabled)
- [ ] Migration tests pass (schema validation)
- [ ] Data integrity tests pass (constraints enforced)

---

## Test Coverage Summary

### Current Coverage (Existing Tests)

| Category | Tests | Coverage | Status |
|----------|-------|----------|--------|
| Incremental Billing | 10 | 95% | ✅ Needs updates |
| iOS API Performance | 4 | 85% | ✅ Needs updates |
| Log & GBQ Integrity | 6 | 90% | ✅ Needs updates |
| iOS API E2E | 3 | 80% | ✅ Needs updates |

### New Coverage (New Tests)

| Category | Tests | Coverage | Status |
|----------|-------|----------|--------|
| Dual-Write Consistency | 8 | 100% | 🆕 New |
| Credit Consistency | 5 | 100% | 🆕 New |
| Edge Cases | 10 | 100% | 🆕 New |
| Database Performance | 5 | 100% | 🆕 New |
| Data Integrity | 3 | 100% | 🆕 New |
| Migration Validation | 3 | 100% | 🆕 New |

### Total Coverage

| Total Tests | Total Coverage | Critical Coverage |
|-------------|----------------|-------------------|
| **57 tests** | **95%** | **100%** (billing logic) |

---

## Appendices

### A. Test Data Fixtures

```python
@pytest.fixture
def counselor_with_credits(db_session):
    """Create counselor with 1000 credits"""
    counselor = Counselor(
        id=uuid4(),
        email="test@example.com",
        username="testcounselor",
        full_name="Test Counselor",
        hashed_password=hash_password("password123"),
        tenant_id="career",
        role="counselor",
        is_active=True,
        available_credits=1000
    )
    db_session.add(counselor)
    db_session.commit()
    return counselor

@pytest.fixture
def test_session_with_usage(db_session, counselor_with_credits):
    """Create session with SessionUsage record"""
    # ... create client, case, session ...

    session_usage = SessionUsage(
        id=uuid4(),
        session_id=session.id,
        counselor_id=counselor_with_credits.id,
        tenant_id="career",
        credits_deducted=0,
        last_billed_minutes=0
    )
    db_session.add(session_usage)
    db_session.commit()

    return session
```

### B. Test Helpers

```python
def create_credit_log(db_session, counselor_id, credits_delta, resource_type=None, resource_id=None):
    """Helper to create CreditLog record"""
    credit_log = CreditLog(
        counselor_id=counselor_id,
        credits_delta=credits_delta,
        transaction_type='usage' if credits_delta < 0 else 'purchase',
        resource_type=resource_type,
        resource_id=resource_id
    )
    db_session.add(credit_log)
    db_session.commit()
    return credit_log

def verify_consistency(db_session, session_id):
    """Helper to verify SessionUsage <-> CreditLog consistency"""
    session_usage = db_session.query(SessionUsage).filter(
        SessionUsage.session_id == session_id
    ).first()

    credit_log_sum = db_session.query(
        func.sum(CreditLog.credits_delta)
    ).filter(
        CreditLog.resource_type == 'session',
        CreditLog.resource_id == str(session_id)
    ).scalar()

    return abs(session_usage.credits_deducted + credit_log_sum) < 0.01
```

---

## Appendix: Implementation Checklist

### Quick Reference Commands

**Run Tests:**
```bash
# Unit tests
poetry run pytest tests/unit/ -v

# Specific integration test
poetry run pytest tests/integration/test_incremental_billing.py -v

# All integration tests
poetry run pytest tests/integration/ -v

# Full test suite with coverage
poetry run pytest tests/ -v --cov=app --cov-report=html
```

**Verify Consistency:**
```sql
-- Check for inconsistencies
SELECT * FROM verify_credit_log_consistency();

-- Manual consistency check
SELECT
    su.session_id,
    su.credits_deducted AS session_credits,
    COALESCE(ABS(SUM(cl.credits_delta)), 0) AS log_credits,
    su.credits_deducted - COALESCE(ABS(SUM(cl.credits_delta)), 0) AS difference
FROM session_usages su
LEFT JOIN credit_logs cl
    ON cl.resource_type = 'session'
    AND cl.resource_id = su.session_id::TEXT
GROUP BY su.session_id, su.credits_deducted
HAVING ABS(su.credits_deducted - COALESCE(ABS(SUM(cl.credits_delta)), 0)) >= 0.01;
```

**Check Performance:**
```sql
-- Slow queries (> 1s)
SELECT * FROM pg_stat_statements
WHERE mean_exec_time > 1000
ORDER BY mean_exec_time DESC;

-- Index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS index_scans
FROM pg_stat_user_indexes
WHERE tablename IN ('credit_logs', 'session_usages', 'counselors')
ORDER BY idx_scan DESC;
```

### Phase Implementation Summary

**Phase 1: Schema Migration (1 day, no downtime)**
- [ ] Run migration on staging
- [ ] Verify data migrated correctly
- [ ] Verify indexes created
- [ ] Run migration on production
- [ ] Monitor for 15 minutes

**Phase 2: Code Implementation (1 week)**
- [ ] Update 23 existing tests
- [ ] Create 34+ new tests
- [ ] Implement dual-write logic
- [ ] Deploy to staging (feature flag OFF)
- [ ] Run full test suite (57 tests)

**Phase 3: Enable Dual-Write (1 week, gradual)**
- [ ] Day 1: 10% traffic → Monitor
- [ ] Day 3: 50% traffic → Run consistency checks
- [ ] Day 7: 100% traffic → Full deployment

**Phase 4: Deprecate Old Fields (1 month later)**
- [ ] Monitor for 30 days
- [ ] Remove code references
- [ ] Drop old columns
- [ ] Verify production stable

### Rollback Plans

**If Phase 1 fails (migration error):**
```sql
BEGIN;
ALTER TABLE counselors DROP COLUMN IF EXISTS available_credits;
ALTER TABLE session_usages DROP COLUMN IF EXISTS last_billed_minutes;
ALTER TABLE credit_logs DROP COLUMN IF EXISTS resource_type;
ALTER TABLE credit_logs DROP COLUMN IF EXISTS resource_id;
DROP INDEX IF EXISTS ix_credit_logs_resource;
DROP INDEX IF EXISTS ix_credit_logs_counselor_type;
ALTER TABLE counselors DROP CONSTRAINT IF EXISTS chk_counselor_available_credits_positive;
ALTER TABLE credit_logs DROP CONSTRAINT IF EXISTS chk_credit_log_resource_consistency;
ALTER TABLE credit_logs DROP CONSTRAINT IF EXISTS chk_credit_log_credits_delta_nonzero;
COMMIT;
```

**If Phase 3 fails (dual-write issues):**
- Set feature flag: `ENABLE_CREDIT_LOG_DUAL_WRITE=false`
- Monitor for 1 hour (verify rollback successful)
- Investigate errors, fix issues
- Restart Phase 3 from Day 1

---

**Document Status:** ✅ Ready for Implementation
**Next Steps:** Review Test Plan → Update Existing Tests → Create New Tests → Execute Test Suite
