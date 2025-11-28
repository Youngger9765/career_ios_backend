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

# Core task patterns using regex for efficiency
TASK_PATTERNS = {
    # Development tasks (高優先)
    "development": r"(add|new|create|implement|build).*(feature|api|endpoint|field|功能|接口)",
    "chinese_dev": r"(新增|實作|開發|建立|創建)",
    # Career-specific (專案特定)
    "career_keywords": r"(session|consultation|client|case|counselor|諮詢|諮商|會談|案主|個案)",
    "career_features": r"(transcript|recording|reflection|report|逐字稿|錄音|心得|報告)",
    # Technical tasks (中優先)
    "bug_fix": r"(fix|bug|error|broken|issue|修復|錯誤|問題)",
    "testing": r"(test|pytest|verify|測試|驗證)",
    "database": r"(migration|schema|model.*change|資料庫|模型)",
    # Maintenance (低優先)
    "quality": r"(review|refactor|quality|審查|重構)",
    "deployment": r"(deploy|staging|production|部署)",
}

# Quick patterns for simple operations (不需要 agent-manager)
SIMPLE_PATTERNS = [
    r"^(what|how|where|explain|show|tell|describe)",  # 問題
    r"^(read|list|ls|pwd|whoami)",  # 簡單操作
    r"(什麼|哪裡|解釋|說明|查看|顯示)",  # 中文問題
]

# ========================================
# DETECTION LOGIC
# ========================================

# Check if it's a simple operation first (早期返回)
is_simple = any(re.search(pattern, user_prompt) for pattern in SIMPLE_PATTERNS)

# Check if it's a task requiring agent-manager
is_task = False
detected_pattern = None

if not is_simple:
    # Check task patterns with priority
    for pattern_name, pattern in TASK_PATTERNS.items():
        if re.search(pattern, user_prompt):
            is_task = True
            detected_pattern = pattern_name
            break

# ========================================
# OUTPUT GENERATION
# ========================================

# If it's a task, enforce agent-manager
if is_task:
    print(
        f"""
🎬 TASK [{detected_pattern}] → USE AGENT-MANAGER
   Action: Task(subagent_type="agent-manager", ...)
   """
    )

# If it's a simple operation, allow direct execution
elif is_simple:
    print("✅ Simple operation detected - can proceed directly without agent-manager")

# Default case - suggest using agent-manager for safety
else:
    print(
        """
💡 Task type unclear - Consider using agent-manager if this involves:
   - Code changes
   - New functionality
   - Bug fixes
   - Testing

   For simple queries, you may proceed directly.
"""
    )

sys.exit(0)
