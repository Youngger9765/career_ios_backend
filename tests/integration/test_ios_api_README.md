# iOS API Testing Suite

Comprehensive performance and data integrity tests for iOS API (append + analyze-partial) vs Realtime API.

## Test Files

### 1. `test_ios_api_performance.py` - Performance Tests (4 tests + 1 summary)

Compare performance between iOS API flow (append transcript → analyze-partial) and Realtime API.

**Test Scenarios:**
- `test_short_transcript_performance`: Short transcript (100 chars)
  - iOS API: append + analyze
  - Realtime API: direct analysis
  - Threshold: append < 0.5s, analyze < 2s

- `test_medium_transcript_performance`: Medium transcript (500 chars)
  - Threshold: analyze < 3s

- `test_long_transcript_performance`: Long transcript (2000 chars)
  - Threshold: analyze < 3s

- `test_multiple_appends_with_analyses`: Multiple appends + analyses (simulate real iOS usage)
  - 4 iterations of append + analyze
  - Threshold: total workflow < 10s

**Expected Benchmarks:**
- append transcript: < 0.5s
- analyze-partial (short): < 2s
- analyze-partial (medium): < 3s
- analyze-partial (long): < 3s
- realtime API: < 5s
- complete workflow (4 iterations): < 10s

**Run Performance Tests:**
```bash
poetry run pytest tests/integration/test_ios_api_performance.py -v -s
```

---

### 2. `test_log_gbq_integrity.py` - Data Integrity Tests (6 tests + 1 summary)

Verify complete data persistence for iOS API across PostgreSQL and BigQuery.

**Test Scenarios:**

1. **`test_session_analysis_log_completeness`**
   - Verify SessionAnalysisLog record has all required fields:
     - session_id, counselor_id, tenant_id
     - transcript, analysis_result
     - safety_level, risk_indicators
     - token_usage, prompt_tokens, completion_tokens, total_tokens
     - model_name, analyzed_at

2. **`test_session_usage_completeness`**
   - Verify SessionUsage cumulative updates:
     - analysis_count increments
     - total_tokens accumulates
     - credits_deducted accumulates
     - last_billed_minutes updates

3. **`test_gbq_write_success`**
   - Mock GBQService.write_analysis_log
   - Verify method is callable
   - Check data structure matches BigQuery schema

4. **`test_log_gbq_data_consistency`**
   - Compare PostgreSQL SessionAnalysisLog vs GBQ data
   - Verify field name alignment:
     - `transcript` (not `transcript_segment`)
     - `analysis_result` (not `result_data`)
     - `model_name` (not `model_used`)

5. **`test_multiple_analyses_log_integrity`**
   - Create 5 analyses on same session
   - Verify 5 SessionAnalysisLog records created
   - Verify 1 SessionUsage record (cumulative)
   - Check analysis_count = 5 in SessionUsage

6. **`test_background_task_execution`**
   - Verify background task for GBQ write executes
   - Check it doesn't block API response (< 5s)

**Run Data Integrity Tests:**
```bash
poetry run pytest tests/integration/test_log_gbq_integrity.py -v -s
```

---

### 3. `test_ios_api_e2e.py` - End-to-End Tests (3 tests + 1 summary)

Test complete iOS API workflow from session creation to completion.

**Test Scenarios:**

1. **`test_complete_ios_workflow`**
   - Complete workflow with incremental billing:
     1. Create session
     2. Append + Analyze chunk 1 (30s) → Verify 1 credit
     3. Append + Analyze chunk 2 (60s total) → Verify 1 credit (same minute)
     4. Append + Analyze chunk 3 (125s total) → Verify 3 credits
     5. Complete session → Verify final state

2. **`test_ios_api_performance_benchmarks`**
   - Measure each step's response time
   - 3 iterations of append + analyze
   - Assert total workflow < 10 seconds
   - Log performance breakdown

3. **`test_ios_vs_realtime_accuracy`**
   - Same transcript tested on both APIs
   - Compare analysis results
   - Verify both produce same safety_level
   - Check token usage similar
   - Verify data integrity in PostgreSQL

**Run End-to-End Tests:**
```bash
poetry run pytest tests/integration/test_ios_api_e2e.py -v -s
```

---

## Run All iOS API Tests

```bash
# Run all tests
poetry run pytest tests/integration/test_ios_api_performance.py tests/integration/test_log_gbq_integrity.py tests/integration/test_ios_api_e2e.py -v -s

# Run specific test category
poetry run pytest tests/integration/test_ios_api_performance.py -v -s
poetry run pytest tests/integration/test_log_gbq_integrity.py -v -s
poetry run pytest tests/integration/test_ios_api_e2e.py -v -s

# Run summary reports only
poetry run pytest -k "summary" tests/integration/test_ios_api_*.py -v -s
```

---

## Test Coverage Summary

| File | Test Count | Purpose |
|------|------------|---------|
| `test_ios_api_performance.py` | 4 + 1 | Performance benchmarks |
| `test_log_gbq_integrity.py` | 6 + 1 | Data persistence verification |
| `test_ios_api_e2e.py` | 3 + 1 | Complete workflow testing |
| **Total** | **13 + 3** | **16 tests** |

---

## Expected Test Assertions

### Performance Tests
- ✅ Response time within thresholds
- ✅ append < 0.5s
- ✅ analyze-partial < 2-3s
- ✅ realtime API < 5s
- ✅ complete workflow < 10s

### Data Integrity Tests
- ✅ SessionAnalysisLog: All required fields populated
- ✅ SessionUsage: Cumulative updates work
- ✅ GBQ write: Method exists and callable
- ✅ Data consistency: Field names align (transcript, analysis_result, model_name)
- ✅ Multiple analyses: Separate logs, cumulative usage
- ✅ Background tasks: Non-blocking execution

### End-to-End Tests
- ✅ Complete workflow: append → analyze → billing
- ✅ Incremental billing: ceiling rounding (30s→1 credit, 125s→3 credits)
- ✅ Performance benchmarks: < 10s total
- ✅ iOS vs Realtime accuracy: Similar results
- ✅ Data integrity: PostgreSQL records verified

---

## Known Issues / Limitations

1. **bcrypt version compatibility**: Some environments may experience bcrypt version issues. This is an environment/dependency issue, not a test code issue.

2. **Realtime API tests**: May be skipped if GCP credentials are not available in test environment. This is expected behavior for CI/CD environments without GCP secrets.

3. **Mock dependencies**: Tests use mocked GeminiService for consistent performance testing. Real API tests should be run separately in integration environment.

---

## Test Data Files Location

- Performance tests: `/Users/young/project/career_ios_backend/tests/integration/test_ios_api_performance.py`
- Integrity tests: `/Users/young/project/career_ios_backend/tests/integration/test_log_gbq_integrity.py`
- E2E tests: `/Users/young/project/career_ios_backend/tests/integration/test_ios_api_e2e.py`

---

## Integration with CI/CD

These tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run iOS API Tests
  run: |
    poetry run pytest tests/integration/test_ios_api_performance.py -v
    poetry run pytest tests/integration/test_log_gbq_integrity.py -v
    poetry run pytest tests/integration/test_ios_api_e2e.py -v
```

---

**Last Updated**: 2025-12-27
**Version**: 1.0.0
**Author**: iOS API Testing Team
