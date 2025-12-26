# Skill Rules Configuration

## Overview

This directory contains configuration files for Claude Code's Skill auto-activation system.

## Files

### skill-rules.json

Defines skill activation rules, keywords, and priorities.

**Structure**:
```json
{
  "skills": {
    "skill-name": {
      "description": "What this skill does",
      "keywords": ["trigger", "words", "關鍵字"],
      "force_activation": true/false,
      "priority": "critical|high|medium|low",
      "activation_message": "Message shown when skill activates"
    }
  },
  "activation_strategy": {
    "method": "forced_eval|keyword_matching",
    "fallback": "keyword_matching",
    "min_confidence": 0.7,
    "max_skills_per_prompt": 3
  }
}
```

## Priority Levels

| Priority | Behavior | When to Use |
|----------|----------|-------------|
| **critical** | Must activate (blocking) | Core workflows (TDD, requirements) |
| **high** | Should activate (strong rec) | Important patterns (Git, debugging) |
| **medium** | May activate (suggestion) | Optional helpers (quality, third-party) |
| **low** | Optional | Monitoring, context tools |

## Adding Keywords

1. **Open skill-rules.json**
2. **Find your skill**
3. **Add keyword to array**:
   ```json
   "keywords": ["existing", "new-keyword", "新關鍵字"]
   ```
4. **Test it**:
   ```bash
   echo "new-keyword test" | ./.claude/hooks/skill-activation-hook.sh
   ```

## Keyword Best Practices

1. **Add variations**:
   - "bug", "bugs", "buggy"
   - "test", "testing", "tests"

2. **Include both languages**:
   - "requirement", "需求"
   - "error", "錯誤"

3. **Use common phrases**:
   - "客戶要" (customer wants)
   - "不work" (not working)

4. **Avoid too generic**:
   - ❌ "code", "write", "make"
   - ✅ "API", "endpoint", "route"

## Testing Keywords

```bash
# Test single keyword
echo "bug fix needed" | ./.claude/hooks/skill-activation-hook.sh

# Test Chinese
echo "客戶要新功能" | ./.claude/hooks/skill-activation-hook.sh

# Test multiple matches
echo "Add new API endpoint with tests" | ./.claude/hooks/skill-activation-hook.sh
```

## Activation Strategy

### keyword_matching (Default)
- Fast (<100ms)
- 75-80% success rate
- Targets specific skills

### forced_eval (Alternative)
- Same speed
- 84% success rate
- More verbose (evaluates ALL skills)

**To switch**: Edit `.claude/settings.json` hook command

## Troubleshooting

### Skill Not Activating

1. **Check keyword exists**:
   ```bash
   cat .claude/config/skill-rules.json | grep -A 5 "your-skill"
   ```

2. **Verify JSON syntax**:
   ```bash
   python3 -m json.tool .claude/config/skill-rules.json
   ```

3. **Test manually**:
   ```bash
   echo "your keyword" | ./.claude/hooks/skill-activation-hook.sh
   ```

### Too Many Skills Activating

Reduce keywords or lower priority:
```json
"priority": "medium"  // Instead of "high"
"force_activation": false  // Instead of true
```

### Skills Activating Too Late

Increase priority:
```json
"priority": "critical"
"force_activation": true
```

## Version History

- **v1.0** (2025-12-25) - Initial skill rules configuration

---

**See Also**: `.claude/hooks/README.md` for hook implementation details
