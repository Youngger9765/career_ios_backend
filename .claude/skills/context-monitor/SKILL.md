# Context Usage Monitor

## Purpose
Monitor and warn about context usage to prevent context exhaustion.

## Usage Thresholds
- **30k tokens**: First warning (Yellow)
- **50k tokens**: Strong warning (Orange)
- **70k tokens**: Critical warning (Red) - Consider /clear

## Monitoring Points
1. After each agent invocation
2. Before complex tasks
3. When reading large files

## Warning Messages

### Yellow (30k)
```
⚠️ Context Usage: ~30k tokens
Consider focusing on current task only.
```

### Orange (50k)
```
🟠 Context Usage: ~50k tokens
Recommend completing current task then /clear.
```

### Red (70k+)
```
🔴 Context Usage: 70k+ tokens
CRITICAL: Use /clear soon to prevent errors.
Save important context before clearing.
```

## Best Practices
1. Use subagents to preserve main context
2. Clear context between major features
3. Avoid reading unnecessary large files
4. Use Task tool for complex searches

## Context-Saving Commands
Before /clear, save important info:
```bash
# Save current branch and status
git status > /tmp/context_save.txt
git diff --staged >> /tmp/context_save.txt

# After /clear, restore context:
cat /tmp/context_save.txt
```
