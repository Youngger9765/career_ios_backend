# Model Selection Strategy

## Available Models

| Model | Speed | Cost | Best For |
|-------|-------|------|----------|
| **Haiku** | ⚡⚡⚡ | $ | Simple, fast tasks |
| **Sonnet 4.5** | ⚡⚡ | $$ | General development |
| **Opus** | ⚡ | $$$ | Complex, critical tasks |

## Auto-Selection Rules

### 🟢 Use Haiku (Fast & Cheap)
- Running tests (`test-runner`)
- Code formatting/linting
- Simple CRUD operations
- File reading/listing
- Log analysis
- Pattern matching

**Estimated time**: < 10 seconds
**Cost**: ~1/10 of Sonnet

### 🟡 Use Sonnet 4.5 (Default - Balanced)
- Writing tests (`test-writer`)
- Code generation (`code-generator`)
- Bug fixes
- Feature development
- Code review (`code-reviewer`)
- TDD orchestration (`tdd-orchestrator`)
- API design

**Estimated time**: 10-30 seconds
**Cost**: Baseline

### 🔴 Use Opus (Powerful & Expensive)
- Complex architecture refactoring
- Security-critical code review
- Algorithm optimization
- Multi-file refactoring (5+ files)
- Critical production bug fixes
- Complex RAG/AI features

**Estimated time**: 30-60+ seconds
**Cost**: ~3x Sonnet

## Agent-Specific Assignments

```yaml
# Fast agents (Haiku)
test-runner: haiku           # Just run pytest and report
code-formatter: haiku        # ruff format

# Balanced agents (Sonnet 4.5)
test-writer: sonnet          # Need good test design
code-generator: sonnet       # Need good implementation
code-reviewer: sonnet        # Need thorough review
tdd-orchestrator: sonnet     # Coordination logic

# Smart router (Sonnet/Opus)
agent-manager: sonnet        # Usually, but can escalate to Opus

# Complex tasks (Opus - on demand)
architect: opus              # Architecture decisions
security-reviewer: opus      # Security audits
```

## Dynamic Model Selection (agent-manager)

Agent-manager can escalate to Opus when:
- Prompt mentions "complex", "critical", "production"
- Task involves 5+ files
- Previous Sonnet attempts failed
- Security/data loss risk detected

## Implementation (CURRENT LIMITATION)

### ✅ What Works: Static Configuration
Each agent has fixed model in frontmatter:
```yaml
---
name: test-runner
model: haiku  # This WORKS - Claude Code reads this
---
```

**Execution**: When Claude invokes `Task(subagent_type="test-runner", ...)`,
Claude Code automatically uses the model specified in test-runner.md frontmatter.

### ✅ What WORKS: Automatic Model Switching via SlashCommand
```python
# ✅ THIS WORKS - agent-manager can execute slash commands!
SlashCommand("/model opus")  # Switch to opus

# Now all agents use opus
Task(subagent_type="tdd-orchestrator", ...)

# Switch back when done
SlashCommand("/model sonnet")
```

**How It Works**:
1. agent-manager detects task complexity
2. Executes `SlashCommand("/model opus")`
3. Invokes agents (they all use opus now)
4. Executes `SlashCommand("/model sonnet")` to restore default

### ❌ What Doesn't Work: Per-Agent Model Override
```python
# ❌ Still not possible - cannot override individual agent models
Task(
    subagent_type="code-generator",
    model="opus",  # ❌ This parameter doesn't exist!
    ...
)
```

**Why**: Task tool doesn't accept `model` parameter.
**Solution**: Use SlashCommand to switch global model before invoking agents.

## Cost-Benefit Analysis

**Current setup (all Sonnet):**
- 10 agent calls = 10 Sonnet = $$$

**Optimized setup:**
- 5 Haiku (tests, formatting) = $
- 4 Sonnet (dev, review) = $$
- 1 Opus (critical) = $$$
- **Total: ~40% cost reduction**

## Recommendations

1. **Immediate**: Update agent model assignments
   - test-runner → Haiku
   - test-writer → Sonnet
   - code-generator → Sonnet
   - code-reviewer → Sonnet
   - tdd-orchestrator → Sonnet
   - agent-manager → Sonnet (can escalate)

2. **Short-term**: Add model hints in hook
   ```
   🎬 TASK [development] → USE AGENT-MANAGER
      Suggested model: Sonnet (balanced)
   ```

3. **Long-term**: Implement dynamic model selection in agent-manager
   - Analyze task complexity
   - Auto-escalate to Opus when needed
   - Track success rates per model

## Examples

```yaml
# Simple test run
Task: "Run tests for sessions API"
Agent: test-runner
Model: Haiku ⚡
Time: ~5s
Cost: $

# Feature development
Task: "Add session name field with TDD"
Agent: tdd-orchestrator → test-writer → code-generator → test-runner → code-reviewer
Models: Sonnet → Sonnet → Sonnet → Haiku → Sonnet
Total time: ~40s
Cost: $$

# Critical refactoring
Task: "Refactor entire authentication system with security audit"
Agent: agent-manager → architect (Opus) → security-reviewer (Opus)
Models: Sonnet → Opus → Opus
Total time: ~90s
Cost: $$$
```

## Monitoring

Track metrics to optimize:
- Model usage distribution
- Success rate per model
- Average completion time
- Cost per task type

Target distribution:
- 40% Haiku (simple tasks)
- 50% Sonnet (development)
- 10% Opus (complex/critical)
