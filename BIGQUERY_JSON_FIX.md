# BigQuery JSON Field Serialization Fix

## Problem

BigQuery JSON type fields were rejecting data with error:
```
This field: analysis_result is not a record.
```

**Root Cause**: BigQuery's `insert_rows_json()` method expects JSON type fields to be passed as **JSON strings**, not Python dicts/lists.

## Solution

Modified `/Users/young/project/career_ios_backend/app/services/gbq_service.py`:

### Changed Function
Updated `ensure_json_serializable()` helper function to convert Python objects to JSON strings:

**Before**:
```python
def ensure_json_serializable(obj):
    """Ensure object is JSON-serializable for BigQuery JSON fields"""
    if obj is None:
        return None
    if isinstance(obj, (dict, list)):
        # For JSON fields, BigQuery insert_rows_json expects them as-is (not stringified)
        # but we need to ensure they're JSON-serializable
        return json.loads(json.dumps(obj, default=str))
    return obj
```

**After**:
```python
def ensure_json_serializable(obj):
    """Convert Python dicts/lists to JSON strings for BigQuery JSON fields

    BigQuery JSON type fields require JSON **strings**, not Python dicts.
    This converts Python objects to JSON strings using json.dumps().
    """
    if obj is None:
        return None
    if isinstance(obj, (dict, list)):
        # CRITICAL: BigQuery JSON fields MUST be JSON strings
        return json.dumps(obj, default=str)
    return obj
```

### Affected Fields
The fix applies to three JSON type fields in the schema:
1. `speakers` (line 100) - List of speaker/text pairs
2. `rag_documents` (line 108) - List of RAG document metadata
3. `analysis_result` (line 131) - Analysis result with suggestions/confidence

## Testing

### Test Results
```bash
$ poetry run python test_gbq_fix.py
✅ SUCCESS! JSON fields were properly serialized and written to BigQuery
```

### Integration Tests
```bash
$ poetry run pytest tests/integration/test_gbq_service_real.py -v
======================== 7 passed in 50.84s ========================
```

### Verification Query
```python
# Query shows JSON fields are properly stored and retrieved
SELECT speakers, rag_documents, analysis_result
FROM `groovy-iris-473015-h3.realtime_logs.realtime_analysis_logs`
ORDER BY analyzed_at DESC LIMIT 1

# Results confirm:
# - Speakers type: <class 'list'> ✅
# - RAG Documents type: <class 'list'> ✅
# - Analysis Result type: <class 'dict'> ✅
```

## Impact

- **Before**: BigQuery rejected all writes with JSON fields
- **After**: All JSON fields are properly serialized and stored
- **No data loss**: Fix is backwards compatible
- **No breaking changes**: All existing tests pass

## Key Takeaway

When using BigQuery's JSON data type with Python:
- Schema defines field as `JSON` type
- Python dict/list must be converted to JSON string using `json.dumps()`
- BigQuery will parse the JSON string and store it as native JSON
- When reading, BigQuery client returns parsed Python objects (dict/list)

---

**Fixed**: 2025-12-25
**Test ID**: 90200ddb-a92b-487b-8226-241168166b0c
**Status**: Verified in production ✅
