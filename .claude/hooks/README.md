# Claude Code Hooks - Skill Auto-Activation System

## Overview

This directory contains hooks that automatically activate Claude Code Skills based on user prompts, improving activation rates from **20% to 80%+**.

## System Architecture

### Components

1. **skill-activation-hook.sh** - Keyword-based skill activation (CURRENTLY ACTIVE)
2. **skill-forced-eval-hook.sh** - Forced evaluation approach (alternative)
3. **skill-rules.json** - Skill configuration and keyword mappings
4. **check-agent-rules.py** - Agent-manager TDD compliance checker

### How It Works

```
User Prompt
    ↓
skill-activation-hook.sh (reads skill-rules.json)
    ↓
Keyword Matching
    ↓
Inject Skill Activation Commands
    ↓
Modified Prompt → Claude
    ↓
Skills Auto-Activate
```

## Hook Types

### 1. Keyword-Based Activation (skill-activation-hook.sh)

**Status**: Currently Active
**Success Rate**: ~75-80%
**Speed**: Fast (<100ms)

This hook analyzes user prompts for keywords and automatically injects Skill activation commands.

**Example Input**:
```
我想新增一個 API endpoint
```

**Example Output**:
```
🚨 CRITICAL: The following skills MUST be activated for this request:

- **api-development** (MANDATORY)
- **tdd-workflow** (MANDATORY)

🎯 INSTRUCTION: Use the Skill tool IMMEDIATELY before proceeding:

Skill(skill="api-development")
Skill(skill="tdd-workflow")

⚠️ IMPORTANT: Do NOT start implementation without activating these skills.

---

我想新增一個 API endpoint
```

### 2. Forced Evaluation (skill-forced-eval-hook.sh)

**Status**: Available (disabled by default)
**Success Rate**: ~84% (Scott Spence research)
**Speed**: Slower (more verbose)

This hook forces Claude to explicitly evaluate EVERY skill before proceeding.

**When to Use**:
- Critical/production tasks
- When keyword-based approach fails
- Maximum activation reliability needed

**How to Enable**:
Edit `.claude/settings.json`:
```json
{
  "eventName": "UserPromptSubmit",
  "type": "command",
  "command": "./.claude/hooks/skill-forced-eval-hook.sh",
  "timeout": 5
}
```

## Configuration

### skill-rules.json Structure

```json
{
  "skills": {
    "skill-name": {
      "description": "Skill purpose",
      "keywords": ["keyword1", "keyword2", "關鍵字"],
      "force_activation": true,
      "priority": "critical",
      "activation_message": "MANDATORY: Use this skill..."
    }
  }
}
```

### Priority Levels

- **critical** - Must activate (blocking)
- **high** - Should activate (strong recommendation)
- **medium** - May activate (suggestion)
- **low** - Optional

### Keyword Matching

Keywords support:
- English: "bug", "error", "API"
- Chinese: "需求", "測試", "客戶要"
- Case-insensitive matching
- Partial word matching

## Testing

### Test the Hook Manually

```bash
# Test with requirements keyword
echo "客戶要一個新功能" | ./.claude/hooks/skill-activation-hook.sh

# Test with bug keyword
echo "There's a bug in the system" | ./.claude/hooks/skill-activation-hook.sh

# Test with API keyword
echo "Add new API endpoint" | ./.claude/hooks/skill-activation-hook.sh

# Test with git keyword
echo "commit and push changes" | ./.claude/hooks/skill-activation-hook.sh
```

### Expected Output

You should see:
1. 🚨 CRITICAL section (if critical skills matched)
2. 💡 Recommended section (if optional skills matched)
3. 🎯 INSTRUCTION with Skill() calls
4. Original user prompt

## Adding New Skills

1. **Create skill directory**:
   ```bash
   mkdir -p .claude/skills/your-skill-name
   ```

2. **Update skill-rules.json**:
   ```json
   {
     "your-skill-name": {
       "description": "What the skill does",
       "keywords": ["trigger1", "trigger2"],
       "force_activation": true,
       "priority": "high",
       "activation_message": "MANDATORY: Use your-skill-name..."
     }
   }
   ```

3. **Test the trigger**:
   ```bash
   echo "trigger1 test" | ./.claude/hooks/skill-activation-hook.sh
   ```

## Troubleshooting

### Hook Not Activating

1. **Check hook is executable**:
   ```bash
   chmod +x .claude/hooks/skill-activation-hook.sh
   ```

2. **Check settings.json**:
   ```bash
   cat .claude/settings.json | grep -A 5 "skill-activation"
   ```

3. **Test manually**:
   ```bash
   echo "test prompt" | ./.claude/hooks/skill-activation-hook.sh
   ```

### Keywords Not Matching

1. **Check skill-rules.json syntax**:
   ```bash
   python3 -m json.tool .claude/config/skill-rules.json
   ```

2. **Add more keywords**:
   - Add variations (e.g., "bug", "bugs", "buggy")
   - Add Chinese/English equivalents
   - Use broader terms

### Python Not Found

The hook requires Python 3. Check:
```bash
which python3
python3 --version
```

## Performance

### Keyword-Based Hook
- **Execution Time**: <100ms
- **Token Cost**: Minimal (adds ~50-100 tokens)
- **Success Rate**: 75-80%

### Forced Eval Hook
- **Execution Time**: Same as keyword-based
- **Token Cost**: Higher (adds ~200-300 tokens)
- **Success Rate**: 84%

## Best Practices

1. **Use keyword-based by default** - Fast and effective
2. **Switch to forced eval for critical tasks** - Higher reliability
3. **Keep keywords updated** - Add new triggers as patterns emerge
4. **Monitor activation rates** - Check if skills are actually activating
5. **Combine with explicit calls** - For 100% reliability, still use manual Skill() calls

## References

- [Scott Spence's Research](https://scottspence.com/posts/how-to-make-claude-code-skills-activate-reliably) - 84% success with forced eval
- [diet103's Infrastructure Showcase](https://github.com/diet103/claude-code-infrastructure-showcase) - Generic skill activation patterns

## Version History

- **v1.0** (2025-12-25) - Initial implementation with keyword-based and forced eval hooks

---

**Last Updated**: 2025-12-25
**Maintained By**: Career iOS Backend Team
