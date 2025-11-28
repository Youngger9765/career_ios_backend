---
name: deploy-check
description: Pre-deployment verification checklist
---

# Deploy Check Command

Complete pre-deployment verification for staging branch.

## Automatic Verification:

### 1. Branch Verification
```bash
# Ensure on staging branch
git branch --show-current
# Should be: staging
```

### 2. Test Suite (via test-runner subagent)
```bash
# Run all integration tests
poetry run pytest tests/integration/ -v

Expected: 106+ tests PASS
```

### 3. Code Quality (via code-reviewer subagent)
- ✅ Ruff formatting clean
- ✅ No critical issues
- ✅ TDD compliance

### 4. Git Status
```bash
# Check clean state
git status

Expected: Nothing to commit, working tree clean
```

### 5. Recent Commits
```bash
# Show last 5 commits
git log --oneline -5

Verify: All commits follow conventional format
```

### 6. CI/CD Readiness
**Before Push:**
- [ ] All tests pass locally
- [ ] Code formatted
- [ ] No secrets committed
- [ ] Commit messages clean

**After Push:**
- [ ] Monitor: `gh run watch`
- [ ] Wait for CI green
- [ ] Check Cloud Run deployment
- [ ] Verify health check

## Deployment Checklist Output:

```
🚀 Deploy Readiness Check

✅ Branch: staging
✅ Tests: 106/106 PASSED
✅ Code Quality: APPROVED
✅ Git Status: Clean
✅ Recent Commits: 5 commits, properly formatted

🟢 READY TO DEPLOY

Next steps:
1. git push
2. gh run watch
3. Monitor deployment health
```

---

**Running deployment checks...**

Automatically coordinating verification...
