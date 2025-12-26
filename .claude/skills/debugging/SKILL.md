---
name: debugging
description: |
  Debug issues in career_ios_backend FastAPI application.
  Auto-activates on "bug", "error", "debug", "不work", "壞掉", "失敗" keywords.
  Provides systematic debugging workflow for API, database, and integration issues.
allowed-tools: [Bash, Read, Grep, Edit]
---

# Debugging Skill

## Purpose
Systematic debugging workflow for career_ios_backend API issues.

## Auto-Activation

Triggers on:
- ✅ "bug", "error", "debug"
- ✅ "不 work", "壞掉", "失敗"
- ✅ "API 失敗", "測試失敗"

---

## Quick Debug Workflow

**Copy this checklist**:
```
Debugging Progress:
- [ ] Step 1: Reproduce the issue
- [ ] Step 2: Check logs and error messages
- [ ] Step 3: Identify root cause
- [ ] Step 4: Fix and verify
- [ ] Step 5: Add test to prevent regression
```

---

## Step 1: Reproduce the Issue

### API Issues

```bash
# Test the failing endpoint
poetry run pytest tests/integration/test_<feature>_api.py -v -k "test_name"

# Or manual test with httpx
python -c "
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        response = await client.get('/api/v1/endpoint')
        print(f'Status: {response.status_code}')
        print(f'Body: {response.json()}')

asyncio.run(test())
"
```

### Database Issues

```bash
# Check database state
poetry run python -c "
from app.db.session import SessionLocal
from app.models.user import User

db = SessionLocal()
users = db.query(User).all()
print(f'Users count: {len(users)}')
db.close()
"
```

---

## Step 2: Check Logs and Errors

### Read Application Logs

```bash
# Check recent logs
tail -100 logs/app.log

# Search for errors
grep -i "error\|exception\|traceback" logs/app.log | tail -20

# Filter by specific endpoint
grep "/api/v1/clients" logs/app.log | tail -10
```

### FastAPI Development Server

```bash
# Run with verbose logging
poetry run uvicorn app.main:app --reload --log-level debug
```

### Test Output

```bash
# Run tests with full output
poetry run pytest tests/integration/ -v -s

# Show print statements
poetry run pytest tests/integration/test_clients_api.py -v -s -k "test_name"
```

---

## Step 3: Identify Root Cause

### Common Issue Patterns

**Authentication Issues**:
```python
# Check token validity
import jwt
from app.core.config import settings

token = "your_token_here"
try:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    print(f"Valid token for user: {payload['sub']}")
except jwt.ExpiredSignatureError:
    print("Token expired")
except jwt.InvalidTokenError:
    print("Invalid token")
```

**Database Connection Issues**:
```bash
# Test database connection
poetry run python -c "
from app.db.session import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connected:', result.fetchone())
"
```

**Import/Dependency Issues**:
```bash
# Check installed packages
poetry show | grep -i "package_name"

# Verify imports work
poetry run python -c "
try:
    from app.api.clients import router
    print('Import successful')
except ImportError as e:
    print(f'Import error: {e}')
"
```

---

## Step 4: Fix and Verify

### Fix the Code

1. **Read the relevant file**:
   ```bash
   # Find the file
   find app/ -name "*clients*" -type f
   ```

2. **Apply fix** using Edit tool

3. **Verify fix locally**:
   ```bash
   # Re-run failing test
   poetry run pytest tests/integration/test_<feature>_api.py -v
   ```

### Validation Checklist

- [ ] Test passes locally
- [ ] No new errors in logs
- [ ] Code follows existing patterns
- [ ] No hardcoded values

---

## Step 5: Prevent Regression

**Add test if missing**:

```python
# tests/integration/test_<feature>_api.py

@pytest.mark.asyncio
async def test_bug_fix_<issue_description>():
    """
    Test for bug: <describe the issue>

    Previously failed because: <root cause>
    Fixed by: <solution>
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/endpoint",
            headers=auth_headers
        )

    assert response.status_code == 200
    # Add specific assertion that would catch the bug
```

---

## Common Debug Scenarios

### Scenario 1: API Returns 500 Error

```bash
# 1. Check server logs
tail -50 logs/app.log | grep -i "error"

# 2. Run with debugger
poetry run pytest tests/integration/test_api.py -v -s --pdb

# 3. Check database state
poetry run python scripts/check_db.py
```

### Scenario 2: Test Fails Randomly

```bash
# Run test multiple times
for i in {1..10}; do
    echo "Run $i:"
    poetry run pytest tests/integration/test_api.py -v -k "test_name"
done

# Check for async/race conditions
# Check for database cleanup issues
```

### Scenario 3: Import Error

```bash
# Check Python path
poetry run python -c "import sys; print('\n'.join(sys.path))"

# Verify package installation
poetry install

# Check for circular imports
poetry run python -c "import app.main"
```

### Scenario 4: Database Query Fails

```bash
# Enable SQL logging
export SQLALCHEMY_ECHO=1
poetry run pytest tests/integration/test_db.py -v -s

# Check database schema
poetry run python -c "
from app.db.base import Base
from app.db.session import engine

Base.metadata.create_all(bind=engine)
print('Tables:', engine.table_names())
"
```

---

## Debug Tools

### Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()

# Run test with debugger
poetry run pytest --pdb
```

### Print Debugging

```python
# Strategic print statements
print(f"DEBUG: variable = {variable}")
print(f"DEBUG: type = {type(variable)}")
print(f"DEBUG: dir = {dir(variable)}")

# Pretty print
import pprint
pprint.pprint(complex_object)
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug info")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)
```

---

## When Stuck

1. **Search codebase for similar patterns**:
   ```bash
   grep -r "similar_function_name" app/
   ```

2. **Check existing tests**:
   ```bash
   grep -r "test_similar_feature" tests/
   ```

3. **Review recent changes**:
   ```bash
   git log --oneline -10
   git diff HEAD~5
   ```

4. **Ask for clarification**:
   - What was the expected behavior?
   - What actually happened?
   - Can you reproduce it manually?

---

## Related Skills

- **api-development**: API patterns and testing
- **tdd-workflow**: Test-first development
- **error-handling**: Proper error handling patterns

---

**Skill Version**: v1.0
**Last Updated**: 2025-12-25
**Project**: career_ios_backend (Prototype Phase)
