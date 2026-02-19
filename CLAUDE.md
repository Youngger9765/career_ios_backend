# Career iOS Backend

> 通用規則見 `~/.claude/CLAUDE.md`（Agent 路由、Git、Security、TDD）

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI |
| Testing | pytest + httpx |
| Linting | ruff (auto-fix) |
| Hooks | pre-commit |

## GCP Configuration

| Field | Value |
|-------|-------|
| gcloud config | `career-ios-app` |
| Account | `dev02@careercreator.tw` |
| GCP Project | `career-creator-card` |
| Region | `asia-east1` |

> Hook auto-switches. If permission error → `gcloud config configurations activate career-ios-app`

## Project Type

- **Prototype Backend API**
- Not yet in production
- TDD for critical features
- **Current Branch**: staging

## Project-Specific Rules

1. **❌ NEVER commit to main/master** - use staging/feature branches
2. **Browser Testing = Claude 自動執行** - 使用 `mcp__claude-in-chrome__*`
3. **AI 輸出驗證** - min/max 驗證、max_tokens 500+、不硬截斷
4. **📚 Update docs before EVERY push** - PRD.md, CHANGELOG.md

## Commands

```bash
# Run tests
poetry run pytest tests/integration/ -v

# Fix formatting
ruff check --fix app/

# Install hooks
poetry run pre-commit install
```

## Model Assignment

| Model | Use Case |
|-------|----------|
| Haiku | test-runner (fast) |
| Sonnet | All other agents |
| Opus | Critical/production tasks |

## Slash Commands

- `/tdd` - Complete TDD workflow
- `/test-api` - Quick API testing
- `/review-pr` - PR review

## Key Docs

- `.claude/skills/` - Detailed workflows
- `.claude/agents/` - Task executors
- `PRD.md` - Product requirements
- `CHANGELOG.md` - Change history

## Philosophy

> **"Prototype 求快不求完美。功能驗證完才追求品質。"**

- 70% Development / 20% Testing / 10% Refactoring
