#!/usr/bin/env python3
"""
Career iOS Backend - Agent Manager Enforcement Hook
Ensures all coding tasks go through agent-manager for TDD compliance
"""
import json
import re
import sys

# Load user prompt from stdin
try:
    input_data = json.load(sys.stdin)
    user_prompt = input_data.get("prompt", "").lower()
except (json.JSONDecodeError, AttributeError):
    # If no JSON input, just exit
    sys.exit(0)

# ========================================
# TASK DETECTION PATTERNS
# ========================================

# Core task patterns - ANY of these REQUIRE agent-manager
CODING_TASK_PATTERNS = {
    # Development tasks (MANDATORY)
    "development": r"(add|new|create|implement|build|write|develop|code)",
    "chinese_dev": r"(新增|實作|開發|建立|創建|撰寫|編寫|處理)",
    # Bug fixes and changes (MANDATORY)
    "bug_fix": r"(fix|bug|error|broken|issue|修復|錯誤|問題|修正|解決)",
    "modification": r"(change|modify|update|edit|refactor|改變|修改|更新|編輯|重構)",
    # Testing (MANDATORY)
    "testing": r"(test|pytest|verify|測試|驗證|檢查)",
    # Database operations (MANDATORY)
    "database": r"(migration|schema|model|database|資料庫|模型|遷移)",
    # Deployment (MANDATORY)
    "deployment": r"(deploy|staging|production|release|部署|發布|上線)",
    # Career-specific features (MANDATORY)
    "career": r"(session|consultation|transcript|recording|諮詢|諮詢|會談|逐字稿|錄音)",
    # Code review and optimization (MANDATORY)
    "optimization": r"(optimize|improve|enhance|review|優化|改善|提升|審查)",
}

# Simple questions that DON'T need agent-manager
SIMPLE_PATTERNS = [
    r"^(what|how|where|when|why|explain|show|tell|describe|list)",
    r"^(read|view|check|look|see|find|search|grep)",
    r"(什麼|哪裡|為什麼|解釋|說明|查看|顯示|列出)",
    r"^(ls|pwd|cat|echo|grep|find)($|\s)",  # Shell commands for viewing
]

# ========================================
# DETECTION LOGIC
# ========================================

# Check if it's a simple operation first
is_simple = any(re.search(pattern, user_prompt) for pattern in SIMPLE_PATTERNS)

# Check if it's a coding task requiring agent-manager
is_coding_task = False
detected_pattern = None

if not is_simple:
    for pattern_name, pattern in CODING_TASK_PATTERNS.items():
        if re.search(pattern, user_prompt):
            is_coding_task = True
            detected_pattern = pattern_name
            break

# ========================================
# OUTPUT GENERATION
# ========================================

# MANDATORY enforcement for coding tasks
if is_coding_task:
    print(
        f"""
🚨 CRITICAL: CODING TASK DETECTED [{detected_pattern.upper()}]
╔═══════════════════════════════════════════════════════════════╗
║  ⛔ FORBIDDEN: Direct use of Edit/Write/Bash for coding       ║
║  ✅ MANDATORY: Use Task(subagent_type="general-purpose", ...) ║
╚═══════════════════════════════════════════════════════════════╝

🎯 YOU MUST execute:
   Task(
       subagent_type="general-purpose",
       prompt="[Your coding task here]",
       description="[Brief description]"
   )

⚠️  VIOLATION of this rule = PROJECT STANDARDS BREACH
"""
    )

# Simple operations can proceed
elif is_simple:
    print("✅ Simple question detected - proceed with direct answer")

# Ambiguous cases - STRONG recommendation
else:
    print(
        """
💡 Task type unclear - Consider using agent-manager if this involves:
   - Code changes
   - New functionality
   - Bug fixes
   - Testing

   For simple queries, you may proceed directly."""
    )

sys.exit(0)
