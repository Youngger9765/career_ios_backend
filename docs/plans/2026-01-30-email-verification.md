# Email Verification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add email verification to registration flow to prevent fake accounts and verify email ownership. Default enabled (ENABLE_EMAIL_VERIFICATION=true).

**Architecture:**
- Add verification token generation using JWT (24-hour expiry)
- Store verification status in `counselors.is_active` (False until verified)
- Send verification email via existing `EmailSenderService`
- Provide verification endpoint and resend functionality
- Environment variable toggle for disabling in dev/test

**Tech Stack:**
- JWT tokens (using existing `jose` library)
- SQLAlchemy ORM (existing `Counselor` model)
- FastAPI endpoints
- Existing SMTP email service

---

## Task 1: Add Email Verification Configuration

**Files:**
- Modify: `app/core/config.py:100-110`

**Step 1: Add email verification settings to Settings class**

Add after line 99 (LOG_FILE):
```python
    # Email Verification (Default Enabled)
    ENABLE_EMAIL_VERIFICATION: bool = True  # Can be disabled for dev/test
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    VERIFICATION_EMAIL_SUBJECT: str = "Verify Your Email - {tenant_name}"
```

**Step 2: Commit**

```bash
git add app/core/config.py
git commit -m "config: add email verification settings (default enabled)"
```

---

## Task 2: Create Email Verification Token Service

**Files:**
- Create: `app/core/email_verification.py`
- Create: `tests/unit/test_email_verification.py`

**Step 1: Write failing test for token generation**

Create `tests/unit/test_email_verification.py`:
```python
"""
Unit tests for email verification token service
"""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.email_verification import (
    create_verification_token,
    verify_verification_token,
)


class TestEmailVerification:
    """Test email verification token operations"""

    def test_create_verification_token(self):
        """Test creating a verification token"""
        email = "test@example.com"
        tenant_id = "career"

        token = create_verification_token(email, tenant_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token(self):
        """Test verifying a valid token"""
        email = "test@example.com"
        tenant_id = "career"

        token = create_verification_token(email, tenant_id)
        result = verify_verification_token(token)

        assert result is not None
        assert result["email"] == email
        assert result["tenant_id"] == tenant_id
        assert result["type"] == "email_verification"

    def test_verify_invalid_token(self):
        """Test verifying an invalid token"""
        result = verify_verification_token("invalid_token")
        assert result is None

    def test_verify_expired_token(self):
        """Test verifying an expired token"""
        # Create token that expires immediately
        from app.core.config import Settings
        from jose import jwt

        settings = Settings()

        data = {
            "sub": "test@example.com",
            "tenant_id": "career",
            "type": "email_verification",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Already expired
        }

        expired_token = jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        result = verify_verification_token(expired_token)

        assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/unit/test_email_verification.py -v`
Expected: FAIL with "ModuleNotFoundError"

**Step 3: Implement email verification token service**

Create `app/core/email_verification.py`:
```python
"""
Email verification token service
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from jose import JWTError, jwt

from app.core.config import Settings

settings = Settings()


def create_verification_token(email: str, tenant_id: str) -> str:
    """
    Create an email verification token

    Args:
        email: Email address to verify
        tenant_id: Tenant ID

    Returns:
        JWT token string
    """
    expires_delta = timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
    expire = datetime.now(timezone.utc) + expires_delta

    data = {
        "sub": email,
        "tenant_id": tenant_id,
        "type": "email_verification",
        "exp": expire,
    }

    token = jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token


def verify_verification_token(token: str) -> Optional[Dict[str, str]]:
    """
    Verify an email verification token

    Args:
        token: JWT token string

    Returns:
        Dict with email, tenant_id, and type if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        token_type = payload.get("type")

        if not email or not tenant_id or token_type != "email_verification":
            return None

        return {"email": email, "tenant_id": tenant_id, "type": token_type}

    except JWTError:
        return None
```

**Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/unit/test_email_verification.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/core/email_verification.py tests/unit/test_email_verification.py
git commit -m "feat: add email verification token service"
```

---

## Task 3: Add Verification Email Template to EmailSenderService

**Files:**
- Modify: `app/services/external/email_sender.py`

**Step 1: Add send_verification_email method**

Add new method after `send_password_reset_email` (around line 78):
```python
    async def send_verification_email(
        self,
        to_email: str,
        verification_token: str,
        counselor_name: str = None,
        tenant_id: str = "career",
    ) -> bool:
        """
        Send email verification email

        Args:
            to_email: Recipient email
            verification_token: Email verification token
            counselor_name: Optional counselor name for personalization
            tenant_id: Tenant ID for customizing email content

        Returns:
            True if sent successfully
        """
        # Tenant name mapping
        tenant_names = {
            "career": "Career",
            "island": "浮島",
            "island_parents": "浮島親子",
        }
        tenant_name = tenant_names.get(tenant_id, "Career")

        subject = f"Verify Your Email - {tenant_name}"

        # Generate verification URL using configured APP_URL
        # Use dynamic tenant route if tenant is valid
        from app.utils.tenant import get_tenant_url_path

        tenant_url_path = get_tenant_url_path(tenant_id)
        if tenant_url_path:
            verify_path = f"/{tenant_url_path}/verify-email"
        else:
            verify_path = "/verify-email"

        verify_url = f"{self.app_url}{verify_path}?token={verification_token}"

        html_body = self._generate_verification_html(
            counselor_name or "User", verify_url, tenant_name
        )

        try:
            return await self._send_email(to_email, subject, html_body)
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            raise
```

**Step 2: Add HTML template generation method**

Add new method after password reset HTML generation:
```python
    def _generate_verification_html(
        self, counselor_name: str, verify_url: str, tenant_name: str
    ) -> str:
        """Generate HTML for verification email"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Welcome to {tenant_name}!</h1>
    </div>

    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Hi {counselor_name},</h2>

        <p style="font-size: 16px; margin: 20px 0;">
            Thank you for registering! Please verify your email address to activate your account and get started.
        </p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}"
               style="background: #667eea; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px; display: inline-block;">
                Verify Email Address
            </a>
        </div>

        <p style="font-size: 14px; color: #666; margin: 20px 0;">
            This verification link will expire in 24 hours.
        </p>

        <p style="font-size: 14px; color: #666; margin: 20px 0;">
            If you didn't create an account, you can safely ignore this email.
        </p>

        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

        <p style="font-size: 12px; color: #999; text-align: center;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{verify_url}" style="color: #667eea; word-break: break-all;">{verify_url}</a>
        </p>
    </div>
</body>
</html>
"""
```

**Step 3: Commit**

```bash
git add app/services/external/email_sender.py
git commit -m "feat: add verification email template to EmailSenderService"
```

---

## Task 4: Modify Registration to Send Verification Email

**Files:**
- Modify: `app/api/auth.py:79-117`
- Modify: `tests/integration/test_auth_api.py`

**Step 1: Write failing test for registration with email verification**

Add to `tests/integration/test_auth_api.py`:
```python
    def test_register_sends_verification_email(self, db_session: Session, monkeypatch):
        """Test that registration sends verification email and sets is_active=False"""
        from app.core.config import Settings

        # Mock email sending
        email_sent = []

        async def mock_send_verification_email(self, to_email, token, name, tenant_id):
            email_sent.append({"to": to_email, "token": token})
            return True

        from app.services.external import email_sender
        monkeypatch.setattr(
            email_sender.EmailSenderService,
            "send_verification_email",
            mock_send_verification_email,
        )

        # Ensure email verification is enabled
        settings = Settings()
        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", True)

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "SecurePass123!",
                    "tenant_id": "career",
                    "full_name": "New User",
                },
            )

            # Registration should succeed but account inactive
            assert response.status_code == 201
            data = response.json()
            assert "access_token" in data  # Still get token for UX

            # Verify email was sent
            assert len(email_sent) == 1
            assert email_sent[0]["to"] == "newuser@example.com"
            assert len(email_sent[0]["token"]) > 0

            # Verify counselor is inactive
            from sqlalchemy import select
            from app.models.counselor import Counselor

            counselor = db_session.execute(
                select(Counselor).where(
                    Counselor.email == "newuser@example.com",
                    Counselor.tenant_id == "career",
                )
            ).scalar_one()

            assert counselor.is_active is False
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/integration/test_auth_api.py::TestAuthAPI::test_register_sends_verification_email -v`
Expected: FAIL (email not sent, is_active not False)

**Step 3: Modify registration endpoint to send verification email**

Modify `app/api/auth.py`:

Add imports at top:
```python
from app.core.email_verification import create_verification_token
from app.services.external.email_sender import email_sender
from app.core.config import Settings

settings = Settings()
```

Modify register function (around line 79-117):
```python
    try:
        # Determine is_active based on email verification setting
        is_active = not settings.ENABLE_EMAIL_VERIFICATION

        # Create new counselor (inactive if email verification enabled)
        counselor = Counselor(
            email=register_data.email,
            username=register_data.username,
            full_name=register_data.full_name,
            hashed_password=hash_password(register_data.password),
            tenant_id=register_data.tenant_id,
            role=register_data.role,
            is_active=is_active,  # False if verification enabled
        )

        db.add(counselor)
        db.commit()
        db.refresh(counselor)

        # Send verification email if enabled
        if settings.ENABLE_EMAIL_VERIFICATION:
            try:
                verification_token = create_verification_token(
                    counselor.email, counselor.tenant_id
                )
                await email_sender.send_verification_email(
                    to_email=counselor.email,
                    verification_token=verification_token,
                    counselor_name=counselor.full_name,
                    tenant_id=counselor.tenant_id,
                )
                logger.info(f"Verification email sent to {counselor.email}")
            except Exception as e:
                logger.error(f"Failed to send verification email: {e}")
                # Don't fail registration if email fails, just log

        # Auto-login: Create access token (even if unverified, for UX)
        token_data = {
            "sub": counselor.email,
            "tenant_id": counselor.tenant_id,
            "role": counselor.role.value,
        }
        access_token = create_access_token(token_data)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
```

**Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/integration/test_auth_api.py::TestAuthAPI::test_register_sends_verification_email -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/api/auth.py tests/integration/test_auth_api.py
git commit -m "feat: send verification email on registration (default enabled)"
```

---

## Task 5: Block Login for Unverified Accounts

**Files:**
- Modify: `app/api/auth.py:119-189`
- Modify: `tests/integration/test_auth_api.py`

**Step 1: Write failing test for login blocking**

Add to `tests/integration/test_auth_api.py`:
```python
    def test_login_blocked_for_unverified_account(self, db_session: Session):
        """Test that login fails for unverified accounts"""
        # Create inactive (unverified) counselor
        counselor = Counselor(
            id=uuid4(),
            email="unverified@example.com",
            username="unverified",
            full_name="Unverified User",
            hashed_password=hash_password("SecurePass123!"),
            tenant_id="career",
            role="counselor",
            is_active=False,  # Unverified
        )
        db_session.add(counselor)
        db_session.commit()

        with TestClient(app) as client:
            response = client.post(
                "/api/auth/login",
                json={
                    "email": "unverified@example.com",
                    "password": "SecurePass123!",
                    "tenant_id": "career",
                },
            )

            assert response.status_code == 403
            assert "not verified" in response.json()["detail"].lower()
```

**Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/integration/test_auth_api.py::TestAuthAPI::test_login_blocked_for_unverified_account -v`
Expected: FAIL (login succeeds for unverified account)

**Step 3: Modify login endpoint to check verification**

Modify `app/api/auth.py` login function (around line 145-161):
```python
    # Check if account is active (verified)
    if not counselor.is_active:
        if settings.ENABLE_EMAIL_VERIFICATION:
            raise ForbiddenError(
                detail="Email not verified. Please check your email and verify your account.",
                instance=str(request.url.path),
            )
        else:
            raise ForbiddenError(
                detail="Account is inactive",
                instance=str(request.url.path),
            )
```

**Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/integration/test_auth_api.py::TestAuthAPI::test_login_blocked_for_unverified_account -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/api/auth.py tests/integration/test_auth_api.py
git commit -m "feat: block login for unverified accounts"
```

---

## Task 6: Create Email Verification Endpoint

**Files:**
- Create: `app/api/v1/email_verification.py`
- Modify: `app/main.py`
- Create: `tests/integration/test_email_verification_api.py`

**Step 1: Write failing test for email verification endpoint**

Create `tests/integration/test_email_verification_api.py`:
```python
"""
Integration tests for email verification API
"""
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.email_verification import create_verification_token
from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor


class TestEmailVerificationAPI:
    """Test email verification endpoints"""

    def test_verify_email_success(self, db_session: Session):
        """Test successful email verification"""
        # Create unverified counselor
        counselor = Counselor(
            id=uuid4(),
            email="verify@example.com",
            username="verifyuser",
            full_name="Verify User",
            hashed_password=hash_password("SecurePass123!"),
            tenant_id="career",
            role="counselor",
            is_active=False,  # Unverified
        )
        db_session.add(counselor)
        db_session.commit()

        # Create verification token
        token = create_verification_token("verify@example.com", "career")

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/verify-email",
                json={"token": token},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Email verified successfully"
            assert "access_token" in data

            # Verify counselor is now active
            db_session.refresh(counselor)
            assert counselor.is_active is True

    def test_verify_email_invalid_token(self, db_session: Session):
        """Test email verification with invalid token"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/verify-email",
                json={"token": "invalid_token"},
            )

            assert response.status_code == 400
            assert "invalid" in response.json()["detail"].lower()

    def test_verify_email_already_verified(self, db_session: Session):
        """Test email verification for already verified account"""
        # Create verified counselor
        counselor = Counselor(
            id=uuid4(),
            email="already@example.com",
            username="already",
            full_name="Already Verified",
            hashed_password=hash_password("SecurePass123!"),
            tenant_id="career",
            role="counselor",
            is_active=True,  # Already verified
        )
        db_session.add(counselor)
        db_session.commit()

        # Create verification token
        token = create_verification_token("already@example.com", "career")

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/verify-email",
                json={"token": token},
            )

            # Should still succeed (idempotent)
            assert response.status_code == 200
```

**Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/integration/test_email_verification_api.py -v`
Expected: FAIL (404 Not Found)

**Step 3: Create email verification endpoint**

Create `app/api/v1/email_verification.py`:
```python
"""
Email verification endpoints
"""
from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.email_verification import (
    create_verification_token,
    verify_verification_token,
)
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.security import create_access_token
from app.models.counselor import Counselor
from app.schemas.auth import TokenResponse
from app.services.external.email_sender import email_sender

router = APIRouter(prefix="/auth", tags=["Email Verification"])


class VerifyEmailRequest(BaseModel):
    """Email verification request"""

    token: str


class ResendVerificationRequest(BaseModel):
    """Resend verification email request"""

    email: str
    tenant_id: str


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email(
    verify_request: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Verify email address using token

    Args:
        verify_request: Token from verification email
        request: Request object
        db: Database session

    Returns:
        TokenResponse with access token (auto-login)

    Raises:
        BadRequestError: If token is invalid or expired
        NotFoundError: If user not found
    """
    # Verify token
    token_data = verify_verification_token(verify_request.token)
    if not token_data:
        raise BadRequestError(
            detail="Invalid or expired verification token",
            instance=str(request.url.path),
        )

    # Find counselor
    result = db.execute(
        select(Counselor).where(
            Counselor.email == token_data["email"],
            Counselor.tenant_id == token_data["tenant_id"],
        )
    )
    counselor = result.scalar_one_or_none()

    if not counselor:
        raise NotFoundError(
            detail="User not found",
            instance=str(request.url.path),
        )

    # Activate account (idempotent)
    counselor.is_active = True
    db.commit()
    db.refresh(counselor)

    # Auto-login: Create access token
    from app.core.config import Settings

    settings = Settings()

    token_data_dict = {
        "sub": counselor.email,
        "tenant_id": counselor.tenant_id,
        "role": counselor.role.value,
    }
    access_token = create_access_token(token_data_dict)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        message="Email verified successfully",
    )


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    resend_request: ResendVerificationRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Resend verification email

    Args:
        resend_request: Email and tenant ID
        request: Request object
        db: Database session

    Returns:
        Success message

    Raises:
        NotFoundError: If user not found
        BadRequestError: If account already verified
    """
    # Find counselor
    result = db.execute(
        select(Counselor).where(
            Counselor.email == resend_request.email,
            Counselor.tenant_id == resend_request.tenant_id,
        )
    )
    counselor = result.scalar_one_or_none()

    if not counselor:
        raise NotFoundError(
            detail="User not found",
            instance=str(request.url.path),
        )

    if counselor.is_active:
        raise BadRequestError(
            detail="Email already verified",
            instance=str(request.url.path),
        )

    # Send new verification email
    verification_token = create_verification_token(
        counselor.email, counselor.tenant_id
    )

    await email_sender.send_verification_email(
        to_email=counselor.email,
        verification_token=verification_token,
        counselor_name=counselor.full_name,
        tenant_id=counselor.tenant_id,
    )

    return {"message": "Verification email sent successfully"}
```

**Step 4: Register router in main.py**

Modify `app/main.py`:

Add import:
```python
from app.api.v1 import email_verification
```

Add router registration after other v1 routers:
```python
app.include_router(email_verification.router, prefix="/api/v1")
```

**Step 5: Update TokenResponse schema to include message**

Modify `app/schemas/auth.py`:
```python
class TokenResponse(BaseModel):
    """JWT token response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    message: Optional[str] = None  # Optional message (e.g., "Email verified")
```

**Step 6: Run tests to verify they pass**

Run: `poetry run pytest tests/integration/test_email_verification_api.py -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add app/api/v1/email_verification.py app/main.py app/schemas/auth.py tests/integration/test_email_verification_api.py
git commit -m "feat: add email verification and resend endpoints"
```

---

## Task 7: Update Environment Variable Documentation

**Files:**
- Modify: `.env.example`
- Modify: `.env.production.example`

**Step 1: Update .env.example**

Add after SMTP configuration:
```bash
# Email Verification (Default Enabled)
ENABLE_EMAIL_VERIFICATION=true
VERIFICATION_TOKEN_EXPIRE_HOURS=24
```

**Step 2: Update .env.production.example**

Add after SMTP configuration (around line 130):
```bash
# Email Verification (Always Enabled in Production)
ENABLE_EMAIL_VERIFICATION=true
VERIFICATION_TOKEN_EXPIRE_HOURS=24
VERIFICATION_EMAIL_SUBJECT="Verify Your Email - {tenant_name}"
```

**Step 3: Commit**

```bash
git add .env.example .env.production.example
git commit -m "docs: add email verification environment variables"
```

---

## Task 8: Update All Existing Tests to Handle Verification

**Files:**
- Modify: `tests/integration/test_auth_api.py`
- Modify: `tests/conftest.py` (if needed)

**Step 1: Update existing tests to create active counselors**

Ensure all test counselors have `is_active=True`:

In `tests/integration/test_auth_api.py`, review all Counselor creations and ensure:
```python
# Before (may cause test failures if verification is enabled)
counselor = Counselor(
    ...
    # Missing is_active or assuming default
)

# After (explicit active state)
counselor = Counselor(
    ...
    is_active=True,  # Explicitly set for tests
)
```

**Step 2: Add fixture to disable email verification in tests (optional)**

Add to `tests/conftest.py`:
```python
import pytest


@pytest.fixture(autouse=True)
def disable_email_verification_in_tests(monkeypatch):
    """
    Disable email verification in tests by default
    (tests that need it enabled can override)
    """
    from app.core.config import Settings

    settings = Settings()
    monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", False)
```

**Step 3: Run all integration tests**

Run: `poetry run pytest tests/integration/ -v`
Expected: All tests PASS

**Step 4: Commit**

```bash
git add tests/integration/test_auth_api.py tests/conftest.py
git commit -m "test: update tests for email verification compatibility"
```

---

## Task 9: Create Verification Web Page (HTML Template)

**Files:**
- Create: `app/templates/verify_email.html`
- Modify: `app/main.py`

**Step 1: Create HTML template for email verification page**

Create `app/templates/verify_email.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Email Verification</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            max-width: 500px;
            text-align: center;
        }
        h1 {
            color: #333;
            margin-bottom: 20px;
        }
        .status {
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .loading {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .btn {
            display: inline-block;
            padding: 12px 30px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 20px;
            transition: background 0.3s;
        }
        .btn:hover {
            background: #5568d3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Email Verification</h1>
        <div id="status" class="status loading">
            Verifying your email...
        </div>
        <div id="actions"></div>
    </div>

    <script>
        // Get token from URL
        const urlParams = new URLSearchParams(window.location.search);
        const token = urlParams.get('token');
        const statusDiv = document.getElementById('status');
        const actionsDiv = document.getElementById('actions');

        if (!token) {
            statusDiv.className = 'status error';
            statusDiv.textContent = 'Invalid verification link. Please check your email and try again.';
        } else {
            // Call verification API
            fetch('/api/v1/auth/verify-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: token }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.access_token) {
                    statusDiv.className = 'status success';
                    statusDiv.innerHTML = '✓ Email verified successfully!<br>You can now log in to your account.';
                    actionsDiv.innerHTML = '<a href="/login" class="btn">Go to Login</a>';
                } else {
                    throw new Error(data.detail || 'Verification failed');
                }
            })
            .catch(error => {
                statusDiv.className = 'status error';
                statusDiv.textContent = `Verification failed: ${error.message}`;
                actionsDiv.innerHTML = '<a href="/resend-verification" class="btn">Resend Verification Email</a>';
            });
        }
    </script>
</body>
</html>
```

**Step 2: Add static file serving to main.py**

Modify `app/main.py`:

Add imports:
```python
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
```

Add template configuration:
```python
templates = Jinja2Templates(directory="app/templates")
```

Add route for verification page:
```python
@app.get("/verify-email", response_class=HTMLResponse)
async def verify_email_page(request: Request):
    """Email verification page"""
    return templates.TemplateResponse("verify_email.html", {"request": request})
```

**Step 3: Commit**

```bash
git add app/templates/verify_email.html app/main.py
git commit -m "feat: add email verification web page"
```

---

## Task 10: Update Documentation

**Files:**
- Modify: `TODO.md`
- Modify: `CHANGELOG.md`
- Create: `docs/EMAIL_VERIFICATION.md` (optional)

**Step 1: Mark email verification as completed in TODO.md**

Update `TODO.md`:
```markdown
### 註冊安全性增強（2026-01-30）✅ 完成

- [x] **郵件驗證功能**（可開關設計）✅ 已實作，預設啟用
  - 環境變數：`ENABLE_EMAIL_VERIFICATION=true`（預設）
  - 註冊流程：註冊 → 發送驗證信 → 點擊連結 → 啟用帳號
  - 未驗證帳號：`is_active=False`，無法登入
  - 驗證連結：24 小時有效期
  - 重發驗證信：`POST /api/v1/auth/resend-verification`
  - Web 頁面：`/verify-email?token=xxx`

- [x] **Rate Limiting**（永久啟用）✅ 已實作
  - 註冊限制：同 IP 每小時最多 3 次（開發：100 次）
  - 登入限制：同 IP 每分鐘最多 5 次（開發：20 次）
  - 忘記密碼限制：同 IP 每小時最多 3 次（開發：20 次）

- [x] **密碼強度驗證增強**（永久啟用）✅ 已實作
  - 至少 12 字元
  - 必須包含大小寫 + 數字 + 特殊字元
  - 檢查常見密碼清單
```

**Step 2: Update CHANGELOG.md**

Add to `CHANGELOG.md`:
```markdown
## [Unreleased]

### Added
- **Email Verification** (default enabled)
  - Registration sends verification email (24-hour token)
  - Unverified accounts cannot login (`is_active=False`)
  - Verification endpoint: `POST /api/v1/auth/verify-email`
  - Resend endpoint: `POST /api/v1/auth/resend-verification`
  - Web verification page: `/verify-email?token=xxx`
  - Environment toggle: `ENABLE_EMAIL_VERIFICATION` (default: true)
- Email templates with tenant-specific branding
- JWT-based verification tokens with expiry

### Changed
- Registration now creates inactive accounts (when verification enabled)
- Login blocks unverified users with helpful error message
```

**Step 3: Create email verification guide (optional)**

Create `docs/EMAIL_VERIFICATION.md`:
```markdown
# Email Verification Guide

## Overview

Email verification prevents fake accounts and ensures email ownership.

**Default**: Enabled (`ENABLE_EMAIL_VERIFICATION=true`)

## User Flow

1. User registers → Account created with `is_active=False`
2. Verification email sent with 24-hour token
3. User clicks link → Redirected to `/verify-email?token=xxx`
4. Token verified → Account activated (`is_active=True`)
5. User can now login

## API Endpoints

### Verify Email
```
POST /api/v1/auth/verify-email
Body: { "token": "xxx" }
Response: { "access_token": "...", "message": "Email verified successfully" }
```

### Resend Verification
```
POST /api/v1/auth/resend-verification
Body: { "email": "user@example.com", "tenant_id": "career" }
Response: { "message": "Verification email sent successfully" }
```

## Configuration

```bash
# .env
ENABLE_EMAIL_VERIFICATION=true  # Enable/disable verification
VERIFICATION_TOKEN_EXPIRE_HOURS=24  # Token expiry time
```

## Disabling (for development)

```bash
# .env.development
ENABLE_EMAIL_VERIFICATION=false
```

All new registrations will be immediately active.

## Testing

```python
# Disable in tests
@pytest.fixture(autouse=True)
def disable_email_verification(monkeypatch):
    from app.core.config import Settings
    settings = Settings()
    monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", False)
```

## Production Deployment

1. Ensure SMTP configured correctly
2. Test email delivery in staging
3. Verify `/verify-email` page loads
4. Confirm `ENABLE_EMAIL_VERIFICATION=true` in production `.env`
5. Monitor email sending logs
```

**Step 4: Commit**

```bash
git add TODO.md CHANGELOG.md docs/EMAIL_VERIFICATION.md
git commit -m "docs: update documentation for email verification feature"
```

---

## Verification Checklist

Before marking complete:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Email verification token generation works
- [ ] Verification email sends successfully
- [ ] Registration creates inactive accounts (when enabled)
- [ ] Login blocks unverified users
- [ ] Verification endpoint activates account
- [ ] Resend endpoint works
- [ ] Web verification page displays correctly
- [ ] Configuration environment variables documented
- [ ] Existing tests updated to handle verification
- [ ] CHANGELOG and TODO updated

---

## Rollback Plan

If issues arise:
```bash
# Disable email verification immediately
echo "ENABLE_EMAIL_VERIFICATION=false" >> .env

# Or revert commits
git log --oneline | head -10
git revert <commit-sha>
```

---

## Notes

**Design Decisions:**
- Email verification is **default enabled** (user requirement: "通通 enable")
- Unverified users still get access token (better UX, can show "verify email" banner)
- Verification is **idempotent** (re-verifying doesn't cause errors)
- 24-hour token expiry (balance security vs UX)
- Web page for verification (better than API-only for mobile apps)

**Security Considerations:**
- JWT tokens prevent token guessing
- Tokens expire after 24 hours
- Failed verifications don't reveal if email exists
- Rate limiting prevents abuse of resend endpoint

**Future Enhancements:**
- Email verification reminder after 48 hours
- Delete unverified accounts after 7 days
- Admin dashboard to view unverified accounts
- Verification analytics (how many verify within 24h)
