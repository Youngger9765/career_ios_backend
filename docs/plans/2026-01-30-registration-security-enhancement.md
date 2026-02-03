# Registration Security Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Rate Limiting and Enhanced Password Strength validation to registration/login endpoints to prevent abuse and enforce strong passwords.

**Architecture:**
- Use `slowapi` for memory-based rate limiting (no Redis dependency)
- Add password complexity validation in Pydantic schema
- Environment-based rate limit thresholds (strict for production, lenient for development)
- All features are always-on (security baseline, no toggles)

**Tech Stack:**
- SlowAPI (rate limiting middleware)
- Pydantic validators (password strength)
- FastAPI exception handlers

---

## Task 1: Install Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add slowapi dependency**

Add to `[tool.poetry.dependencies]`:
```toml
slowapi = "^0.1.9"
```

**Step 2: Install dependencies**

Run: `poetry install`
Expected: slowapi installed successfully

**Step 3: Commit**

```bash
git add pyproject.toml poetry.lock
git commit -m "chore: add slowapi for rate limiting"
```

---

## Task 2: Add Rate Limiting Configuration

**Files:**
- Modify: `app/core/config.py:100-110`

**Step 1: Add rate limit settings to Settings class**

Add after line 99 (LOG_FILE):
```python
    # Rate Limiting (Always Enabled - Security Baseline)
    # Adjust values to control strictness, but cannot be fully disabled
    RATE_LIMIT_ENABLED: bool = True  # Always True, but allows testing override
    RATE_LIMIT_REGISTER_PER_HOUR: int = 100 if DEBUG else 3
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 20 if DEBUG else 5
    RATE_LIMIT_PASSWORD_RESET_PER_HOUR: int = 20 if DEBUG else 3
```

**Step 2: Commit**

```bash
git add app/core/config.py
git commit -m "config: add rate limiting settings"
```

---

## Task 3: Create Rate Limiting Middleware

**Files:**
- Create: `app/middleware/rate_limit.py`

**Step 1: Write test for rate limiter initialization**

Create `tests/unit/test_rate_limit.py`:
```python
"""
Unit tests for rate limiting middleware
"""
import pytest
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.middleware.rate_limit import limiter


def test_limiter_initialized():
    """Test that limiter is properly initialized"""
    assert limiter is not None
    assert isinstance(limiter, Limiter)
    assert limiter.key_func == get_remote_address
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/unit/test_rate_limit.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.middleware.rate_limit'"

**Step 3: Create rate limiting middleware**

Create `app/middleware/rate_limit.py`:
```python
"""
Rate limiting middleware using SlowAPI
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import Settings

settings = Settings()

# Initialize limiter with remote address as key
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # No default limits, apply per-route
    enabled=settings.RATE_LIMIT_ENABLED,
)
```

**Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/unit/test_rate_limit.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/middleware/rate_limit.py tests/unit/test_rate_limit.py
git commit -m "feat: add rate limiting middleware"
```

---

## Task 4: Apply Rate Limiting to Registration Endpoint

**Files:**
- Modify: `app/api/auth.py:33-42`
- Create: `tests/integration/test_rate_limit_auth.py`

**Step 1: Write failing test for registration rate limit**

Create `tests/integration/test_rate_limit_auth.py`:
```python
"""
Integration tests for rate limiting on auth endpoints
"""
import time
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app


class TestRateLimitAuth:
    """Test rate limiting on authentication endpoints"""

    def test_register_rate_limit_enforced(self, db_session: Session):
        """Test that registration is rate limited (3 per hour in production)"""
        with TestClient(app) as client:
            # First 3 attempts should succeed (or fail with duplicate, but not rate limit)
            for i in range(3):
                response = client.post(
                    "/api/auth/register",
                    json={
                        "email": f"test{i}@example.com",
                        "password": "SecurePass123!",
                        "tenant_id": "career",
                    },
                )
                # Should not be rate limited
                assert response.status_code in [201, 409]  # Created or Conflict (duplicate)

            # 4th attempt should be rate limited
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "test_limit@example.com",
                    "password": "SecurePass123!",
                    "tenant_id": "career",
                },
            )
            assert response.status_code == 429  # Too Many Requests
            assert "rate limit" in response.json()["detail"].lower()
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/integration/test_rate_limit_auth.py::TestRateLimitAuth::test_register_rate_limit_enforced -v`
Expected: FAIL with "AssertionError: assert 201 == 429" (4th request not rate limited)

**Step 3: Apply rate limiter to registration endpoint**

Modify `app/api/auth.py`:

Add import at top:
```python
from app.middleware.rate_limit import limiter
from app.core.config import Settings

settings = Settings()
```

Add rate limit decorator to register function (line 33):
```python
@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit(f"{settings.RATE_LIMIT_REGISTER_PER_HOUR}/hour")
def register(
    register_data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
```

**Step 4: Integrate limiter with FastAPI app**

Modify `app/main.py`:

Add imports:
```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.middleware.rate_limit import limiter
```

Add after `app = FastAPI(...)`:
```python
# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Step 5: Run test to verify it passes**

Run: `poetry run pytest tests/integration/test_rate_limit_auth.py::TestRateLimitAuth::test_register_rate_limit_enforced -v`
Expected: PASS

**Step 6: Commit**

```bash
git add app/api/auth.py app/main.py tests/integration/test_rate_limit_auth.py
git commit -m "feat: add rate limiting to registration endpoint"
```

---

## Task 5: Apply Rate Limiting to Login Endpoint

**Files:**
- Modify: `app/api/auth.py:119-127`
- Modify: `tests/integration/test_rate_limit_auth.py`

**Step 1: Write failing test for login rate limit**

Add to `tests/integration/test_rate_limit_auth.py`:
```python
    def test_login_rate_limit_enforced(self, db_session: Session):
        """Test that login is rate limited (5 per minute in production)"""
        from app.core.security import hash_password
        from app.models.counselor import Counselor

        # Create test counselor
        counselor = Counselor(
            id=uuid4(),
            email="logintest@example.com",
            username="logintest",
            full_name="Login Test",
            hashed_password=hash_password("password123"),
            tenant_id="career",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            # First 5 attempts should go through (might fail with wrong password, but not rate limit)
            for i in range(5):
                response = client.post(
                    "/api/auth/login",
                    json={
                        "email": "logintest@example.com",
                        "password": "password123",
                        "tenant_id": "career",
                    },
                )
                # Should not be rate limited
                assert response.status_code in [200, 401]  # Success or Unauthorized

            # 6th attempt should be rate limited
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "logintest@example.com",
                    "password": "password123",
                    "tenant_id": "career",
                },
            )
            assert response.status_code == 429  # Too Many Requests
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/integration/test_rate_limit_auth.py::TestRateLimitAuth::test_login_rate_limit_enforced -v`
Expected: FAIL with "AssertionError: assert 200 == 429"

**Step 3: Apply rate limiter to login endpoint**

Modify `app/api/auth.py`, add decorator to login function (line 119):
```python
@router.post("/login", response_model=TokenResponse)
@limiter.limit(f"{settings.RATE_LIMIT_LOGIN_PER_MINUTE}/minute")
def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
```

**Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/integration/test_rate_limit_auth.py::TestRateLimitAuth::test_login_rate_limit_enforced -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/api/auth.py tests/integration/test_rate_limit_auth.py
git commit -m "feat: add rate limiting to login endpoint"
```

---

## Task 6: Apply Rate Limiting to Password Reset Endpoint

**Files:**
- Modify: `app/api/v1/password_reset.py`
- Modify: `tests/integration/test_rate_limit_auth.py`

**Step 1: Write failing test for password reset rate limit**

Add to `tests/integration/test_rate_limit_auth.py`:
```python
    def test_password_reset_rate_limit_enforced(self, db_session: Session):
        """Test that password reset is rate limited (3 per hour in production)"""
        from app.core.security import hash_password
        from app.models.counselor import Counselor

        # Create test counselor
        counselor = Counselor(
            id=uuid4(),
            email="resettest@example.com",
            username="resettest",
            full_name="Reset Test",
            hashed_password=hash_password("password123"),
            tenant_id="island_parents",
            role="counselor",
            is_active=True,
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            # First 3 attempts should go through
            for i in range(3):
                response = client.post(
                    "/api/v1/auth/password-reset/request",
                    json={
                        "email": "resettest@example.com",
                        "tenant_id": "island_parents",
                    },
                )
                assert response.status_code == 200

            # 4th attempt should be rate limited
            response = client.post(
                "/api/v1/auth/password-reset/request",
                json={
                    "email": "resettest@example.com",
                    "tenant_id": "island_parents",
                },
            )
            assert response.status_code == 429
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/integration/test_rate_limit_auth.py::TestRateLimitAuth::test_password_reset_rate_limit_enforced -v`
Expected: FAIL

**Step 3: Apply rate limiter to password reset endpoint**

Modify `app/api/v1/password_reset.py`:

Add imports:
```python
from app.middleware.rate_limit import limiter
from app.core.config import Settings

settings = Settings()
```

Find `request_password_reset` function and add decorator:
```python
@router.post("/password-reset/request", response_model=PasswordResetResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PASSWORD_RESET_PER_HOUR}/hour")
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
```

**Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/integration/test_rate_limit_auth.py::TestRateLimitAuth::test_password_reset_rate_limit_enforced -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/api/v1/password_reset.py tests/integration/test_rate_limit_auth.py
git commit -m "feat: add rate limiting to password reset endpoint"
```

---

## Task 7: Add Password Strength Validation

**Files:**
- Create: `app/core/password_validator.py`
- Create: `tests/unit/test_password_validator.py`

**Step 1: Write failing tests for password validation**

Create `tests/unit/test_password_validator.py`:
```python
"""
Unit tests for password strength validation
"""
import pytest

from app.core.password_validator import validate_password_strength


class TestPasswordValidator:
    """Test password strength validation"""

    def test_valid_strong_password(self):
        """Test that a strong password passes validation"""
        password = "SecurePass123!"
        # Should not raise exception
        validate_password_strength(password)

    def test_password_too_short(self):
        """Test that password shorter than 12 chars fails"""
        password = "Short1!"
        with pytest.raises(ValueError, match="at least 12 characters"):
            validate_password_strength(password)

    def test_password_no_uppercase(self):
        """Test that password without uppercase fails"""
        password = "securepass123!"
        with pytest.raises(ValueError, match="uppercase letter"):
            validate_password_strength(password)

    def test_password_no_lowercase(self):
        """Test that password without lowercase fails"""
        password = "SECUREPASS123!"
        with pytest.raises(ValueError, match="lowercase letter"):
            validate_password_strength(password)

    def test_password_no_digit(self):
        """Test that password without digit fails"""
        password = "SecurePassword!"
        with pytest.raises(ValueError, match="digit"):
            validate_password_strength(password)

    def test_password_no_special_char(self):
        """Test that password without special char fails"""
        password = "SecurePass123"
        with pytest.raises(ValueError, match="special character"):
            validate_password_strength(password)

    def test_common_password_rejected(self):
        """Test that common passwords are rejected"""
        password = "Password123!"
        with pytest.raises(ValueError, match="too common"):
            validate_password_strength(password)
```

**Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/unit/test_password_validator.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement password validator**

Create `app/core/password_validator.py`:
```python
"""
Password strength validation
"""
import re


# List of common passwords to reject
COMMON_PASSWORDS = {
    "password",
    "password123",
    "12345678",
    "qwerty",
    "abc123",
    "monkey",
    "letmein",
    "trustno1",
    "dragon",
    "baseball",
    "iloveyou",
    "master",
    "sunshine",
    "ashley",
    "bailey",
    "shadow",
    "superman",
    "qazwsx",
}


def validate_password_strength(password: str) -> None:
    """
    Validate password strength according to security policy

    Requirements:
    - At least 12 characters
    - Contains uppercase letter
    - Contains lowercase letter
    - Contains digit
    - Contains special character
    - Not a common password

    Args:
        password: Password to validate

    Raises:
        ValueError: If password doesn't meet requirements
    """
    # Check length
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")

    # Check for uppercase
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")

    # Check for lowercase
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")

    # Check for digit
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")

    # Check for special character
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};:'\",.<>?/\\|`~]", password):
        raise ValueError("Password must contain at least one special character")

    # Check against common passwords (case-insensitive)
    if password.lower() in COMMON_PASSWORDS:
        raise ValueError("Password is too common, please choose a stronger password")
```

**Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_password_validator.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/core/password_validator.py tests/unit/test_password_validator.py
git commit -m "feat: add password strength validator"
```

---

## Task 8: Integrate Password Validation into Registration Schema

**Files:**
- Modify: `app/schemas/auth.py:21-29`
- Modify: `tests/integration/test_auth_api.py`

**Step 1: Write failing test for registration with weak password**

Add to `tests/integration/test_auth_api.py`:
```python
    def test_register_weak_password_rejected(self, db_session: Session):
        """Test that registration with weak password is rejected"""
        with TestClient(app) as client:
            # Too short
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "weak@example.com",
                    "password": "Short1!",
                    "tenant_id": "career",
                },
            )
            assert response.status_code == 422
            assert "at least 12 characters" in response.json()["detail"][0]["msg"]

            # No uppercase
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "weak2@example.com",
                    "password": "securepass123!",
                    "tenant_id": "career",
                },
            )
            assert response.status_code == 422
            assert "uppercase" in response.json()["detail"][0]["msg"]
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/integration/test_auth_api.py::TestAuthAPI::test_register_weak_password_rejected -v`
Expected: FAIL (weak passwords not rejected)

**Step 3: Add password validation to RegisterRequest**

Modify `app/schemas/auth.py`:

Add import:
```python
from pydantic import field_validator

from app.core.password_validator import validate_password_strength
```

Modify `RegisterRequest` class:
```python
class RegisterRequest(BaseModel):
    """Registration request - simplified to only require email and password"""

    email: EmailStr
    password: str = Field(..., min_length=12)  # Changed from 8 to 12
    tenant_id: str
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, min_length=1)
    role: CounselorRole = CounselorRole.COUNSELOR

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        validate_password_strength(v)
        return v
```

**Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/integration/test_auth_api.py::TestAuthAPI::test_register_weak_password_rejected -v`
Expected: PASS

**Step 5: Update existing tests to use strong passwords**

Modify all test files that create users with weak passwords:
- `tests/integration/test_auth_api.py`: Change all `"password123"` to `"SecurePass123!"`
- Update any other integration tests

Run all integration tests:
```bash
poetry run pytest tests/integration/test_auth_api.py -v
```
Expected: All tests PASS

**Step 6: Commit**

```bash
git add app/schemas/auth.py tests/integration/test_auth_api.py
git commit -m "feat: enforce strong password requirements in registration"
```

---

## Task 9: Update Documentation

**Files:**
- Modify: `TODO.md`
- Modify: `CHANGELOG.md`
- Create: `docs/SECURITY.md` (optional)

**Step 1: Mark tasks as completed in TODO.md**

Update `TODO.md`:
```markdown
### 註冊安全性增強（2026-01-30）✅ 完成

- [x] **Rate Limiting**（永久啟用）✅ 已實作
  - 註冊限制：同 IP 每小時最多 3 次（開發環境：100 次）
  - 登入限制：同 IP 每分鐘最多 5 次（開發環境：20 次）
  - 忘記密碼限制：同 IP 每小時最多 3 次（開發環境：20 次）
  - 使用 slowapi memory-based 實作

- [x] **密碼強度驗證增強**（永久啟用）✅ 已實作
  - 至少 12 字元
  - 必須包含大小寫 + 數字 + 特殊字元
  - 檢查常見密碼清單

- [ ] **郵件驗證功能**（可開關設計）⏳ 待 PM 確認
```

**Step 2: Update CHANGELOG.md**

Add to `CHANGELOG.md`:
```markdown
## [Unreleased]

### Added
- **Rate Limiting** on authentication endpoints
  - Registration: 3 requests/hour (100 in dev)
  - Login: 5 requests/minute (20 in dev)
  - Password reset: 3 requests/hour (20 in dev)
  - Implementation: slowapi memory-based
- **Enhanced Password Strength Validation**
  - Minimum 12 characters (increased from 8)
  - Requires uppercase, lowercase, digit, special character
  - Rejects common passwords

### Changed
- Registration password requirements strengthened from 8 to 12 characters
- All authentication endpoints now protected by rate limiting
```

**Step 3: Commit**

```bash
git add TODO.md CHANGELOG.md
git commit -m "docs: update TODO and CHANGELOG for security enhancements"
```

---

## Task 10: Deployment Verification

**Files:**
- None (testing only)

**Step 1: Run full integration test suite**

```bash
poetry run pytest tests/integration/ -v
```
Expected: All tests PASS

**Step 2: Run unit test suite**

```bash
poetry run pytest tests/unit/ -v
```
Expected: All tests PASS

**Step 3: Verify configuration in different environments**

Check `.env` for development:
```bash
grep RATE_LIMIT .env
```
Expected: No RATE_LIMIT settings (uses defaults)

Check `.env.production.example`:
```bash
grep RATE_LIMIT .env.production.example
```
Expected: Production rate limits documented

**Step 4: Manual testing (optional)**

Start development server:
```bash
poetry run uvicorn app.main:app --reload
```

Test endpoints:
1. Register 4 times quickly → 4th should fail with 429
2. Login 6 times quickly → 6th should fail with 429
3. Try weak password → Should fail with 422

**Step 5: Create summary report**

Document:
- All tests passing
- Rate limits verified in dev/prod
- Password validation working
- No breaking changes to existing functionality

---

## Verification Checklist

Before marking complete:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Rate limiting works on registration endpoint
- [ ] Rate limiting works on login endpoint
- [ ] Rate limiting works on password reset endpoint
- [ ] Weak passwords rejected during registration
- [ ] Strong passwords accepted during registration
- [ ] Documentation updated (TODO, CHANGELOG)
- [ ] No breaking changes to existing tests
- [ ] Development environment has lenient limits
- [ ] Production environment has strict limits

---

## Rollback Plan

If issues arise:
```bash
git log --oneline | head -10  # Find commits
git revert <commit-sha>       # Revert specific commit
```

Or complete rollback:
```bash
git reset --hard HEAD~10      # Go back 10 commits
```

---

## Notes

**Design Decisions:**
- Rate limiting is always-on (security baseline)
- No environment variable to disable (prevents misconfiguration)
- Development has lenient limits (doesn't block development)
- Password validation is always-on (security baseline)
- Uses slowapi memory-based (no Redis dependency, simpler deployment)

**Future Enhancements:**
- Add Redis backend for distributed rate limiting (multi-instance deployments)
- Add email verification (requires PM approval)
- Add IP whitelist for trusted sources
- Add admin endpoint to reset rate limits
