# Performance Testing - Quick Start Guide

## TL;DR

**Status**: ❌ Performance tests show 8x slower than target
**Bottleneck**: AI model processing time (not code)
**Quick fix**: Reduce transcript size → 70% improvement

---

## Running Performance Tests

### Prerequisites
```bash
# 1. Authenticate with Google Cloud
gcloud auth application-default login

# 2. Ensure you're in the project directory
cd /Users/young/project/career_ios_backend
```

### Run Tests
```bash
# Run all performance tests
poetry run pytest tests/performance/test_realtime_performance.py -v -s

# Run specific test
poetry run pytest tests/performance/test_realtime_performance.py::TestRealtimePerformance::test_realtime_analyze_10min_transcript_v1 -v -s
```

---

## Current Performance (2025-12-27)

### Test Results

| Test | Target | Actual | Status |
|------|--------|--------|--------|
| 10-min transcript (手足衝突) | < 2s | **18.8s** | ❌ |
| 10-min transcript (青少年网络成瘾) | < 2s | **13.8s** | ❌ |

### Performance Breakdown

```
┌───────────────────────────────────────────┐
│ Realtime Analysis (10-min transcript)    │
├───────────────────────────────────────────┤
│ 1. Request Processing      ~200 ms        │
│ 2. RAG Search              ~800 ms        │
│ 3. AI Analysis (Gemini)    ~15,000 ms ⚠️  │ ← BOTTLENECK
│ 4. Response Formatting     ~100 ms        │
├───────────────────────────────────────────┤
│ TOTAL:                     ~16,000 ms ❌  │
└───────────────────────────────────────────┘

Target: < 2,000 ms
Gap: ~14,000 ms (7x slower)
```

---

## Files in This Directory

### Performance Tests
- **`test_realtime_performance.py`** - Main performance test suite
  - Test 1: 10-min transcript analysis (手足衝突)
  - Test 2: 10-min transcript analysis v2 (青少年网络成瘾)
  - Test 3: iOS flow - Append recording
  - Test 4: Complete iOS flow (append + analyze)

### Documentation
- **`PERFORMANCE_REPORT.md`** - Detailed performance analysis and findings
- **`OPTIMIZATION_PLAN.md`** - Step-by-step optimization roadmap
- **`README.md`** (this file) - Quick reference guide

### Test Data
- Uses existing test data: `tests/data/long_transcripts.json`
- Uses existing test data: `tests/data/long_transcripts_v2.json`

---

## Quick Optimization Guide

### Priority 1: Immediate Wins (This Week)

#### 1. Reduce Transcript Size (70% improvement)
```python
# File: app/api/realtime.py

# Before: Analyze full 10 minutes (~3000 chars)
transcript = full_transcript

# After: Analyze only last 2-3 minutes (~600-900 chars)
MAX_CHARS = 1000
if len(transcript) > MAX_CHARS:
    transcript = transcript[-MAX_CHARS:]

# Expected: 18s → ~5s
```

#### 2. Enable Caching (30% improvement on cache hits)
```python
# File: app/services/gemini_service.py

from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def analyze_cached(transcript_hash: str, mode: str):
    return _analyze_impl(transcript_hash, mode)

# Expected: Cache hit → ~50ms, Cache miss → 5s
```

### Priority 2: Medium-term (Next Sprint)

#### 3. Streaming Response (Better UX)
```python
# New endpoint: /api/v1/realtime/analyze-stream
# Stream partial results as they arrive
# User sees first feedback in < 1s
```

#### 4. Client-side Pre-screening (70% reduction in backend calls)
```swift
// iOS App
// Check safety locally, only call backend if needed
```

---

## Expected Results After Optimizations

| Phase | Optimizations | Expected Time | Status |
|-------|--------------|---------------|--------|
| **Current** | None | 16s | ❌ Baseline |
| **Week 1** | Reduce transcript + Cache | **5s** | 🎯 Target |
| **Week 2** | + Streaming | **4s** + better UX | 🎯 Target |
| **Month 2** | + Faster AI model | **< 3s** | 🎯 Stretch |

---

## Test Data Details

### Transcript 1: 手足衝突 (Sibling Conflict)
```json
{
  "duration_minutes": 10,
  "topic": "手足衝突",
  "speakers": 28,
  "content": "Parent discussing children fighting over TV, toys, etc."
}
```

### Transcript 2: 青少年网络成瘾 (Teen Internet Addiction)
```json
{
  "duration_minutes": 10,
  "topic": "青少年网络成瘾",
  "speakers": 28,
  "content": "Parent discussing high school son gaming until 2-3 AM"
}
```

---

## Monitoring Recommendations

### Add to All Analyze Endpoints
```python
import time
from app.services.monitoring import track_performance

@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    start = time.time()

    # ... analysis logic ...

    duration_ms = (time.time() - start) * 1000
    track_performance({
        "endpoint": "/analyze",
        "duration_ms": duration_ms,
        "transcript_length": len(request.transcript),
    })
```

### Metrics to Track
1. P50 latency (median)
2. P95 latency (95th percentile)
3. Cache hit rate
4. Average transcript length
5. Model API errors

---

## Known Issues

### 1. GBQ Logging Errors (Non-blocking)
```
ERROR: BigQuery insert failed: no such field: result_data
```
- Impact: Logs not saved to BigQuery (analysis still works)
- Fix: Update GBQ table schema
- Priority: Low (doesn't affect performance)

### 2. iOS Flow Tests Require Auth Setup
```
ERROR at setup of TestiOSFlowPerformance.test_append_recording_1min
```
- Impact: Can't test append/analyze-partial flow
- Fix: Set up test user authentication
- Priority: Medium (nice to have)

---

## Next Steps

1. **Immediate**: Implement transcript size reduction (2 hours)
2. **This week**: Add caching (4 hours)
3. **Next week**: Implement streaming response (2 days)
4. **Ongoing**: Monitor performance metrics

---

## Questions?

- See **PERFORMANCE_REPORT.md** for detailed analysis
- See **OPTIMIZATION_PLAN.md** for implementation details
- See **test_realtime_performance.py** for test code

---

**Last Updated**: 2025-12-27
**Tested By**: Performance Test Suite v1.0
**Environment**: Local development (macOS, Python 3.12.8)
