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

# Task keywords that REQUIRE agent-manager
task_keywords = [
    # Feature Development
    "add feature",
    "new feature",
    "implement",
    "create api",
    "new endpoint",
    "add field",
    "新增",
    "實作",
    "開發",
    # Session/Consultation Related (Career iOS Backend specific)
    "session",
    "諮詢",
    "諮商",
    "會談",
    "consultation",
    "recording",
    "transcript",
    "逐字稿",
    "reflection",
    "心得",
    "append recording",
    "錄音",
    "timeline",
    # Client/Case Management (Career iOS Backend specific)
    "client",
    "案主",
    "個案",
    "case management",
    "counselor",
    "諮商師",
    "client code",
    "案主代碼",
    "identity_option",
    "current_status",
    # Report Generation
    "report",
    "報告",
    "generate",
    "生成",
    # RAG/AI Features (Career iOS Backend specific)
    "rag",
    "embedding",
    "vector",
    "search",
    "嵌入",
    "gemini",
    "vertex ai",
    "keyword analysis",
    "關鍵字分析",
    "transcript keywords",
    "逐字稿關鍵字",
    # Bug Fixes
    "bug",
    "error",
    "broken",
    "not working",
    "issue",
    "fix",
    "錯誤",
    "修復",
    "問題",
    # Testing
    "test",
    "pytest",
    "測試",
    "verify",
    "check",
    # Database Changes
    "migration",
    "alembic",
    "schema",
    "model change",
    "資料庫",
    # Code Quality
    "review",
    "refactor",
    "quality",
    "審查",
    "重構",
    # API Operations
    "api",
    "endpoint",
    "route",
    "get",
    "post",
    "put",
    "delete",
    "patch",
    # Deployment
    "deploy",
    "push",
    "staging",
    "production",
    "部署",
    # Git Operations
    "commit",
    "git",
    "pr",
    "pull request",
]

# Simple operations that DON'T need agent-manager
simple_operations = [
    # Questions
    "what is",
    "what's",
    "how does",
    "where is",
    "where's",
    "explain",
    "show me",
    "tell me",
    "describe",
    "什麼是",
    "在哪裡",
    "解釋",
    "說明",
    # Simple file operations
    "read file",
    "show file",
    "list files",
    "ls",
    "查看",
    "顯示",
    "列出",
    # Information queries
    "current branch",
    "git status",
    "pwd",
    "whoami",
]

# TDD-specific patterns
tdd_patterns = [
    r"add.*field",  # Adding new fields
    r"create.*api",  # Creating new APIs
    r"new.*endpoint",  # New endpoints
    r"implement.*feature",  # Feature implementation
]

# ========================================
# DETECTION LOGIC
# ========================================

# Check if it's a task requiring agent-manager
is_task = False

# Check direct keyword match
for keyword in task_keywords:
    if keyword in user_prompt:
        is_task = True
        break

# Check regex patterns if not found
if not is_task:
    for pattern in tdd_patterns:
        if re.search(pattern, user_prompt):
            is_task = True
            break

# Check if it's a simple operation
is_simple = any(op in user_prompt for op in simple_operations)

# Special case: "Session name/title field" detection
if "session" in user_prompt and ("name" in user_prompt or "title" in user_prompt):
    is_task = True
    is_simple = False

# ========================================
# OUTPUT GENERATION
# ========================================

# If it's a task and not simple, enforce agent-manager
if is_task and not is_simple:
    detected_keywords = [kw for kw in task_keywords if kw in user_prompt][
        :3
    ]  # 只顯示前3個
    print(
        f"""
🎬 TASK DETECTED → USE AGENT-MANAGER
   Keywords: {detected_keywords}
   Action: Task(subagent_type="agent-manager", description="...", prompt="...")
   """
    )

    # Special TDD reminder for feature additions
    if any(
        kw in user_prompt for kw in ["add feature", "new api", "implement", "create"]
    ):
        print(
            """
🧪 TDD REMINDER: Tests MUST be written FIRST!
   The agent-manager will ensure test-first development.
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
