# Password Reset - Verification Code Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace token-based password reset with 6-digit verification code system

**Architecture:** Generate 6-digit code instead of 32-byte token, send via email, verify code with lockout mechanism, then allow password update. Completely replaces existing token-based flow.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Alembic, Gmail SMTP

**Security Specs:**
- Code Length: 6 digits (000000-999999)
- Expiry: 15 minutes
- Max Attempts: 5 (then lockout)
- Lockout Duration: 15 minutes
- Resend Cooldown: 60 seconds

---

## Task 1: Database Migration

**Files:**
- Create: `alembic/versions/2026_01_31_add_verification_code_fields.py`

**Step 1: Generate migration file**

Run:
```bash
alembic revision -m "add verification code fields to password_reset_tokens"
```

Expected: Creates new migration file in `alembic/versions/`

**Step 2: Write migration upgrade**

```python
def upgrade() -> None:
    # Add new columns for verification code system
    op.add_column('password_reset_tokens', sa.Column('verification_code', sa.String(length=6), nullable=True))
    op.add_column('password_reset_tokens', sa.Column('verify_attempts', sa.Integer(), server_default='0', nullable=False))
    op.add_column('password_reset_tokens', sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column('password_reset_tokens', sa.Column('code_expires_at', sa.DateTime(timezone=True), nullable=True))

    # Add index on verification_code for faster lookups
    op.create_index('ix_password_reset_tokens_verification_code', 'password_reset_tokens', ['verification_code'])
```

**Step 3: Write migration downgrade**

```python
def downgrade() -> None:
    op.drop_index('ix_password_reset_tokens_verification_code', table_name='password_reset_tokens')
    op.drop_column('password_reset_tokens', 'code_expires_at')
    op.drop_column('password_reset_tokens', 'locked_until')
    op.drop_column('password_reset_tokens', 'verify_attempts')
    op.drop_column('password_reset_tokens', 'verification_code')
```

**Step 4: Run migration**

Run:
```bash
alembic upgrade head
```

Expected: "Running upgrade ... -> ..., add verification code fields to password_reset_tokens"

**Step 5: Commit**

```bash
git add alembic/versions/2026_01_31_*.py
git commit -m "feat: add verification code fields to password_reset_tokens table"
```

---

## Task 2: Update Model

**Files:**
- Modify: `app/models/password_reset.py`

**Step 1: Add new fields to PasswordResetToken model**

Add after line with `used_at` field:

```python
    # Verification code fields (new system)
    verification_code = Column(String(6), index=True, nullable=True)
    verify_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    code_expires_at = Column(DateTime(timezone=True), nullable=True)
```

**Step 2: Verify model loads correctly**

Run:
```bash
python -c "from app.models.password_reset import PasswordResetToken; print('Model OK')"
```

Expected: "Model OK"

**Step 3: Commit**

```bash
git add app/models/password_reset.py
git commit -m "feat: add verification code fields to PasswordResetToken model"
```

---

## Task 3: Add Configuration Constants

**Files:**
- Modify: `app/core/config.py`

**Step 1: Add verification code constants**

Add to the Config class:

```python
    # Verification Code Settings
    VERIFICATION_CODE_LENGTH: int = 6
    VERIFICATION_CODE_EXPIRY_MINUTES: int = 15
    VERIFICATION_CODE_MAX_ATTEMPTS: int = 5
    VERIFICATION_CODE_LOCKOUT_MINUTES: int = 15
    VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS: int = 60
```

**Step 2: Verify config loads**

Run:
```bash
python -c "from app.core.config import settings; print(f'Code length: {settings.VERIFICATION_CODE_LENGTH}')"
```

Expected: "Code length: 6"

**Step 3: Commit**

```bash
git add app/core/config.py
git commit -m "feat: add verification code configuration constants"
```

---

## Task 4: Update Schemas

**Files:**
- Modify: `app/schemas/auth.py`

**Step 1: Add VerifyCodeRequest schema**

Add after PasswordResetConfirm schema:

```python
class VerifyCodeRequest(BaseModel):
    """Request to verify a password reset code"""
    email: str = Field(..., description="User's email address")
    verification_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")
    tenant_id: str = Field(default="career", description="Tenant identifier")

    @validator('verification_code')
    def validate_code_format(cls, v):
        if not v.isdigit():
            raise ValueError("Verification code must contain only digits")
        if len(v) != 6:
            raise ValueError("Verification code must be exactly 6 digits")
        return v
```

**Step 2: Update PasswordResetConfirm schema**

Replace existing PasswordResetConfirm with:

```python
class PasswordResetConfirm(BaseModel):
    """Request to confirm password reset with verification code"""
    email: str = Field(..., description="User's email address")
    verification_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")
    tenant_id: str = Field(default="career", description="Tenant identifier")

    @validator('verification_code')
    def validate_code_format(cls, v):
        if not v.isdigit():
            raise ValueError("Verification code must contain only digits")
        if len(v) != 6:
            raise ValueError("Verification code must be exactly 6 digits")
        return v
```

**Step 3: Add response schemas**

Add:

```python
class VerifyCodeResponse(BaseModel):
    """Response after verifying code"""
    success: bool
    message: str = "Verification code is valid"


class PasswordResetConfirmResponse(BaseModel):
    """Response after password reset"""
    success: bool
    message: str = "Password has been reset successfully"
```

**Step 4: Verify schemas work**

Run:
```bash
python -c "from app.schemas.auth import VerifyCodeRequest; print('Schemas OK')"
```

Expected: "Schemas OK"

**Step 5: Commit**

```bash
git add app/schemas/auth.py
git commit -m "feat: add verification code request/response schemas"
```

---

## Task 5: Update Email Service

**Files:**
- Modify: `app/services/external/email_sender.py`

**Step 1: Update send_password_reset_email function signature**

Replace the function definition (around line 180) with:

```python
async def send_password_reset_email(
    to_email: str,
    verification_code: str,  # Changed from reset_token
    counselor_name: str = None,
    tenant_id: str = "career",
    source: str | None = None,
):
    """
    Send password reset email with 6-digit verification code

    Args:
        to_email: Recipient email address
        verification_code: 6-digit verification code
        counselor_name: Name of the counselor (optional)
        tenant_id: Tenant identifier (career/island/island_parents)
        source: Source of request (app/web)
    """
```

**Step 2: Update email HTML template**

Replace the email body HTML with:

```python
    tenant_names = {
        "career": "Career",
        "island": "浮島",
        "island_parents": "浮島親子",
    }
    tenant_name = tenant_names.get(tenant_id, "Career")

    subject = f"密碼重設驗證碼 - {tenant_name}"

    greeting = f"Hi {counselor_name}," if counselor_name else "Hi User,"

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2c3e50;">密碼重設請求</h2>

            <p>{greeting}</p>

            <p>我們收到了重設您 {tenant_name} 帳號密碼的請求。</p>

            <div style="background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin: 20px 0;">
                <p style="margin: 0; font-size: 14px; color: #666;">您的驗證碼：</p>
                <p style="margin: 10px 0 0 0; font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #007bff;">
                    {verification_code}
                </p>
            </div>

            <p style="color: #666; font-size: 14px;">
                <strong>注意事項：</strong>
            </p>
            <ul style="color: #666; font-size: 14px;">
                <li>此驗證碼 <strong>15 分鐘</strong>內有效</li>
                <li>請在 App 內輸入此驗證碼以重設密碼</li>
                <li>如果不是您本人的請求，請忽略此郵件</li>
                <li>請勿將此驗證碼分享給任何人</li>
            </ul>

            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

            <p style="color: #999; font-size: 12px; text-align: center;">
                這是一封自動發送的郵件，請勿直接回覆。<br>
                © 2026 {tenant_name}. All rights reserved.
            </p>
        </div>
    </body>
    </html>
    """
```

**Step 3: Verify email function imports**

Run:
```bash
python -c "from app.services.external.email_sender import send_password_reset_email; print('Email service OK')"
```

Expected: "Email service OK"

**Step 4: Commit**

```bash
git add app/services/external/email_sender.py
git commit -m "feat: update password reset email to send verification code"
```

---

## Task 6: Add Code Generation Utility

**Files:**
- Create: `app/utils/verification_code.py`

**Step 1: Write test for code generation**

Create file `tests/unit/test_verification_code.py`:

```python
import pytest
from app.utils.verification_code import generate_verification_code


def test_generate_code_length():
    """Test that code is exactly 6 digits"""
    code = generate_verification_code()
    assert len(code) == 6


def test_generate_code_is_numeric():
    """Test that code contains only digits"""
    code = generate_verification_code()
    assert code.isdigit()


def test_generate_code_uniqueness():
    """Test that generated codes are different (statistically)"""
    codes = [generate_verification_code() for _ in range(100)]
    unique_codes = set(codes)
    # At least 95% should be unique (allowing for rare collisions)
    assert len(unique_codes) >= 95


def test_generate_code_range():
    """Test that code is within valid range"""
    for _ in range(100):
        code = generate_verification_code()
        code_int = int(code)
        assert 0 <= code_int <= 999999
```

**Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/unit/test_verification_code.py -v
```

Expected: FAIL (module not found)

**Step 3: Write implementation**

Create `app/utils/verification_code.py`:

```python
import secrets
from app.core.config import settings


def generate_verification_code() -> str:
    """
    Generate a cryptographically secure 6-digit verification code.

    Returns:
        str: A 6-digit string (with leading zeros if necessary)

    Example:
        >>> code = generate_verification_code()
        >>> len(code)
        6
        >>> code.isdigit()
        True
    """
    # Generate random number in range [0, 999999]
    code_int = secrets.randbelow(1_000_000)

    # Format with leading zeros to ensure 6 digits
    code = f"{code_int:06d}"

    return code
```

**Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/unit/test_verification_code.py -v
```

Expected: 4 PASSED

**Step 5: Commit**

```bash
git add app/utils/verification_code.py tests/unit/test_verification_code.py
git commit -m "feat: add verification code generation utility"
```

---

## Task 7: Update Password Reset Request Endpoint (TDD)

**Files:**
- Modify: `app/api/v1/password_reset.py`
- Create: `tests/integration/test_password_reset_verification.py`

**Step 7.1: Write failing test for code generation**

Create `tests/integration/test_password_reset_verification.py`:

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone

from app.models.counselor import Counselor
from app.models.password_reset import PasswordResetToken


class TestPasswordResetRequest:
    """Test /api/v1/auth/password-reset/request endpoint"""

    @pytest.mark.asyncio
    async def test_request_generates_verification_code(
        self, client: AsyncClient, db: AsyncSession, test_counselor: Counselor
    ):
        """Test that request generates 6-digit verification code"""
        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": "career",
                "source": "app",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify code was created in database
        result = await db.execute(
            "SELECT verification_code, code_expires_at FROM password_reset_tokens WHERE email = :email ORDER BY created_at DESC LIMIT 1",
            {"email": test_counselor.email}
        )
        row = result.fetchone()

        assert row is not None
        code = row[0]
        expires_at = row[1]

        # Verify code format
        assert code is not None
        assert len(code) == 6
        assert code.isdigit()

        # Verify expiry time (should be ~15 minutes from now)
        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(minutes=15)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 10  # Allow 10 seconds tolerance
```

**Step 7.2: Run test to verify failure**

Run:
```bash
pytest tests/integration/test_password_reset_verification.py::TestPasswordResetRequest::test_request_generates_verification_code -v
```

Expected: FAIL (verification_code is None)

**Step 7.3: Implement code generation in request endpoint**

In `app/api/v1/password_reset.py`, modify the `request_password_reset` function:

Add import at top:
```python
from app.utils.verification_code import generate_verification_code
```

Replace the token generation section (around line 60-75) with:

```python
    # Generate 6-digit verification code instead of token
    verification_code = generate_verification_code()
    code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.VERIFICATION_CODE_EXPIRY_MINUTES
    )

    # Create password reset record with verification code
    reset_token = PasswordResetToken(
        token=secrets.token_urlsafe(32),  # Keep for backward compat during transition
        verification_code=verification_code,
        email=email,
        tenant_id=tenant_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
        code_expires_at=code_expires_at,
        verify_attempts=0,
        request_ip=request.client.host if request.client else None,
    )
```

**Step 7.4: Update email sending call**

Replace the email sending line (around line 90) with:

```python
    await send_password_reset_email(
        to_email=email,
        verification_code=verification_code,  # Changed from reset_token=reset_token.token
        counselor_name=counselor_name,
        tenant_id=tenant_id,
        source=source,
    )
```

**Step 7.5: Run test to verify it passes**

Run:
```bash
pytest tests/integration/test_password_reset_verification.py::TestPasswordResetRequest::test_request_generates_verification_code -v
```

Expected: PASSED

**Step 7.6: Commit**

```bash
git add app/api/v1/password_reset.py tests/integration/test_password_reset_verification.py
git commit -m "feat: generate 6-digit verification code in password reset request"
```

---

## Task 8: Implement Verify Code Endpoint (TDD)

**Files:**
- Modify: `app/api/v1/password_reset.py`
- Modify: `tests/integration/test_password_reset_verification.py`

**Step 8.1: Write tests for verify code endpoint**

Add to `tests/integration/test_password_reset_verification.py`:

```python
class TestVerifyCode:
    """Test /api/v1/auth/password-reset/verify-code endpoint"""

    @pytest.mark.asyncio
    async def test_verify_code_success(
        self, client: AsyncClient, db: AsyncSession, test_counselor: Counselor
    ):
        """Test successful code verification"""
        # First request a reset
        await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_counselor.email, "tenant_id": "career"},
        )

        # Get the verification code from DB
        result = await db.execute(
            "SELECT verification_code FROM password_reset_tokens WHERE email = :email ORDER BY created_at DESC LIMIT 1",
            {"email": test_counselor.email}
        )
        code = result.scalar_one()

        # Verify the code
        response = await client.post(
            "/api/v1/auth/password-reset/verify-code",
            json={
                "email": test_counselor.email,
                "verification_code": code,
                "tenant_id": "career",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "valid" in data["message"].lower()


    @pytest.mark.asyncio
    async def test_verify_code_invalid(
        self, client: AsyncClient, test_counselor: Counselor
    ):
        """Test verification with invalid code"""
        response = await client.post(
            "/api/v1/auth/password-reset/verify-code",
            json={
                "email": test_counselor.email,
                "verification_code": "999999",
                "tenant_id": "career",
            },
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


    @pytest.mark.asyncio
    async def test_verify_code_expired(
        self, client: AsyncClient, db: AsyncSession, test_counselor: Counselor
    ):
        """Test verification with expired code"""
        # Request a reset
        await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_counselor.email, "tenant_id": "career"},
        )

        # Manually expire the code
        await db.execute(
            """
            UPDATE password_reset_tokens
            SET code_expires_at = :expired_time
            WHERE email = :email
            """,
            {
                "expired_time": datetime.now(timezone.utc) - timedelta(minutes=1),
                "email": test_counselor.email
            }
        )
        await db.commit()

        # Get the code
        result = await db.execute(
            "SELECT verification_code FROM password_reset_tokens WHERE email = :email ORDER BY created_at DESC LIMIT 1",
            {"email": test_counselor.email}
        )
        code = result.scalar_one()

        # Try to verify
        response = await client.post(
            "/api/v1/auth/password-reset/verify-code",
            json={
                "email": test_counselor.email,
                "verification_code": code,
                "tenant_id": "career",
            },
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()


    @pytest.mark.asyncio
    async def test_verify_code_max_attempts_lockout(
        self, client: AsyncClient, db: AsyncSession, test_counselor: Counselor
    ):
        """Test lockout after max verification attempts"""
        # Request a reset
        await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_counselor.email, "tenant_id": "career"},
        )

        # Try wrong code 5 times
        for i in range(5):
            response = await client.post(
                "/api/v1/auth/password-reset/verify-code",
                json={
                    "email": test_counselor.email,
                    "verification_code": "000000",  # Wrong code
                    "tenant_id": "career",
                },
            )
            assert response.status_code == 400

        # 6th attempt should be locked
        response = await client.post(
            "/api/v1/auth/password-reset/verify-code",
            json={
                "email": test_counselor.email,
                "verification_code": "000000",
                "tenant_id": "career",
            },
        )

        assert response.status_code == 429  # Too Many Requests
        assert "locked" in response.json()["detail"].lower() or "too many" in response.json()["detail"].lower()

        # Verify locked_until is set correctly
        result = await db.execute(
            "SELECT locked_until FROM password_reset_tokens WHERE email = :email ORDER BY created_at DESC LIMIT 1",
            {"email": test_counselor.email}
        )
        locked_until = result.scalar_one()

        assert locked_until is not None
        expected_unlock = datetime.now(timezone.utc) + timedelta(minutes=15)
        time_diff = abs((locked_until - expected_unlock).total_seconds())
        assert time_diff < 10
```

**Step 8.2: Run tests to verify failure**

Run:
```bash
pytest tests/integration/test_password_reset_verification.py::TestVerifyCode -v
```

Expected: FAIL (endpoint not found)

**Step 8.3: Implement verify code endpoint**

In `app/api/v1/password_reset.py`, add new endpoint after `request_password_reset`:

```python
@router.post("/auth/password-reset/verify-code", response_model=VerifyCodeResponse)
async def verify_password_reset_code(
    request: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a password reset verification code.

    This endpoint checks if the provided verification code is:
    - Valid (exists in database)
    - Not expired (within 15 minutes)
    - Not locked out (less than 5 failed attempts)

    Returns success if code is valid, otherwise raises appropriate error.
    """
    # Query for the reset token with this email and tenant
    result = await db.execute(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.email == request.email,
            PasswordResetToken.tenant_id == request.tenant_id,
            PasswordResetToken.deleted_at.is_(None),
        )
        .order_by(PasswordResetToken.created_at.desc())
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification code"
        )

    # Check if locked out
    if reset_token.locked_until:
        if datetime.now(timezone.utc) < reset_token.locked_until:
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed attempts. Please try again after {reset_token.locked_until.strftime('%H:%M')}"
            )
        else:
            # Lockout expired, reset attempts
            reset_token.locked_until = None
            reset_token.verify_attempts = 0

    # Check if code is expired
    if reset_token.code_expires_at and datetime.now(timezone.utc) > reset_token.code_expires_at:
        raise HTTPException(
            status_code=400,
            detail="Verification code has expired. Please request a new one."
        )

    # Verify the code
    if reset_token.verification_code != request.verification_code:
        # Increment failed attempts
        reset_token.verify_attempts += 1

        # Check if should lock out
        if reset_token.verify_attempts >= settings.VERIFICATION_CODE_MAX_ATTEMPTS:
            reset_token.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.VERIFICATION_CODE_LOCKOUT_MINUTES
            )
            await db.commit()
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed attempts. Account locked for {settings.VERIFICATION_CODE_LOCKOUT_MINUTES} minutes."
            )

        await db.commit()
        remaining = settings.VERIFICATION_CODE_MAX_ATTEMPTS - reset_token.verify_attempts
        raise HTTPException(
            status_code=400,
            detail=f"Invalid verification code. {remaining} attempts remaining."
        )

    # Code is valid - reset attempts counter
    reset_token.verify_attempts = 0
    await db.commit()

    return VerifyCodeResponse(
        success=True,
        message="Verification code is valid"
    )
```

**Step 8.4: Add imports**

Add to imports at top of file:

```python
from app.schemas.auth import VerifyCodeRequest, VerifyCodeResponse
```

**Step 8.5: Run tests to verify they pass**

Run:
```bash
pytest tests/integration/test_password_reset_verification.py::TestVerifyCode -v
```

Expected: 4 PASSED

**Step 8.6: Commit**

```bash
git add app/api/v1/password_reset.py tests/integration/test_password_reset_verification.py
git commit -m "feat: implement verification code validation endpoint with lockout"
```

---

## Task 9: Update Confirm Password Reset Endpoint (TDD)

**Files:**
- Modify: `app/api/v1/password_reset.py`
- Modify: `tests/integration/test_password_reset_verification.py`

**Step 9.1: Write tests for confirm with verification code**

Add to `tests/integration/test_password_reset_verification.py`:

```python
class TestConfirmPasswordReset:
    """Test /api/v1/auth/password-reset/confirm endpoint with verification code"""

    @pytest.mark.asyncio
    async def test_confirm_success_with_verification_code(
        self, client: AsyncClient, db: AsyncSession, test_counselor: Counselor
    ):
        """Test successful password reset with verification code"""
        old_password_hash = test_counselor.password_hash

        # Request reset
        await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_counselor.email, "tenant_id": "career"},
        )

        # Get code
        result = await db.execute(
            "SELECT verification_code FROM password_reset_tokens WHERE email = :email ORDER BY created_at DESC LIMIT 1",
            {"email": test_counselor.email}
        )
        code = result.scalar_one()

        # Confirm with new password
        new_password = "NewSecurePassword123"
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": test_counselor.email,
                "verification_code": code,
                "new_password": new_password,
                "tenant_id": "career",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify password was changed
        await db.refresh(test_counselor)
        assert test_counselor.password_hash != old_password_hash

        # Verify can login with new password
        from app.utils.password import verify_password
        assert verify_password(new_password, test_counselor.password_hash)


    @pytest.mark.asyncio
    async def test_confirm_invalid_code(
        self, client: AsyncClient, test_counselor: Counselor
    ):
        """Test confirm with invalid verification code"""
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": test_counselor.email,
                "verification_code": "999999",
                "new_password": "NewPassword123",
                "tenant_id": "career",
            },
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


    @pytest.mark.asyncio
    async def test_confirm_weak_password(
        self, client: AsyncClient, db: AsyncSession, test_counselor: Counselor
    ):
        """Test confirm with weak password"""
        # Request reset
        await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_counselor.email, "tenant_id": "career"},
        )

        # Get code
        result = await db.execute(
            "SELECT verification_code FROM password_reset_tokens WHERE email = :email ORDER BY created_at DESC LIMIT 1",
            {"email": test_counselor.email}
        )
        code = result.scalar_one()

        # Try with weak password (less than 8 chars)
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": test_counselor.email,
                "verification_code": code,
                "new_password": "weak",
                "tenant_id": "career",
            },
        )

        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()


    @pytest.mark.asyncio
    async def test_confirm_code_cannot_be_reused(
        self, client: AsyncClient, db: AsyncSession, test_counselor: Counselor
    ):
        """Test that verification code cannot be reused after successful reset"""
        # Request reset
        await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_counselor.email, "tenant_id": "career"},
        )

        # Get code
        result = await db.execute(
            "SELECT verification_code FROM password_reset_tokens WHERE email = :email ORDER BY created_at DESC LIMIT 1",
            {"email": test_counselor.email}
        )
        code = result.scalar_one()

        # First reset - should succeed
        response1 = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": test_counselor.email,
                "verification_code": code,
                "new_password": "FirstPassword123",
                "tenant_id": "career",
            },
        )
        assert response1.status_code == 200

        # Second attempt with same code - should fail
        response2 = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": test_counselor.email,
                "verification_code": code,
                "new_password": "SecondPassword123",
                "tenant_id": "career",
            },
        )
        assert response2.status_code == 400
```

**Step 9.2: Run tests to verify failure**

Run:
```bash
pytest tests/integration/test_password_reset_verification.py::TestConfirmPasswordReset -v
```

Expected: FAIL (endpoint uses old logic)

**Step 9.3: Rewrite confirm endpoint to use verification code**

In `app/api/v1/password_reset.py`, replace the `confirm_password_reset` function:

```python
@router.post("/auth/password-reset/confirm", response_model=PasswordResetConfirmResponse)
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm password reset with verification code and set new password.

    This endpoint:
    1. Validates the verification code
    2. Checks password strength
    3. Updates the user's password
    4. Marks the code as used (cannot be reused)
    """
    # Query for the reset token
    result = await db.execute(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.email == request.email,
            PasswordResetToken.tenant_id == request.tenant_id,
            PasswordResetToken.verification_code == request.verification_code,
            PasswordResetToken.deleted_at.is_(None),
        )
        .order_by(PasswordResetToken.created_at.desc())
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(
            status_code=400,
            detail="Invalid verification code"
        )

    # Check if already used
    if reset_token.used:
        raise HTTPException(
            status_code=400,
            detail="This verification code has already been used"
        )

    # Check if locked out
    if reset_token.locked_until and datetime.now(timezone.utc) < reset_token.locked_until:
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Please request a new code."
        )

    # Check if expired
    if reset_token.code_expires_at and datetime.now(timezone.utc) > reset_token.code_expires_at:
        raise HTTPException(
            status_code=400,
            detail="Verification code has expired. Please request a new one."
        )

    # Validate password strength
    if is_password_weak(request.new_password):
        raise HTTPException(
            status_code=400,
            detail="Password is too weak. Must be at least 8 characters."
        )

    # Find the counselor
    counselor_result = await db.execute(
        select(Counselor).where(
            Counselor.email == request.email,
            Counselor.tenant_id == request.tenant_id,
            Counselor.deleted_at.is_(None),
        )
    )
    counselor = counselor_result.scalar_one_or_none()

    if not counselor:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Update password
    counselor.password_hash = hash_password(request.new_password)

    # Mark token as used
    reset_token.used = True
    reset_token.used_at = datetime.now(timezone.utc)

    await db.commit()

    return PasswordResetConfirmResponse(
        success=True,
        message="Password has been reset successfully"
    )
```

**Step 9.4: Run tests to verify they pass**

Run:
```bash
pytest tests/integration/test_password_reset_verification.py::TestConfirmPasswordReset -v
```

Expected: 4 PASSED

**Step 9.5: Commit**

```bash
git add app/api/v1/password_reset.py tests/integration/test_password_reset_verification.py
git commit -m "feat: update confirm endpoint to use verification code instead of token"
```

---

## Task 10: Remove Old Token Verification Endpoint

**Files:**
- Modify: `app/api/v1/password_reset.py`

**Step 10.1: Delete old verify endpoint**

Remove the `verify_reset_token` function (around line 100-150 in original file).

**Step 10.2: Verify API still works**

Run:
```bash
pytest tests/integration/test_password_reset_verification.py -v
```

Expected: All tests still PASS

**Step 10.3: Commit**

```bash
git add app/api/v1/password_reset.py
git commit -m "refactor: remove old token verification endpoint"
```

---

## Task 11: End-to-End Integration Test

**Files:**
- Modify: `tests/integration/test_password_reset_verification.py`

**Step 11.1: Write comprehensive E2E test**

Add to `tests/integration/test_password_reset_verification.py`:

```python
class TestPasswordResetEndToEnd:
    """End-to-end tests for complete password reset flow"""

    @pytest.mark.asyncio
    async def test_complete_password_reset_flow(
        self, client: AsyncClient, db: AsyncSession, test_counselor: Counselor
    ):
        """Test complete flow: request → verify → confirm → login"""
        original_password = "OriginalPassword123"
        new_password = "NewSecurePassword456"

        # Step 1: Request password reset
        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={
                "email": test_counselor.email,
                "tenant_id": "career",
                "source": "app",
            },
        )
        assert response.status_code == 200

        # Step 2: Get verification code from database
        result = await db.execute(
            "SELECT verification_code FROM password_reset_tokens WHERE email = :email ORDER BY created_at DESC LIMIT 1",
            {"email": test_counselor.email}
        )
        code = result.scalar_one()
        assert len(code) == 6
        assert code.isdigit()

        # Step 3: Verify the code (optional step)
        response = await client.post(
            "/api/v1/auth/password-reset/verify-code",
            json={
                "email": test_counselor.email,
                "verification_code": code,
                "tenant_id": "career",
            },
        )
        assert response.status_code == 200

        # Step 4: Confirm password reset
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": test_counselor.email,
                "verification_code": code,
                "new_password": new_password,
                "tenant_id": "career",
            },
        )
        assert response.status_code == 200

        # Step 5: Verify can login with new password
        await db.refresh(test_counselor)
        from app.utils.password import verify_password
        assert verify_password(new_password, test_counselor.password_hash)

        # Step 6: Verify cannot use code again
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": test_counselor.email,
                "verification_code": code,
                "new_password": "AnotherPassword789",
                "tenant_id": "career",
            },
        )
        assert response.status_code == 400
```

**Step 11.2: Run E2E test**

Run:
```bash
pytest tests/integration/test_password_reset_verification.py::TestPasswordResetEndToEnd -v
```

Expected: PASSED

**Step 11.3: Commit**

```bash
git add tests/integration/test_password_reset_verification.py
git commit -m "test: add end-to-end password reset verification flow test"
```

---

## Task 12: Run Full Test Suite

**Step 12.1: Run all password reset tests**

Run:
```bash
pytest tests/integration/test_password_reset_verification.py -v
```

Expected: All tests PASS

**Step 12.2: Run entire integration test suite**

Run:
```bash
pytest tests/integration/ -v
```

Expected: All tests PASS (or identify any broken tests from old API)

**Step 12.3: Fix any broken old tests**

If old tests in `test_password_reset_api.py` are failing:
- Either delete them (if testing old token flow)
- Or update them to use verification codes

---

## Task 13: Update Documentation

**Files:**
- Create: `docs/api/password-reset-verification-code.md`

**Step 13.1: Write API documentation**

Create `docs/api/password-reset-verification-code.md`:

```markdown
# Password Reset - Verification Code API

## Overview

The password reset system uses 6-digit verification codes sent via email. This is more user-friendly than token-based links as users can complete the flow entirely within the app.

## Security Features

- **6-digit codes**: 1,000,000 possible combinations
- **15-minute expiry**: Codes are valid for 15 minutes only
- **Lockout mechanism**: 5 failed attempts locks the account for 15 minutes
- **One-time use**: Codes cannot be reused after successful password reset
- **Rate limiting**: 3 requests per hour per IP address

## API Endpoints

### 1. Request Password Reset

**POST** `/api/v1/auth/password-reset/request`

Send verification code to user's email.

**Request Body:**
```json
{
  "email": "user@example.com",
  "tenant_id": "career",
  "source": "app"
}
```

**Response:**
```json
{
  "success": true,
  "message": "If an account exists, a verification code has been sent"
}
```

**Notes:**
- Always returns success (prevents user enumeration)
- Sends 6-digit code to email if user exists
- Rate limited to 3 requests/hour

---

### 2. Verify Code (Optional)

**POST** `/api/v1/auth/password-reset/verify-code`

Validate verification code before password update.

**Request Body:**
```json
{
  "email": "user@example.com",
  "verification_code": "485921",
  "tenant_id": "career"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Verification code is valid"
}
```

**Error Responses:**

| Status | Detail |
|--------|--------|
| 400 | Invalid verification code |
| 400 | Verification code has expired |
| 429 | Too many failed attempts. Account locked for X minutes |

---

### 3. Confirm Password Reset

**POST** `/api/v1/auth/password-reset/confirm`

Reset password using verification code.

**Request Body:**
```json
{
  "email": "user@example.com",
  "verification_code": "485921",
  "new_password": "NewSecurePassword123",
  "tenant_id": "career"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Password has been reset successfully"
}
```

**Error Responses:**

| Status | Detail |
|--------|--------|
| 400 | Invalid verification code |
| 400 | This verification code has already been used |
| 400 | Verification code has expired |
| 400 | Password is too weak (min 8 characters) |
| 429 | Too many failed attempts |

---

## Client Implementation Example

### React Native / Flutter

```typescript
// Step 1: Request code
async function requestPasswordReset(email: string) {
  const response = await fetch('/api/v1/auth/password-reset/request', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      tenant_id: 'career',
      source: 'app'
    })
  });

  return response.json();
}

// Step 2: User enters code from email

// Step 3: Verify code (optional - for better UX)
async function verifyCode(email: string, code: string) {
  const response = await fetch('/api/v1/auth/password-reset/verify-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      verification_code: code,
      tenant_id: 'career'
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return response.json();
}

// Step 4: Confirm password reset
async function confirmPasswordReset(
  email: string,
  code: string,
  newPassword: string
) {
  const response = await fetch('/api/v1/auth/password-reset/confirm', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      email,
      verification_code: code,
      new_password: newPassword,
      tenant_id: 'career'
    })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }

  return response.json();
}
```

---

## Email Template

Users will receive an email with:

```
密碼重設請求

Hi User,

我們收到了重設您 Career 帳號密碼的請求。

您的驗證碼：
  485921

注意事項：
- 此驗證碼 15 分鐘內有效
- 請在 App 內輸入此驗證碼以重設密碼
- 如果不是您本人的請求,請忽略此郵件
- 請勿將此驗證碼分享給任何人
```

---

## Testing

Run tests:
```bash
pytest tests/integration/test_password_reset_verification.py -v
```

Test coverage:
- ✅ Code generation (6 digits, numeric)
- ✅ Code verification (valid/invalid/expired)
- ✅ Lockout mechanism (5 attempts)
- ✅ Password confirmation
- ✅ One-time use enforcement
- ✅ End-to-end flow
```

**Step 13.2: Commit**

```bash
git add docs/api/password-reset-verification-code.md
git commit -m "docs: add verification code API documentation"
```

---

## Task 14: Update CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

**Step 14.1: Add entry to CHANGELOG**

Add at the top of `CHANGELOG.md`:

```markdown
## [Unreleased]

### Changed
- **BREAKING**: Password reset now uses 6-digit verification codes instead of token-based links
  - Users receive verification code via email
  - Code must be entered in app to reset password
  - Codes expire after 15 minutes
  - Maximum 5 verification attempts before 15-minute lockout
  - Old token-based endpoint `/auth/password-reset/verify` removed

### Added
- New endpoint `POST /api/v1/auth/password-reset/verify-code` for code verification
- Lockout mechanism after 5 failed verification attempts
- Verification code expiry (15 minutes)
- Improved email template with verification code display

### Removed
- Token-based password reset verification endpoint
- Long-lived (6-hour) password reset tokens

### Security
- Reduced attack surface with shorter code expiry (15 min vs 6 hours)
- Added lockout mechanism to prevent brute force attacks
- Verification codes are cryptographically secure (secrets.randbelow)
```

**Step 14.2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: update CHANGELOG for verification code implementation"
```

---

## Task 15: Final Verification

**Step 15.1: Run complete test suite**

Run:
```bash
pytest -v
```

Expected: All tests PASS

**Step 15.2: Test manual flow (optional but recommended)**

Start the server:
```bash
uvicorn app.main:app --reload
```

Test in another terminal:
```bash
# Request reset
curl -X POST http://localhost:8000/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "tenant_id": "career"}'

# Check email for code (or check database)

# Verify code
curl -X POST http://localhost:8000/api/v1/auth/password-reset/verify-code \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "verification_code": "123456", "tenant_id": "career"}'

# Confirm password reset
curl -X POST http://localhost:8000/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "verification_code": "123456", "new_password": "NewPassword123", "tenant_id": "career"}'
```

**Step 15.3: Final commit**

```bash
git add -A
git commit -m "feat: complete password reset verification code implementation"
```

---

## Summary

**Total Tasks**: 15
**Estimated Time**: 6-7 hours
**Complexity**: Medium-High

**Key Changes**:
- ✅ Database schema updated with verification code fields
- ✅ 6-digit code generation utility
- ✅ Email service sends codes instead of links
- ✅ New verify-code endpoint with lockout mechanism
- ✅ Updated confirm endpoint to use verification codes
- ✅ Removed old token verification endpoint
- ✅ Comprehensive test coverage (13+ test cases)
- ✅ API documentation
- ✅ CHANGELOG updated

**Security Improvements**:
- Shorter expiry time (15 min vs 6 hours)
- Lockout after failed attempts
- Cryptographically secure code generation
- One-time use enforcement

**Breaking Changes**:
- Old token-based reset links no longer work
- Frontend must be updated to collect verification code input
- Removed `/auth/password-reset/verify` endpoint

---

## Rollback Plan

If issues occur, rollback with:

```bash
# Revert all commits
git revert HEAD~15..HEAD

# Or rollback database
alembic downgrade -1
```

---

**Plan Version**: 1.0
**Created**: 2026-01-31
**Author**: Claude (Sonnet 4.5)
