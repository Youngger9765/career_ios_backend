#!/bin/bash
# Test script for Skill Auto-Activation System
# Run this to verify the hooks are working correctly

echo "=============================================="
echo "Skill Auto-Activation System - Test Suite"
echo "=============================================="
echo ""

HOOK_SCRIPT="./.claude/hooks/skill-activation-hook.sh"

if [ ! -f "$HOOK_SCRIPT" ]; then
    echo "❌ ERROR: Hook script not found at $HOOK_SCRIPT"
    exit 1
fi

if [ ! -x "$HOOK_SCRIPT" ]; then
    echo "❌ ERROR: Hook script is not executable"
    echo "Run: chmod +x $HOOK_SCRIPT"
    exit 1
fi

# Test cases
test_case() {
    local name="$1"
    local prompt="$2"
    local expected_skill="$3"

    echo "Test: $name"
    echo "Input: \"$prompt\""

    result=$(echo "$prompt" | $HOOK_SCRIPT)

    if echo "$result" | grep -q "Skill(skill=\"$expected_skill\")"; then
        echo "✅ PASS - Skill '$expected_skill' activated"
    else
        echo "❌ FAIL - Skill '$expected_skill' NOT activated"
        echo "Output preview:"
        echo "$result" | head -n 5
    fi
    echo ""
}

echo "Running test cases..."
echo ""

# Test 1: Requirements clarification
test_case \
    "Requirements Clarification" \
    "客戶要一個新功能但需求不清楚" \
    "requirements-clarification"

# Test 2: TDD workflow
test_case \
    "TDD Workflow" \
    "implement new API endpoint for search" \
    "tdd-workflow"

# Test 3: Debugging
test_case \
    "Debugging" \
    "there's a bug in the authentication" \
    "debugging"

# Test 4: Git workflow
test_case \
    "Git Workflow" \
    "need to commit and push changes" \
    "git-workflow"

# Test 5: API development
test_case \
    "API Development" \
    "create new FastAPI route" \
    "api-development"

# Test 6: PRD workflow
test_case \
    "PRD Workflow" \
    "update PRD with new feature spec" \
    "prd-workflow"

# Test 7: No activation (should pass through)
echo "Test: No Activation (Pass-Through)"
echo "Input: \"What is Python?\""
result=$(echo "What is Python?" | $HOOK_SCRIPT)
if echo "$result" | grep -q "Skill("; then
    echo "❌ FAIL - Skills activated when they shouldn't"
else
    echo "✅ PASS - No skills activated (correct)"
fi
echo ""

echo "=============================================="
echo "Test Suite Complete"
echo "=============================================="
echo ""
echo "To test manually:"
echo "  echo 'your prompt' | $HOOK_SCRIPT"
echo ""
echo "To see all configured skills:"
echo "  cat .claude/config/skill-rules.json | python3 -m json.tool"
echo ""
