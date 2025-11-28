---
name: tdd
description: Start complete TDD workflow for new feature
---

# TDD Workflow Command

Execute complete Test-Driven Development workflow for: **$ARGUMENTS**

## Automatic Steps (No user intervention needed):

### 1. Invoke TDD Orchestrator Subagent
The orchestrator will automatically:
- ✅ Invoke test-writer to create tests (RED)
- ✅ Invoke code-generator to implement (GREEN)
- ✅ Invoke test-runner to verify all tests
- ✅ Invoke code-reviewer for quality check

### 2. Report Results
You will see:
- ❌ RED: Test created and failing
- ✅ GREEN: Code implemented, tests passing
- 🧪 VERIFY: All 106+ tests still pass
- ♻️ REFACTOR: Code review complete

### 3. Ready to Commit
When workflow completes:
- All tests pass
- Code reviewed
- Ready for git commit

---

**Starting TDD workflow for: $ARGUMENTS**

Invoking tdd-orchestrator subagent now...
