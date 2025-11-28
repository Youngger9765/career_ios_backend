---
name: test-api
description: Quick test for specific API endpoint
---

# Test API Command

Quick test execution for: **$ARGUMENTS**

## Automatic Actions:

### 1. Invoke Test Runner Subagent
Automatically runs tests for the specified API and fixes any failures.

### 2. Test Execution
```bash
# If $ARGUMENTS provided (e.g., "clients"):
poetry run pytest tests/integration/test_${ARGUMENTS}_api.py -v

# If no arguments, run all integration tests:
poetry run pytest tests/integration/ -v
```

### 3. Auto-Fix Failures
If tests fail, test-runner will:
- Analyze failure reason
- Fix implementation code (NOT tests)
- Re-run until GREEN

### 4. Report Results
You will see:
- ✅ Pass count
- ❌ Fail count (and auto-fixes applied)
- ⏱️  Duration

---

**Testing API: $ARGUMENTS**

Invoking test-runner subagent now...
