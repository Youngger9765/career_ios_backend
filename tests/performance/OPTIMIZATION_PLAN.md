# Performance Optimization Plan
**Project**: Career iOS Backend - Realtime Analysis
**Date**: 2025-12-27
**Current Status**: Performance tests reveal 8-9x slower than target

---

## Quick Reference

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| **10-min Analysis** | < 2s | ~16s | ❌ 8x slower |
| **Bottleneck** | - | AI Model | Identified |
| **Quick Win** | - | Reduce transcript size | Ready |

---

## Priority 1: Immediate Fixes (This Week)

### 1.1 Reduce Transcript Size Sent to AI

**Problem**: Sending full 10-minute transcript (~3000 chars) to AI model
**Solution**: Only analyze recent 2-3 minutes (~600-900 chars)

**Implementation**:
```python
# app/api/realtime.py - Line ~900

def analyze_transcript(transcript: str, mode: str):
    # Current: Uses full transcript
    full_text = transcript

    # NEW: Only analyze last N minutes
    MAX_CHARS = 1000  # ~2-3 minutes of conversation
    if len(transcript) > MAX_CHARS:
        # Take last N characters (most recent conversation)
        recent_text = transcript[-MAX_CHARS:]
        # Or split by speaker turns and take last 10 turns
        turns = transcript.split('\n')
        recent_text = '\n'.join(turns[-10:])
    else:
        recent_text = transcript

    # Use recent_text for analysis
    result = ai_model.analyze(recent_text)
```

**Expected Impact**:
- Current: 16 seconds
- After: **~5 seconds** (70% improvement)
- User Experience: **Acceptable** for practice mode

**Effort**: 2 hours
**Risk**: Low (can easily revert)

---

### 1.2 Enable Gemini Response Caching

**Problem**: Every request makes fresh AI call
**Solution**: Cache common patterns and repeated analyses

**Implementation**:
```python
# app/services/gemini_service.py

from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def analyze_transcript_cached(transcript_hash: str, mode: str):
    # Use hash to cache results
    return _analyze_transcript_impl(transcript_hash, mode)

def analyze_transcript(transcript: str, mode: str):
    # Create hash of transcript (for cache key)
    transcript_hash = hashlib.md5(transcript.encode()).hexdigest()
    return analyze_transcript_cached(transcript_hash, mode)
```

**Expected Impact**:
- Cache hit rate: ~30-40% (repeated scenarios)
- Cache hit response time: **~50ms** (vs 16s)
- Average improvement: **~30%** faster

**Effort**: 4 hours
**Risk**: Low

---

### 1.3 Parallel RAG + AI Processing

**Problem**: RAG search → then AI analysis (sequential)
**Solution**: Run RAG and AI in parallel

**Implementation**:
```python
# app/api/realtime.py

import asyncio

async def analyze_with_rag_parallel(transcript: str):
    # Run RAG search and basic AI analysis in parallel
    rag_task = asyncio.create_task(rag_service.search(transcript))
    ai_task = asyncio.create_task(ai_service.basic_analysis(transcript))

    # Wait for both
    rag_results, basic_analysis = await asyncio.gather(rag_task, ai_task)

    # Then do final analysis with RAG context
    final = await ai_service.final_analysis(basic_analysis, rag_results)
    return final
```

**Expected Impact**:
- Save RAG search time: **~500-1000ms**
- Total time: **~15 seconds** (vs 16s)

**Effort**: 6 hours
**Risk**: Medium (async complexity)

---

## Priority 2: Medium-term Optimizations (Next Sprint)

### 2.1 Implement Streaming Response

**Problem**: User waits 16 seconds for any feedback
**Solution**: Stream partial results as they arrive

**Implementation**:
```python
# app/api/realtime.py

from fastapi.responses import StreamingResponse

@router.post("/analyze-stream")
async def analyze_streaming(request: AnalyzeRequest):
    async def generate():
        # Send quick safety assessment first (500ms)
        yield json.dumps({"type": "safety", "level": "green"})

        # Then send issues as detected (2-3s)
        for issue in detect_issues(transcript):
            yield json.dumps({"type": "issue", "data": issue})

        # Finally send full analysis (16s)
        yield json.dumps({"type": "complete", "data": full_analysis})

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Expected Impact**:
- **Perceived latency**: < 1 second (user sees first feedback)
- Total time: Still ~16s, but feels faster

**Effort**: 2 days
**Risk**: Medium (iOS app needs update)

---

### 2.2 Client-side Pre-screening

**Problem**: Backend analyzes every 1-minute segment
**Solution**: iOS app does basic safety check, only calls backend if needed

**iOS Implementation**:
```swift
// iOS App

func analyzeSegment(_ transcript: String) {
    // Quick local check (100ms)
    let localSafety = SimpleSafetyChecker.check(transcript)

    if localSafety.isGreen {
        // Don't call backend, show green immediately
        showSafetyLevel(.green)
    } else {
        // Call backend for detailed analysis
        callBackendAnalysis(transcript)
    }
}
```

**Expected Impact**:
- **70% of segments**: No backend call needed (instant feedback)
- **30% of segments**: Backend call (16s)
- **Average**: ~5 seconds per segment

**Effort**: 3 days (iOS + Backend)
**Risk**: Medium (requires iOS app update)

---

### 2.3 Background Analysis with Push Notifications

**Problem**: User must wait for analysis
**Solution**: Return immediately, notify when ready

**Implementation**:
```python
# app/api/realtime.py

@router.post("/analyze-async")
async def analyze_async(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    # Generate job ID
    job_id = str(uuid.uuid4())

    # Start analysis in background
    background_tasks.add_task(analyze_and_notify, job_id, request)

    # Return immediately
    return {"job_id": job_id, "status": "processing"}

async def analyze_and_notify(job_id: str, request: AnalyzeRequest):
    # Do analysis (16s)
    result = await analyze(request)

    # Send push notification to iOS
    await push_service.notify(job_id, result)
```

**Expected Impact**:
- **Frontend blocking time**: 0ms (immediate return)
- User gets notification when ready (~16s later)

**Effort**: 4 days (Backend + iOS + Push service)
**Risk**: High (complex architecture change)

---

## Priority 3: Long-term Strategies (Future Sprints)

### 3.1 Switch to Faster AI Model

**Options**:
1. **Gemini 2.0 Flash** (if faster than 1.5)
2. **Claude 3.5 Haiku** (known for speed)
3. **GPT-4o mini** (fast and cheap)

**Research Needed**:
- Benchmark each model with 10-min transcripts
- Compare quality vs speed trade-off

**Expected Impact**:
- Potential **50-70% speed improvement**
- Cost reduction possible

**Effort**: 1 week (research + implementation)
**Risk**: Medium (quality may vary)

---

### 3.2 Hybrid On-device + Cloud AI

**Concept**:
- iOS app runs lightweight AI model (Core ML)
- Cloud handles complex cases only

**Expected Impact**:
- **90% of analyses**: On-device (< 500ms)
- **10% of analyses**: Cloud (16s)
- **Average**: < 2 seconds

**Effort**: 4 weeks (major architecture change)
**Risk**: High (requires ML model training)

---

## Implementation Timeline

### Week 1 (Current Week)
- ✅ Day 1: Performance testing (DONE)
- [ ] Day 2-3: Implement Priority 1.1 (Reduce transcript size)
- [ ] Day 4: Implement Priority 1.2 (Caching)
- [ ] Day 5: Test and measure improvements

**Expected Result**: **~5 seconds** for 10-min analysis

---

### Week 2
- [ ] Day 1-2: Implement Priority 1.3 (Parallel processing)
- [ ] Day 3-5: Implement Priority 2.1 (Streaming response)

**Expected Result**: **~4 seconds** + streaming feedback

---

### Week 3-4
- [ ] Research faster AI models
- [ ] Implement Priority 2.2 (Client-side pre-screening)
- [ ] Prototype Priority 2.3 (Background analysis)

**Expected Result**: **< 3 seconds** average

---

## Success Metrics

| Timeline | Target | Optimizations Applied |
|----------|--------|----------------------|
| **Week 1** | < 5s | Reduce transcript + Caching |
| **Week 2** | < 4s | + Parallel + Streaming |
| **Week 3** | < 3s | + Client-side pre-screening |
| **Month 2** | < 2s | + Faster AI model |

---

## Risk Mitigation

### Technical Risks

1. **Cache invalidation complexity**
   - Mitigation: Use simple TTL-based cache (5 minutes)

2. **Streaming breaks existing iOS app**
   - Mitigation: Keep both endpoints (`/analyze` and `/analyze-stream`)

3. **Transcript truncation loses context**
   - Mitigation: Allow counselor to request full analysis manually

### Business Risks

1. **Faster model = lower quality**
   - Mitigation: A/B test with users before switching

2. **Complexity increases maintenance burden**
   - Mitigation: Document thoroughly, add monitoring

---

## Monitoring & Validation

### Metrics to Track

```python
# Add to all analyze endpoints

import time
from app.services.monitoring import track_performance

@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    start_time = time.time()

    # ... analysis logic ...

    duration_ms = (time.time() - start_time) * 1000

    # Log performance
    track_performance({
        "endpoint": "/analyze",
        "duration_ms": duration_ms,
        "transcript_length": len(request.transcript),
        "model": "gemini-1.5-flash",
        "cache_hit": cache_hit,
    })
```

### Dashboard Metrics

1. **P50 latency** (median response time)
2. **P95 latency** (95th percentile)
3. **Cache hit rate**
4. **Average transcript length analyzed**
5. **Model API errors**

---

## Decision Matrix

| Optimization | Impact | Effort | Risk | Priority | Implement? |
|-------------|--------|--------|------|----------|-----------|
| **1.1 Reduce transcript** | ⭐⭐⭐⭐⭐ | ⏱️ | 🟢 | P0 | ✅ YES |
| **1.2 Caching** | ⭐⭐⭐ | ⏱️⏱️ | 🟢 | P0 | ✅ YES |
| **1.3 Parallel processing** | ⭐⭐ | ⏱️⏱️⏱️ | 🟡 | P1 | ⚠️ MAYBE |
| **2.1 Streaming** | ⭐⭐⭐⭐ | ⏱️⏱️⏱️⏱️ | 🟡 | P1 | ✅ YES |
| **2.2 Client pre-screen** | ⭐⭐⭐⭐⭐ | ⏱️⏱️⏱️⏱️⏱️ | 🟡 | P2 | ⚠️ MAYBE |
| **2.3 Background + Push** | ⭐⭐⭐⭐⭐ | ⏱️⏱️⏱️⏱️⏱️⏱️ | 🔴 | P2 | ❌ NO (for now) |
| **3.1 Faster model** | ⭐⭐⭐⭐ | ⏱️⏱️⏱️⏱️ | 🟡 | P3 | 🔬 RESEARCH |
| **3.2 Hybrid on-device** | ⭐⭐⭐⭐⭐ | ⏱️⏱️⏱️⏱️⏱️⏱️⏱️ | 🔴 | P4 | 🔬 RESEARCH |

---

## Recommended Action Plan

### This Week (Immediate)

```bash
# 1. Implement transcript truncation
# Priority 1.1 - Expected: 70% improvement (16s → 5s)

# 2. Add simple caching
# Priority 1.2 - Expected: 30% improvement on cache hits

# 3. Measure and validate
# Run performance tests again
poetry run pytest tests/performance/ -v -s
```

### Next Sprint (Medium-term)

```bash
# 1. Add streaming response
# Priority 2.1 - Improves perceived latency

# 2. Research faster AI models
# Priority 3.1 - Benchmark alternatives
```

---

**Last Updated**: 2025-12-27
**Next Review**: After Week 1 implementation
