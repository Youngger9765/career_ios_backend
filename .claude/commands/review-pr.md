---
name: review-pr
description: Comprehensive PR review with TDD compliance check
---

# PR Review Command

Comprehensive review for current branch changes.

## Automatic Review Process:

### 1. Invoke Code Reviewer Subagent
Automatically performs comprehensive review including:

### 2. What Gets Checked:

✅ **TDD Compliance**
- Tests exist for all new/modified endpoints
- Tests pass (GREEN state)
- Integration test coverage

✅ **Code Quality**
- Follows project patterns
- Proper error handling
- Authentication applied

✅ **Security**
- No hardcoded secrets
- Input validation
- Authorization checks

✅ **Project Standards**
- Ruff formatting
- CLAUDE.md compliance
- Console API coverage

### 3. Review Output:

You will receive:
- ✅ What's good
- ❌ Critical issues (must fix)
- ⚠️  Warnings (should fix)
- 🟢 Suggestions (optional)
- 📊 Overall approval status

### 4. Commit Readiness:

**APPROVED** ✅
- Ready to commit and push
- Suggested commit message

**CHANGES NEEDED** ❌
- List of required fixes
- Can auto-fix or needs manual attention

---

**Reviewing current branch...**

Invoking code-reviewer subagent now...
