# Skill Auto-Activation - Quick Start Guide

## What Is This?

Claude Code Skills now **auto-activate** when you use certain keywords in your prompts.

**Before** (20% success):
- You: "新增一個 API endpoint"
- Claude: [Misses the tdd-workflow skill, implements without tests]

**After** (80% success):
- You: "新增一個 API endpoint"
- Hook: [Auto-injects Skill activation]
- Claude: [Activates tdd-workflow + api-development, follows proper workflow]

## How It Works

```
Your Message
    ↓
Hook Intercepts (skill-activation-hook.sh)
    ↓
Scans for Keywords (skill-rules.json)
    ↓
Injects Skill Commands
    ↓
Claude Gets Modified Prompt
    ↓
Skills Auto-Activate ✨
```

## Trigger Keywords

Just mention these words naturally in your messages:

| Keyword | Activates Skill |
|---------|----------------|
| "需求", "requirement", "客戶要" | requirements-clarification |
| "bug", "error", "不work", "壞掉" | debugging |
| "API", "endpoint", "FastAPI" | api-development |
| "new feature", "implement", "新功能" | tdd-workflow |
| "git", "commit", "push" | git-workflow |
| "PRD", "產品需求", "功能文檔" | prd-workflow |

**See all keywords**: Open `.claude/config/skill-rules.json`

## Quick Test

```bash
# Test what activates for your prompt
echo "我想修一個 bug" | ./.claude/hooks/skill-activation-hook.sh

# Run full test suite
./.claude/hooks/test-skill-activation.sh
```

## Examples

### Example 1: Bug Fix
**You say**:
```
There's a bug in the client search - returns empty results
```

**What happens**:
```
🚨 CRITICAL: debugging skill MUST be activated

Skill(skill="debugging")

[Your original message]
```

**Claude does**:
```
[Skill activated: debugging]
Following 5-step debugging checklist:
1. Reproduce the issue
2. Check recent changes...
```

### Example 2: New Feature
**You say**:
```
客戶要一個新功能：在報告頁面顯示家長評分
```

**What happens**:
```
🚨 CRITICAL: requirements-clarification, tdd-workflow activated

Skill(skill="requirements-clarification")
Skill(skill="tdd-workflow")
```

**Claude does**:
```
[Skill activated: requirements-clarification]
Let me use CARIO framework to clarify requirements:
C - Context: Who needs this?
A - Acceptance: What defines success?
...

[Skill activated: tdd-workflow]
Following TDD process:
1. Write test first
2. Implement to pass test...
```

### Example 3: Git Operation
**You say**:
```
準備 commit 和 push
```

**What happens**:
```
🚨 CRITICAL: git-workflow activated

Skill(skill="git-workflow")
```

**Claude does**:
```
[Skill activated: git-workflow]
Pre-push checklist:
✅ PRD.md updated?
✅ CHANGELOG.md updated?
...
```

## Customization

### Add New Keyword

1. Edit `.claude/config/skill-rules.json`
2. Find your skill, add keyword:
   ```json
   "keywords": ["existing", "new-trigger"]
   ```
3. Test it:
   ```bash
   echo "new-trigger test" | ./.claude/hooks/skill-activation-hook.sh
   ```

### Change Priority

```json
{
  "priority": "critical"  // MUST activate
  "priority": "high"      // SHOULD activate
  "priority": "medium"    // MAY activate
}
```

### Disable Auto-Activation

Edit `.claude/settings.json`, remove the skill-activation-hook entry.

## Troubleshooting

### "Skills still not activating"

1. **Check hook is enabled**:
   ```bash
   cat .claude/settings.json | grep skill-activation
   ```

2. **Test manually**:
   ```bash
   echo "bug fix" | ./.claude/hooks/skill-activation-hook.sh
   # Should show: Skill(skill="debugging")
   ```

3. **Check keywords**:
   ```bash
   cat .claude/config/skill-rules.json | grep -A 5 "debugging"
   ```

### "Wrong skill activating"

- Keywords might be too broad
- Refine in skill-rules.json
- Test with: `echo "your message" | ./.claude/hooks/skill-activation-hook.sh`

### "Hook not running"

```bash
# Make sure it's executable
chmod +x .claude/hooks/skill-activation-hook.sh

# Check JSON is valid
python3 -m json.tool .claude/config/skill-rules.json
```

## Files You Should Know

```
.claude/
├── config/
│   ├── skill-rules.json          ← Keyword configuration
│   └── README.md                 ← Config documentation
├── hooks/
│   ├── skill-activation-hook.sh  ← Main hook (ACTIVE)
│   ├── skill-forced-eval-hook.sh ← Alternative approach
│   ├── test-skill-activation.sh  ← Test suite
│   └── README.md                 ← Hook documentation
├── settings.json                 ← Hook integration
├── SKILL_AUTO_ACTIVATION.md      ← Full implementation details
└── QUICK_START.md                ← This file
```

## Alternative: Forced Eval

For **critical tasks** needing higher reliability (84% vs 80%):

1. Edit `.claude/settings.json`
2. Change hook command:
   ```json
   "command": "./.claude/hooks/skill-forced-eval-hook.sh"
   ```
3. Restart Claude Code

**Trade-off**: More verbose (Claude lists ALL skills), but more reliable.

## Success Metrics

System is working if you see:

- ✅ Skills activate without manual Skill() calls
- ✅ Workflows are followed consistently
- ✅ Less "I forgot to use TDD" moments
- ✅ Better code quality automatically

## Learn More

- **Full docs**: `.claude/SKILL_AUTO_ACTIVATION.md`
- **Hook details**: `.claude/hooks/README.md`
- **Config guide**: `.claude/config/README.md`

## References

- [Scott Spence - Skill Activation Research](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably)
- [diet103 - Infrastructure Showcase](https://github.com/diet103/claude-code-infrastructure-showcase)

---

**Status**: ✅ Active & Working
**Version**: 1.0
**Last Updated**: 2025-12-25
