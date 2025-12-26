# CLAUDE.md - Project Configuration

---

## 🎯 Project Type

- **Prototype Backend API** (Python FastAPI)
- Not yet in production
- TDD for critical features only
- **Current Branch**: parents_rag_refine

---

## 🔒 Absolute Rules (Non-Negotiable)

**CRITICAL: These rules CANNOT be violated**

1. **❌ NEVER commit to main/master**
   - Always use staging/feature branches
   - Pre-commit hook will BLOCK commits to main

2. **❌ NEVER use `--no-verify`**
   - No `git commit --no-verify`
   - No `git push --no-verify`
   - Fix issues, don't bypass checks

3. **✅ TDD for critical features**
   - All console.html APIs require tests
   - Test FIRST, then implement
   - 106+ integration tests must pass

4. **✅ Integration tests required**
   - Every API endpoint needs ≥1 test
   - Tests define behavior (human-written)
   - AI implements code to pass tests

5. **🤖 ALL tasks through agent-manager**
   - Use `Task(subagent_type="agent-manager", ...)`
   - Preserves main context
   - Ensures TDD compliance

6. **📚 Update docs before EVERY push**
   - PRD.md (version, features, status)
   - CHANGELOG.md ([Unreleased] section)
   - CHANGELOG_zh-TW.md (sync with English)
   - Weekly report (if new week)
   - **NO EXCEPTIONS** - even small changes

---

## 🔧 Tool Chain

- **pytest**: Integration tests
- **ruff**: Linting + formatting (auto-fix)
- **httpx**: API testing
- **pre-commit**: Git hooks (auto-checks)

### Quick Commands

```bash
# Run tests
poetry run pytest tests/integration/ -v

# Fix formatting
ruff check --fix app/

# Install hooks (first time)
poetry run pre-commit install
poetry run pre-commit install --hook-type pre-push
```

---

## 🤖 Agent Configuration

### Model Assignment (Static)

- **Haiku** → test-runner (fast, cheap)
- **Sonnet** → All other agents (default)
- **Opus** → Manual switch for complex tasks

**Switch to Opus**:
```bash
/model claude-opus-4-5-20251101
```

**When to use Opus**:
- Critical/production tasks
- Security-sensitive changes
- Architecture refactoring (5+ files)
- Previous failures

### Available Slash Commands

- `/tdd` - Complete TDD workflow
- `/test-api` - Quick API testing
- `/review-pr` - PR review
- `/deploy-check` - Pre-deployment checks

---

## 📚 Detailed Workflows (Skills)

**All detailed processes are in Skills** with **AUTOMATIC ACTIVATION** (80%+ success rate):

| Skill | Purpose | Trigger Keywords |
|-------|---------|-----------------|
| **requirements-clarification** | Clarify requirements BEFORE coding | "需求", "requirement", "客戶要", "案主說" |
| **prd-workflow** | PRD-driven development | "PRD", "產品需求", "功能文檔", "規格書" |
| **tdd-workflow** | TDD development process | "new feature", "add API", "implement", "新功能" |
| **git-workflow** | Git commit/push workflow | "git", "commit", "push", "提交" |
| **api-development** | API development patterns | "API", "endpoint", "FastAPI", "測試 API" |
| **quality-standards** | Quality requirements | "quality", "refactor", "optimize", "品質" |
| **third-party-apis** | External API integration | "ElevenLabs", "OpenAI", "Gemini", "第三方 API" |
| **debugging** | Debug issues systematically | "bug", "error", "debug", "不work", "壞掉" |
| **error-handling** | Error handling patterns | "error", "exception", "validation", "錯誤處理" |
| **context-monitor** | Context usage monitoring | Auto-activates when context high |

### 🤖 Skill Auto-Activation System

**Status**: ACTIVE (since v3.1)
**Success Rate**: 80%+ (up from 20% baseline)

Skills now auto-activate via UserPromptSubmit hook:
1. **Keyword Detection** - Hook scans your message for trigger keywords
2. **Smart Injection** - Critical skills are forced to activate
3. **Zero User Action** - Happens automatically, every time

**Example**:
- You say: "我想新增一個 API endpoint"
- Hook detects: "API", "新增"
- Auto-activates: `api-development` + `tdd-workflow`
- You get: Full workflow guidance automatically

**Tech Details**:
- Hook: `.claude/hooks/skill-activation-hook.sh`
- Config: `.claude/config/skill-rules.json`
- Based on: [Scott Spence's research](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably) (84% success)

**Debugging Auto-Activation**:
```bash
# Test what skills activate for a prompt
echo "your prompt here" | .claude/hooks/skill-activation-hook.sh
```

**Reference**: See `.claude/hooks/README.md` for full documentation

---

## 🚀 Development Philosophy

### Core Principle

> **"Prototype 求快不求完美。功能驗證完才追求品質。"**

### What We Do

- ✅ Rapid prototyping
- ✅ AI-assisted development
- ✅ TDD for critical features
- ✅ Human verification

### What We Don't Do

- ❌ Production-grade quality (yet)
- ❌ 100% test coverage
- ❌ Over-engineering

### Time Allocation

- 70% Development
- 20% Testing
- 10% Refactoring

**Reference**: See `quality-standards` skill for full details.

---

## 🎯 Quick Reference

### Before Commit

```bash
git add .
git commit -m "feat: description"
# ↓ Auto-runs (~5s):
# - Branch check
# - Ruff linting
# - Security scan
```

### Before Push

```bash
git push
# ↓ Auto-runs (~10s):
# - Smoke tests
# - Doc verification
# Full tests in CI (~2 min)
```

**Reference**: See `git-workflow` skill for full Git workflow.

---

## 🔍 Getting Help

### For Detailed Workflows

Ask Claude to activate relevant Skill:
- "How do I use TDD?" → Activates `tdd-workflow` skill
- "Git workflow?" → Activates `git-workflow` skill
- "API development?" → Activates `api-development` skill

### For Coding Tasks

All development tasks go through agent-manager:
- Mention your goal (e.g., "add client search API")
- agent-manager routes to appropriate subagent
- TDD workflow automatically enforced

---

## 📊 Success Metrics

- ✅ Zero commits to main/master
- ✅ 100% console.html APIs have tests
- ✅ All commits pass pre-commit hooks
- ✅ All pushes have updated docs
- ✅ No use of `--no-verify`

---

## 🔗 Related Documentation

- **Skills Directory**: `.claude/skills/` - Detailed workflows
- **Agents Directory**: `.claude/agents/` - Task executors
- **Commands Directory**: `.claude/commands/` - Slash commands
- **Hooks Directory**: `.claude/hooks/` - Auto-activation system
- **Config Directory**: `.claude/config/` - Skill rules and settings
- **PRD.md**: Product requirements
- **CHANGELOG.md**: Change history

---

**Version**: v3.1 (Skill Auto-Activation System)
**Last Updated**: 2025-12-25
**Philosophy**: Context efficiency through progressive disclosure + intelligent automation
