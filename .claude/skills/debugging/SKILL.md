---
name: debugging
version: 2.0
description: |
  Self-diagnostic debugging - Agent decides diagnostic approach.
  Auto-activates on "bug", "error", "debug", "不work", "壞掉" keywords.
  AMP principle: Think > Follow - Agent writes own debug tools.
allowed-tools: [Bash, Read, Grep, Edit, Write]
trigger_keywords:
  - bug
  - error
  - debug
  - 不work
  - 不 work
  - 壞掉
  - 錯誤
  - broken
  - failing
  - 失敗
auto_activate: true
priority: high
---

# Debugging - 自主诊断和修复

**Purpose**: 让 Agent 自己决定诊断方法，而非遵循固定步骤

**AMP Principle**: "告诉它「你想理解什么」，而非「怎么测试」"

---

## 核心思维

### ❌ 旧方式（固定步骤）
```
第1步: 运行测试
第2步: 检查日志
第3步: 添加 print
第4步: 重现错误
第5步: 修复
```

### ✅ 新方式（自主诊断）
```
问自己:
  - 我想理解什么？
  - 需要什么信息来诊断？
  - 最快的方法是什么？

然后:
  - 自己写诊断脚本
  - 执行并分析结果
  - 迭代直到找到根因
  - 用完删除临时工具
```

---

## 诊断模式示例

### Pattern 1: 写临时诊断脚本

**场景**: API 返回 500 错误

**不要**: 遵循固定步骤

**应该**:
```bash
# 自己写临时诊断脚本
cat > /tmp/debug_api.sh << 'EOF'
#!/bin/bash

# Create logs directory
mkdir -p logs
rm -f logs/*.log

# Run API with verbose logging
export DEBUG=true
export LOG_LEVEL=DEBUG

cd /Users/young/project/career_ios_backend
poetry run uvicorn app.main:app \
  --reload \
  --log-level debug \
  > logs/api.log 2>&1 &

API_PID=$!

# Wait for startup
sleep 2

# Test the failing endpoint
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name": "test"}' \
  -v > logs/curl.log 2>&1

# Analyze logs
echo "=== Errors ==="
grep -i "error\|exception" logs/api.log

echo "=== Response ==="
cat logs/curl.log

# Cleanup
kill $API_PID
EOF

chmod +x /tmp/debug_api.sh
/tmp/debug_api.sh

# 用完就删
rm /tmp/debug_api.sh
```

### Pattern 2: 动态添加日志

**场景**: 不确定哪里出错

**不要**: 预设添加日志的位置

**应该**:
```python
# TEMP: Add detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# 在怀疑的函数添加
def problematic_function(input_data):
    logger.debug(f"Input: {input_data}")
    logger.debug(f"Processing...")
    result = some_operation()
    logger.debug(f"Result: {result}")
    return result

# 运行、分析、然后移除日志
```

### Pattern 3: 数据库诊断

**场景**: 数据不一致

**不要**: 手动查询

**应该**:
```bash
# 写临时分析脚本
cat > /tmp/analyze_db.py << 'EOF'
from sqlalchemy import create_engine, text
import os
import sys

# Add project root to path
sys.path.insert(0, '/Users/young/project/career_ios_backend')

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

queries = {
    "orphaned_sessions": """
        SELECT s.id, s.name, s.client_id
        FROM sessions s
        LEFT JOIN clients c ON s.client_id = c.id
        WHERE c.id IS NULL
    """,
    "duplicate_codes": """
        SELECT client_code, COUNT(*)
        FROM clients
        GROUP BY client_code
        HAVING COUNT(*) > 1
    """,
    "invalid_timestamps": """
        SELECT * FROM sessions
        WHERE created_at > updated_at
    """
}

for name, query in queries.items():
    print(f"\n=== {name} ===")
    result = engine.execute(text(query))
    for row in result:
        print(row)
EOF

cd /Users/young/project/career_ios_backend
poetry run python /tmp/analyze_db.py
rm /tmp/analyze_db.py
```

---

## 诊断思维流程

```
遇到 Bug
  ↓
问: "我需要理解什么？"
  - 错误发生在哪一层？(API/Service/DB)
  - 输入数据是什么？
  - 预期 vs 实际输出？
  ↓
问: "最快的验证方法是什么？"
  - 写临时脚本？
  - 添加日志？
  - 直接测试 SQL？
  ↓
执行诊断
  - 不要担心代码质量
  - 不要过度工程化
  - 快速迭代
  ↓
找到根因
  ↓
修复
  ↓
清理临时工具
  - 删除临时脚本
  - 移除调试日志
  - 恢复正常代码
```

---

## 快速诊断工具箱

### 1. HTTP 请求诊断
```bash
# 详细查看 HTTP 交互
curl -v http://localhost:8000/api/endpoint

# 添加 timing 信息
curl -w "Time: %{time_total}s\n" http://localhost:8000/api/endpoint

# 保存响应详情
curl -v http://localhost:8000/api/endpoint > /tmp/response.log 2>&1
```

### 2. Python 交互式调试
```python
# 在怀疑的地方添加断点
import pdb; pdb.set_trace()

# 或使用 breakpoint() (Python 3.7+)
breakpoint()
```

### 3. 数据库实时查询
```bash
# PostgreSQL
cd /Users/young/project/career_ios_backend
poetry run python -c "
from app.core.config import settings
import psycopg2

conn = psycopg2.connect(settings.DATABASE_URL)
cur = conn.cursor()
cur.execute('SELECT * FROM sessions LIMIT 5')
print(cur.fetchall())
"
```

### 4. 日志实时监控
```bash
# 实时查看日志
tail -f /Users/young/project/career_ios_backend/logs/app.log | grep -i error

# 过滤特定关键词
tail -f /Users/young/project/career_ios_backend/logs/app.log | grep "session\|client"
```

---

## AMP 原则应用

**Graham 的例子**:
> "Agent 自己写了一整个 bash 脚本: 建立 logs 目录、每次执行前清空、设环境变数、把输出写入 log 档、用 grep 找出失败的地方。这个 script 不是人要求的，是 Agent 自己判断需要而产生的。"

**我们应该**:
- 让 Agent 自己决定需要什么工具
- 鼓励临时脚本和一次性工具
- 用完就删，不要保留
- 不要预设固定流程

---

## IMPORTANT

- **No Fixed Checklist** - 每个 bug 都不同
- **Think, Don't Follow** - 理解问题，自主决策
- **Temporary is OK** - 诊断脚本可以很丑
- **Clean Up After** - 修复后删除临时工具

---

**Version**: 2.0 (Self-Diagnostic refactor)
**Size**: ~230 lines
**Philosophy**: Think > Follow
