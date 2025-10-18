# CLAUDE.md - Development Guidelines

---

## 🔒 MANDATORY RULES (Self-Recursive - MUST Display Every Response)

**⚠️ BEFORE responding to ANY request, you MUST display:**

```
═══════════════════════════════════════
🔒 Rules Check ✓
═══════════════════════════════════════
1. ❌ No commit to main/master
2. ❌ No Claude attribution in commits
3. ✅ Confirm before commit
4. ✅ Confirm before push
5. 📢 Show rules every response
═══════════════════════════════════════
```

### Core Rules

1. **❌ NEVER commit to main or master branch**
   - Always check current branch first: `git branch --show-current`
   - If on main/master → STOP and tell user to create feature branch

2. **❌ NEVER add Claude attribution in commit messages**
   - ✅ Allowed: `feat: add user login`
   - ❌ Forbidden: `feat: add user login 🤖 Generated with Claude`
   - ❌ Forbidden: `Co-Authored-By: Claude <noreply@anthropic.com>`

3. **✅ Commit confirmation rules**
   - If user says "commit" → Treat as "yes", proceed directly
   - If user says "commit changes" → Treat as "yes", proceed directly
   - Otherwise: Ask "確定要 commit 嗎？(y/n)" and wait

4. **✅ Push confirmation rules**
   - If user says "push" → Treat as "yes", proceed directly
   - Otherwise: Ask "確定要 push 嗎？(y/n)" and wait

5. **📢 MUST display these 5 rules at the start of EVERY response**
   - This ensures you never forget the rules
   - Even after long conversations

### Git Workflow (MANDATORY)

```
Step 1: Check branch
  ↓
git branch --show-current
  ↓
Step 2: Validate
  ↓
main/master? → ❌ STOP, tell user
feature branch? → ✅ Continue
  ↓
Step 3: Ask confirmation
  ↓
"確定要 commit/push 嗎？(y/n)"
  ↓
Step 4: Wait for "y"
  ↓
Step 5: Execute (NO Claude attribution)
```

---

## Test-Driven Development (TDD)

### Core TDD Principles (2025 Best Practices)

1. **Red-Green-Refactor Cycle**
   - ❌ RED: Write a failing test first
   - ✅ GREEN: Write minimal code to pass the test
   - ♻️ REFACTOR: Improve code while keeping tests green

2. **Write Tests First, Always**
   - Tests define requirements before implementation
   - Focus on behavior, not implementation details
   - Each test should be small, atomic, and focused

3. **Comprehensive Test Coverage**
   - Happy path scenarios
   - Negative tests (failure conditions)
   - Edge cases and boundary values
   - Equivalence partitioning

4. **Keep Units Small**
   - Small, focused functions/modules
   - Easier to test, debug, and maintain
   - Faster iteration cycle

### TDD with AI-Assisted Coding (Kent Beck's Approach)

**Kent Beck's "Augmented Coding" Principles:**

1. **TDD is a Superpower with AI**
   - Tests guide AI assistants to correct implementations
   - Prevents AI from introducing bugs
   - AI struggles with refactoring; TDD provides safety net

2. **Challenges to Watch For**
   - AI may try to delete tests to make code "pass" ❌
   - AI excels at adding features, struggles with simplification
   - Complexity can exceed AI's capacity to help

3. **Best Practices for AI + TDD**
   - Write tests before asking AI to implement
   - Review AI-generated code against test requirements
   - Use tests to catch AI hallucinations
   - Refactor frequently to prevent complexity buildup
   - Keep test setups simple for AI comprehension

4. **Workflow**
   ```
   1. Define behavior in test (human writes)
   2. Run test → RED
   3. Ask AI to implement minimal solution
   4. Run test → GREEN
   5. Human reviews code quality
   6. Refactor (human-led, AI-assisted)
   7. Tests still GREEN → commit
   ```

## Git Workflow Rules

### Commit & Push Policy

**STRICTLY FORBIDDEN:**
- ❌ `git commit --no-verify`
- ❌ `git push --no-verify`
- ❌ Bypassing pre-commit hooks in any way
- ❌ Committing without passing tests
- ❌ Random/unplanned commits

**REQUIRED:**
- ✅ All commits must pass pre-commit hooks
- ✅ All tests must be GREEN before commit
- ✅ Meaningful commit messages following conventions
- ✅ Code review (even for AI-generated code)

### Pre-commit Hook Strategy

**Mandatory Checks (before every commit):**
1. Code formatting (Ruff)
2. Linting (Ruff with --fix)
3. Type checking (MyPy)
4. Test execution (pytest)
5. YAML/TOML validation
6. Large file prevention
7. Trailing whitespace removal

**Configuration: `.pre-commit-config.yaml`**

## Development Workflow

### 1. Feature Development Process

```
┌─────────────────────────────────────┐
│ 1. Understand Requirement           │
├─────────────────────────────────────┤
│ 2. Write Test (RED)                 │
├─────────────────────────────────────┤
│ 3. Minimal Implementation (GREEN)   │
├─────────────────────────────────────┤
│ 4. Refactor (tests stay GREEN)      │
├─────────────────────────────────────┤
│ 5. Pre-commit checks pass           │
├─────────────────────────────────────┤
│ 6. Code review                      │
├─────────────────────────────────────┤
│ 7. Commit with meaningful message   │
└─────────────────────────────────────┘
```

### 2. AI Collaboration Rules

**When using AI (Claude/GitHub Copilot):**
- Always write tests first yourself
- Review all AI-generated code line by line
- Never accept AI suggestions blindly
- AI writes implementation, human owns quality
- Tests are the contract, AI must fulfill it

### 3. Code Quality Standards

**Every piece of code must:**
- Have corresponding tests (minimum 80% coverage)
- Pass all linting checks
- Have type hints (Python 3.9+)
- Be reviewed before commit
- Follow project coding conventions

## Project-Specific Guidelines

### FastAPI + Supabase + OpenAI Stack

**Testing Strategy:**
1. **Unit Tests**: Services (OpenAI, PDF processing, chunking)
2. **Integration Tests**: API endpoints with test database
3. **E2E Tests**: Complete RAG flow (upload → embed → query)

**Test Structure:**
```
tests/
├── unit/
│   ├── test_openai_service.py
│   ├── test_pdf_service.py
│   └── test_chunking.py
├── integration/
│   ├── test_ingest_api.py
│   └── test_search_api.py
└── e2e/
    └── test_rag_flow.py
```

**Mock Strategy:**
- Mock OpenAI API calls (use fixtures)
- Mock Supabase for unit tests
- Use test database for integration tests
- Real services only in E2E tests

## Continuous Integration

**Pre-push Checklist:**
- [ ] All tests pass locally
- [ ] Pre-commit hooks pass
- [ ] Code reviewed
- [ ] No debug prints or commented code
- [ ] Documentation updated if needed
- [ ] No secrets in code

**CI Pipeline Must:**
1. Run all tests
2. Check code coverage (min 80%)
3. Run linting and type checking
4. Build Docker images
5. Deploy to staging (if main branch)

## References

- **TDD Best Practices 2025**: [BrowserStack Guide](https://www.browserstack.com/guide/what-is-test-driven-development)
- **Kent Beck on AI + TDD**: [Pragmatic Engineer Podcast](https://newsletter.pragmaticengineer.com/p/tdd-ai-agents-and-coding-with-kent)
- **Pre-commit Framework**: [pre-commit.com](https://pre-commit.com/)
- **FastAPI Testing**: [FastAPI Official Docs](https://fastapi.tiangolo.com/tutorial/testing/)

---

**Remember: Code without tests is legacy code. Tests without passing are todos. Commits without hooks are technical debt.**