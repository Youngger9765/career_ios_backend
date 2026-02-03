# Monthly Usage Limit with Billing Modes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add monthly usage limits for subscription users while maintaining backward compatibility with prepaid users.

**Architecture:** Extend Counselor model with billing_mode field (prepaid/subscription) and subscription-specific usage tracking. Add middleware to check limits before session creation. Support both billing modes with minimal code changes.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, Alembic, pytest

---

## Background

**Current State:**
- System has `available_credits` for prepaid billing
- System has `subscription_expires_at` field (unused)
- No usage limits for subscription users

**New Requirements:**
- Support two billing modes: `prepaid` and `subscription`
- Subscription users: 6 hours/month limit (360 minutes)
- Prepaid users: continue using credit balance
- Rolling 30-day usage period
- HTTP 429 when subscription limit exceeded

**Cost Analysis:**
- ElevenLabs STT: $0.40/hour
- Other services: $0.08/hour
- Total: $0.48/hour = NT$14.53/hour
- 6 hours/month = NT$87 cost ≈ NT$100 monthly fee

---

## Task 1: Database Migration - Add Billing Mode Fields

**Files:**
- Create: `alembic/versions/XXXX_add_billing_mode_and_usage_tracking.py`
- Modify: `app/models/counselor.py`

**Step 1: Write the failing test**

Create: `tests/unit/test_counselor_billing_fields.py`

```python
"""Test counselor billing mode fields"""
import pytest
from datetime import datetime, timezone
from app.models.counselor import Counselor, BillingMode


def test_counselor_default_billing_mode_is_prepaid():
    """New counselors should default to prepaid mode"""
    counselor = Counselor(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        tenant_id="test",
        role="counselor"
    )
    assert counselor.billing_mode == BillingMode.PREPAID


def test_counselor_subscription_fields_exist():
    """Counselor should have subscription usage tracking fields"""
    counselor = Counselor(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        tenant_id="test",
        role="counselor",
        billing_mode=BillingMode.SUBSCRIPTION
    )
    assert hasattr(counselor, 'monthly_usage_limit_minutes')
    assert hasattr(counselor, 'monthly_minutes_used')
    assert hasattr(counselor, 'usage_period_start')


def test_subscription_default_limit_is_360_minutes():
    """Subscription users should default to 360 minute limit"""
    counselor = Counselor(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        tenant_id="test",
        role="counselor",
        billing_mode=BillingMode.SUBSCRIPTION
    )
    assert counselor.monthly_usage_limit_minutes == 360
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/unit/test_counselor_billing_fields.py -v
```

Expected: FAIL with "AttributeError: 'Counselor' object has no attribute 'billing_mode'"

**Step 3: Update Counselor model**

Modify: `app/models/counselor.py`

Add after line 1 (imports):
```python
import enum

class BillingMode(str, enum.Enum):
    """Billing mode for counselor"""
    PREPAID = "prepaid"
    SUBSCRIPTION = "subscription"
```

Add after line 54 (after subscription_expires_at):
```python
    # Billing mode (prepaid vs subscription)
    billing_mode = Column(
        SQLEnum(BillingMode),
        default=BillingMode.PREPAID,
        nullable=False,
        index=True,
        comment="Billing mode: prepaid (credit-based) or subscription (time-limited)"
    )

    # Subscription-specific usage tracking fields
    monthly_usage_limit_minutes = Column(
        Integer,
        default=360,
        nullable=True,
        comment="Monthly usage limit in minutes (subscription mode only), 6 hours = 360 min"
    )
    monthly_minutes_used = Column(
        Integer,
        default=0,
        nullable=True,
        comment="Minutes used in current billing period (subscription mode only)"
    )
    usage_period_start = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Start of current 30-day usage period (subscription mode only)"
    )
```

**Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/unit/test_counselor_billing_fields.py -v
```

Expected: PASS (3 tests)

**Step 5: Create Alembic migration**

```bash
poetry run alembic revision -m "add billing mode and subscription usage tracking"
```

Edit the generated migration file:

```python
"""add billing mode and subscription usage tracking

Revision ID: XXXX
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create enum type
    billing_mode_enum = postgresql.ENUM('prepaid', 'subscription', name='billingmode')
    billing_mode_enum.create(op.get_bind())

    # Add billing_mode column (default to prepaid for existing users)
    op.add_column('counselors', sa.Column(
        'billing_mode',
        sa.Enum('prepaid', 'subscription', name='billingmode'),
        nullable=False,
        server_default='prepaid',
        comment='Billing mode: prepaid (credit-based) or subscription (time-limited)'
    ))
    op.create_index('ix_counselors_billing_mode', 'counselors', ['billing_mode'])

    # Add subscription usage tracking columns
    op.add_column('counselors', sa.Column(
        'monthly_usage_limit_minutes',
        sa.Integer(),
        nullable=True,
        server_default='360',
        comment='Monthly usage limit in minutes (subscription mode only)'
    ))
    op.add_column('counselors', sa.Column(
        'monthly_minutes_used',
        sa.Integer(),
        nullable=True,
        server_default='0',
        comment='Minutes used in current billing period (subscription mode only)'
    ))
    op.add_column('counselors', sa.Column(
        'usage_period_start',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='Start of current 30-day usage period (subscription mode only)'
    ))

def downgrade():
    op.drop_index('ix_counselors_billing_mode', 'counselors')
    op.drop_column('counselors', 'usage_period_start')
    op.drop_column('counselors', 'monthly_minutes_used')
    op.drop_column('counselors', 'monthly_usage_limit_minutes')
    op.drop_column('counselors', 'billing_mode')

    billing_mode_enum = postgresql.ENUM('prepaid', 'subscription', name='billingmode')
    billing_mode_enum.drop(op.get_bind())
```

**Step 6: Run migration**

```bash
poetry run alembic upgrade head
```

Expected: Migration applies successfully

**Step 7: Commit**

```bash
git add app/models/counselor.py tests/unit/test_counselor_billing_fields.py alembic/versions/*_add_billing_mode*.py
git commit -m "feat: add billing mode and subscription usage tracking to Counselor model

Add support for two billing modes:
- prepaid: existing credit-based billing
- subscription: new time-limited billing with 360 min/month limit

New fields:
- billing_mode (enum): prepaid | subscription
- monthly_usage_limit_minutes: 360 (6 hours)
- monthly_minutes_used: tracks current period usage
- usage_period_start: rolling 30-day period start

All existing users default to prepaid mode (backward compatible).

Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>"
```

---

## Task 2: Usage Tracking Service

**Files:**
- Create: `app/services/billing/usage_tracker.py`
- Create: `tests/unit/test_usage_tracker.py`

**Step 1: Write the failing test**

Create: `tests/unit/test_usage_tracker.py`

```python
"""Test usage tracking service"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from app.models.counselor import Counselor, BillingMode
from app.services.billing.usage_tracker import UsageTracker


@pytest.fixture
def subscription_counselor():
    """Create a subscription counselor"""
    return Counselor(
        id=uuid4(),
        email="sub@example.com",
        username="subcounselor",
        hashed_password="hashed",
        tenant_id="test",
        role="counselor",
        billing_mode=BillingMode.SUBSCRIPTION,
        monthly_usage_limit_minutes=360,
        monthly_minutes_used=0,
        usage_period_start=datetime.now(timezone.utc)
    )


def test_reset_usage_period_if_expired(subscription_counselor):
    """Should reset usage when period expires (30 days)"""
    # Set period start to 31 days ago
    subscription_counselor.usage_period_start = datetime.now(timezone.utc) - timedelta(days=31)
    subscription_counselor.monthly_minutes_used = 200

    tracker = UsageTracker()
    tracker.reset_if_period_expired(subscription_counselor)

    assert subscription_counselor.monthly_minutes_used == 0
    assert subscription_counselor.usage_period_start > datetime.now(timezone.utc) - timedelta(minutes=1)


def test_no_reset_if_period_active(subscription_counselor):
    """Should not reset usage if period still active"""
    original_start = datetime.now(timezone.utc) - timedelta(days=15)
    subscription_counselor.usage_period_start = original_start
    subscription_counselor.monthly_minutes_used = 100

    tracker = UsageTracker()
    tracker.reset_if_period_expired(subscription_counselor)

    assert subscription_counselor.monthly_minutes_used == 100
    assert subscription_counselor.usage_period_start == original_start


def test_check_limit_not_exceeded(subscription_counselor):
    """Should return True if under limit"""
    subscription_counselor.monthly_minutes_used = 300
    subscription_counselor.monthly_usage_limit_minutes = 360

    tracker = UsageTracker()
    result = tracker.is_limit_exceeded(subscription_counselor)

    assert result is False


def test_check_limit_exceeded(subscription_counselor):
    """Should return True if at or over limit"""
    subscription_counselor.monthly_minutes_used = 360
    subscription_counselor.monthly_usage_limit_minutes = 360

    tracker = UsageTracker()
    result = tracker.is_limit_exceeded(subscription_counselor)

    assert result is True


def test_get_usage_stats(subscription_counselor):
    """Should return usage statistics"""
    subscription_counselor.monthly_minutes_used = 120
    subscription_counselor.monthly_usage_limit_minutes = 360
    subscription_counselor.usage_period_start = datetime.now(timezone.utc) - timedelta(days=10)

    tracker = UsageTracker()
    stats = tracker.get_usage_stats(subscription_counselor)

    assert stats['monthly_limit_minutes'] == 360
    assert stats['monthly_used_minutes'] == 120
    assert stats['monthly_remaining_minutes'] == 240
    assert stats['usage_percentage'] == pytest.approx(33.33, rel=0.01)
    assert stats['is_limit_reached'] is False
    assert 'usage_period_start' in stats
    assert 'usage_period_end' in stats
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/unit/test_usage_tracker.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.services.billing'"

**Step 3: Implement UsageTracker service**

Create: `app/services/billing/__init__.py` (empty file)

Create: `app/services/billing/usage_tracker.py`

```python
"""Usage tracking service for subscription billing"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from app.models.counselor import Counselor, BillingMode


class UsageTracker:
    """Track and manage subscription usage limits"""

    PERIOD_DAYS = 30  # Rolling 30-day period

    def reset_if_period_expired(self, counselor: Counselor) -> None:
        """Reset usage if 30-day period has expired"""
        if counselor.billing_mode != BillingMode.SUBSCRIPTION:
            return

        if not counselor.usage_period_start:
            # First time - initialize period
            counselor.usage_period_start = datetime.now(timezone.utc)
            counselor.monthly_minutes_used = 0
            return

        # Check if period expired (30 days)
        period_end = counselor.usage_period_start + timedelta(days=self.PERIOD_DAYS)
        now = datetime.now(timezone.utc)

        if now >= period_end:
            # Reset for new period
            counselor.usage_period_start = now
            counselor.monthly_minutes_used = 0

    def is_limit_exceeded(self, counselor: Counselor) -> bool:
        """Check if counselor has exceeded monthly usage limit"""
        if counselor.billing_mode != BillingMode.SUBSCRIPTION:
            return False

        if not counselor.monthly_usage_limit_minutes:
            return False  # No limit set

        return counselor.monthly_minutes_used >= counselor.monthly_usage_limit_minutes

    def get_usage_stats(self, counselor: Counselor) -> Dict[str, Any]:
        """Get usage statistics for counselor"""
        if counselor.billing_mode != BillingMode.SUBSCRIPTION:
            return {
                'billing_mode': 'prepaid',
                'available_credits': counselor.available_credits
            }

        limit = counselor.monthly_usage_limit_minutes or 0
        used = counselor.monthly_minutes_used or 0
        remaining = max(0, limit - used)
        percentage = (used / limit * 100) if limit > 0 else 0

        period_start = counselor.usage_period_start or datetime.now(timezone.utc)
        period_end = period_start + timedelta(days=self.PERIOD_DAYS)

        return {
            'billing_mode': 'subscription',
            'monthly_limit_minutes': limit,
            'monthly_used_minutes': used,
            'monthly_remaining_minutes': remaining,
            'usage_percentage': round(percentage, 2),
            'is_limit_reached': used >= limit,
            'usage_period_start': period_start,
            'usage_period_end': period_end
        }
```

**Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/unit/test_usage_tracker.py -v
```

Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add app/services/billing/ tests/unit/test_usage_tracker.py
git commit -m "feat: add usage tracking service for subscription billing

Implements UsageTracker service to manage monthly usage limits:
- reset_if_period_expired(): auto-reset after 30 days
- is_limit_exceeded(): check if user hit monthly limit
- get_usage_stats(): return usage statistics for API

Supports rolling 30-day periods and proper limit checking.

Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>"
```

---

## Task 3: Middleware for Usage Limit Enforcement

**Files:**
- Create: `app/middleware/usage_limit.py`
- Create: `tests/unit/test_usage_limit_middleware.py`
- Modify: `app/api/sessions.py` (add usage check before session creation)

**Step 1: Write the failing test**

Create: `tests/unit/test_usage_limit_middleware.py`

```python
"""Test usage limit middleware"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import HTTPException
from app.models.counselor import Counselor, BillingMode
from app.middleware.usage_limit import check_usage_limit


@pytest.fixture
def prepaid_counselor():
    """Create prepaid counselor"""
    return Counselor(
        id=uuid4(),
        email="prepaid@example.com",
        username="prepaid",
        hashed_password="hashed",
        tenant_id="test",
        role="counselor",
        billing_mode=BillingMode.PREPAID,
        available_credits=100.0
    )


@pytest.fixture
def subscription_counselor():
    """Create subscription counselor"""
    return Counselor(
        id=uuid4(),
        email="sub@example.com",
        username="sub",
        hashed_password="hashed",
        tenant_id="test",
        role="counselor",
        billing_mode=BillingMode.SUBSCRIPTION,
        monthly_usage_limit_minutes=360,
        monthly_minutes_used=0,
        usage_period_start=datetime.now(timezone.utc),
        subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )


def test_prepaid_with_credits_allowed(prepaid_counselor):
    """Prepaid user with credits should be allowed"""
    check_usage_limit(prepaid_counselor)  # Should not raise


def test_prepaid_no_credits_blocked(prepaid_counselor):
    """Prepaid user without credits should be blocked"""
    prepaid_counselor.available_credits = 0

    with pytest.raises(HTTPException) as exc:
        check_usage_limit(prepaid_counselor)

    assert exc.value.status_code == 402
    assert "INSUFFICIENT_CREDITS" in str(exc.value.detail)


def test_subscription_under_limit_allowed(subscription_counselor):
    """Subscription user under limit should be allowed"""
    subscription_counselor.monthly_minutes_used = 100
    check_usage_limit(subscription_counselor)  # Should not raise


def test_subscription_at_limit_blocked(subscription_counselor):
    """Subscription user at limit should be blocked"""
    subscription_counselor.monthly_minutes_used = 360

    with pytest.raises(HTTPException) as exc:
        check_usage_limit(subscription_counselor)

    assert exc.value.status_code == 429
    assert "MONTHLY_USAGE_LIMIT_EXCEEDED" in str(exc.value.detail)


def test_subscription_expired_blocked(subscription_counselor):
    """Subscription user with expired subscription blocked"""
    subscription_counselor.subscription_expires_at = datetime.now(timezone.utc) - timedelta(days=1)

    with pytest.raises(HTTPException) as exc:
        check_usage_limit(subscription_counselor)

    assert exc.value.status_code == 402
    assert "SUBSCRIPTION_EXPIRED" in str(exc.value.detail)


def test_subscription_auto_reset_period(subscription_counselor):
    """Should auto-reset usage after 30 days"""
    subscription_counselor.usage_period_start = datetime.now(timezone.utc) - timedelta(days=31)
    subscription_counselor.monthly_minutes_used = 300

    check_usage_limit(subscription_counselor)  # Should not raise

    # Usage should be reset
    assert subscription_counselor.monthly_minutes_used == 0
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/unit/test_usage_limit_middleware.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'app.middleware.usage_limit'"

**Step 3: Implement usage limit middleware**

Create: `app/middleware/usage_limit.py`

```python
"""Usage limit enforcement middleware"""
from datetime import datetime, timezone
from fastapi import HTTPException
from app.models.counselor import Counselor, BillingMode
from app.services.billing.usage_tracker import UsageTracker


def check_usage_limit(counselor: Counselor) -> None:
    """
    Check if counselor can create a new session based on billing mode.

    Raises:
        HTTPException 402: Prepaid user has no credits or subscription expired
        HTTPException 429: Subscription user exceeded monthly limit
    """
    tracker = UsageTracker()

    if counselor.billing_mode == BillingMode.PREPAID:
        # Prepaid mode: check credits
        if counselor.available_credits <= 0:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "INSUFFICIENT_CREDITS",
                    "message": "Credits 不足，請儲值後再使用。",
                    "available_credits": counselor.available_credits
                }
            )

    elif counselor.billing_mode == BillingMode.SUBSCRIPTION:
        # Subscription mode: check subscription validity
        now = datetime.now(timezone.utc)
        if counselor.subscription_expires_at and counselor.subscription_expires_at < now:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "SUBSCRIPTION_EXPIRED",
                    "message": "訂閱已過期，請續訂後再使用。",
                    "subscription_expires_at": counselor.subscription_expires_at
                }
            )

        # Auto-reset usage if period expired
        tracker.reset_if_period_expired(counselor)

        # Check monthly usage limit
        if tracker.is_limit_exceeded(counselor):
            stats = tracker.get_usage_stats(counselor)
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "MONTHLY_USAGE_LIMIT_EXCEEDED",
                    "message": f"您本月的使用時間已達上限（{stats['monthly_limit_minutes']}分鐘），請下個週期再使用。",
                    "monthly_limit_minutes": stats['monthly_limit_minutes'],
                    "monthly_used_minutes": stats['monthly_used_minutes'],
                    "reset_date": stats['usage_period_end']
                }
            )
```

**Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/unit/test_usage_limit_middleware.py -v
```

Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add app/middleware/usage_limit.py tests/unit/test_usage_limit_middleware.py
git commit -m "feat: add usage limit enforcement middleware

Implements check_usage_limit() middleware:
- Prepaid mode: checks available_credits > 0
- Subscription mode: checks subscription validity + monthly limit
- Auto-resets usage after 30-day period
- Returns proper HTTP status codes (402/429) with error details

Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>"
```

---

## Task 4: Usage Stats API Endpoint

**Files:**
- Create: `app/api/v1/usage.py`
- Create: `app/schemas/usage.py`
- Create: `tests/integration/test_usage_api.py`
- Modify: `app/main.py` (register router)

**Step 1: Write the failing test**

Create: `tests/integration/test_usage_api.py`

```python
"""Test usage API endpoints"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.counselor import Counselor, BillingMode
from app.core.security import hash_password, create_access_token


@pytest.fixture
def subscription_counselor(db_session: Session):
    """Create subscription counselor for testing"""
    counselor = Counselor(
        id=uuid4(),
        email="usage-test@example.com",
        username="usagetest",
        hashed_password=hash_password("ValidP@ssw0rd123"),
        tenant_id="test_tenant",
        role="counselor",
        is_active=True,
        billing_mode=BillingMode.SUBSCRIPTION,
        monthly_usage_limit_minutes=360,
        monthly_minutes_used=120,
        usage_period_start=datetime.now(timezone.utc) - timedelta(days=10),
        subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=20)
    )
    db_session.add(counselor)
    db_session.commit()
    return counselor


@pytest.fixture
def auth_headers(subscription_counselor):
    """Create auth headers"""
    token = create_access_token({"sub": str(subscription_counselor.id)})
    return {"Authorization": f"Bearer {token}"}


def test_get_usage_stats_subscription(auth_headers):
    """Should return subscription usage stats"""
    with TestClient(app) as client:
        response = client.get("/api/v1/usage/stats", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data['billing_mode'] == 'subscription'
    assert data['monthly_limit_minutes'] == 360
    assert data['monthly_used_minutes'] == 120
    assert data['monthly_remaining_minutes'] == 240
    assert data['usage_percentage'] == pytest.approx(33.33, rel=0.1)
    assert data['is_limit_reached'] is False
    assert 'usage_period_start' in data
    assert 'usage_period_end' in data


def test_get_usage_stats_unauthorized():
    """Should return 401 without auth"""
    with TestClient(app) as client:
        response = client.get("/api/v1/usage/stats")

    assert response.status_code == 401
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/integration/test_usage_api.py -v
```

Expected: FAIL with "404 Not Found" (route doesn't exist)

**Step 3: Create usage schemas**

Create: `app/schemas/usage.py`

```python
"""Usage statistics schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UsageStatsResponse(BaseModel):
    """Usage statistics response"""

    billing_mode: str = Field(..., description="Billing mode: prepaid or subscription")

    # Prepaid fields
    available_credits: Optional[float] = Field(None, description="Available credits (prepaid only)")

    # Subscription fields
    monthly_limit_minutes: Optional[int] = Field(None, description="Monthly usage limit in minutes")
    monthly_used_minutes: Optional[int] = Field(None, description="Minutes used this period")
    monthly_remaining_minutes: Optional[int] = Field(None, description="Minutes remaining this period")
    usage_percentage: Optional[float] = Field(None, description="Usage percentage (0-100)")
    is_limit_reached: Optional[bool] = Field(None, description="Whether monthly limit reached")
    usage_period_start: Optional[datetime] = Field(None, description="Current usage period start")
    usage_period_end: Optional[datetime] = Field(None, description="Current usage period end")

    class Config:
        json_schema_extra = {
            "example": {
                "billing_mode": "subscription",
                "monthly_limit_minutes": 360,
                "monthly_used_minutes": 120,
                "monthly_remaining_minutes": 240,
                "usage_percentage": 33.33,
                "is_limit_reached": False,
                "usage_period_start": "2026-01-21T00:00:00Z",
                "usage_period_end": "2026-02-20T00:00:00Z"
            }
        }
```

**Step 4: Create usage API router**

Create: `app/api/v1/usage.py`

```python
"""Usage statistics API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_counselor
from app.models.counselor import Counselor
from app.schemas.usage import UsageStatsResponse
from app.services.billing.usage_tracker import UsageTracker

router = APIRouter()


@router.get("/stats", response_model=UsageStatsResponse)
def get_usage_stats(
    current_counselor: Counselor = Depends(get_current_counselor),
    db: Session = Depends(get_db)
) -> UsageStatsResponse:
    """
    Get current usage statistics for authenticated counselor.

    Returns different fields based on billing mode:
    - prepaid: available_credits
    - subscription: monthly usage stats
    """
    tracker = UsageTracker()

    # Auto-reset if period expired (update in DB)
    tracker.reset_if_period_expired(current_counselor)
    if current_counselor in db:
        db.commit()

    stats = tracker.get_usage_stats(current_counselor)
    return UsageStatsResponse(**stats)
```

**Step 5: Register router in main.py**

Modify: `app/main.py`

Add import after line with other api imports:
```python
from app.api.v1 import usage
```

Add router registration after other v1 routers:
```python
app.include_router(usage.router, prefix="/api/v1/usage", tags=["usage"])
```

**Step 6: Run test to verify it passes**

```bash
poetry run pytest tests/integration/test_usage_api.py -v
```

Expected: PASS (2 tests)

**Step 7: Commit**

```bash
git add app/api/v1/usage.py app/schemas/usage.py tests/integration/test_usage_api.py app/main.py
git commit -m "feat: add usage statistics API endpoint

Add GET /api/v1/usage/stats endpoint:
- Returns usage stats based on billing mode
- Prepaid: shows available_credits
- Subscription: shows monthly usage (limit, used, remaining, %)
- Auto-resets expired usage periods
- Requires authentication

Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>"
```

---

## Task 5: Integrate Usage Check into Session Creation

**Files:**
- Modify: `app/api/sessions.py`
- Create: `tests/integration/test_session_usage_limit.py`

**Step 1: Write the failing test**

Create: `tests/integration/test_session_usage_limit.py`

```python
"""Test session creation with usage limits"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.counselor import Counselor, BillingMode
from app.models.client import Client
from app.models.case import Case
from app.core.security import hash_password, create_access_token


@pytest.fixture
def subscription_counselor_at_limit(db_session: Session):
    """Subscription counselor who reached monthly limit"""
    counselor = Counselor(
        id=uuid4(),
        email="limit-test@example.com",
        username="limituser",
        hashed_password=hash_password("ValidP@ssw0rd123"),
        tenant_id="test_tenant",
        role="counselor",
        is_active=True,
        billing_mode=BillingMode.SUBSCRIPTION,
        monthly_usage_limit_minutes=360,
        monthly_minutes_used=360,  # At limit
        usage_period_start=datetime.now(timezone.utc),
        subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db_session.add(counselor)
    db_session.commit()
    return counselor


@pytest.fixture
def test_case(db_session: Session, subscription_counselor_at_limit):
    """Create test case"""
    client = Client(
        id=uuid4(),
        name="Test Client",
        client_code="TEST001",
        counselor_id=subscription_counselor_at_limit.id,
        tenant_id="test_tenant"
    )
    db_session.add(client)
    db_session.flush()

    case = Case(
        id=uuid4(),
        client_id=client.id,
        counselor_id=subscription_counselor_at_limit.id,
        status="active"
    )
    db_session.add(case)
    db_session.commit()
    return case


def test_session_creation_blocked_at_limit(subscription_counselor_at_limit, test_case):
    """Should block session creation when at monthly limit"""
    token = create_access_token({"sub": str(subscription_counselor_at_limit.id)})
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/sessions",
            headers=headers,
            json={
                "name": "Test Session",
                "case_id": str(test_case.id)
            }
        )

    assert response.status_code == 429
    error = response.json()
    assert error['detail']['code'] == "MONTHLY_USAGE_LIMIT_EXCEEDED"
    assert "monthly_limit_minutes" in error['detail']
    assert error['detail']['monthly_limit_minutes'] == 360
```

**Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/integration/test_session_usage_limit.py -v
```

Expected: FAIL (session creation not blocked, returns 200 instead of 429)

**Step 3: Add usage check to session creation**

Modify: `app/api/sessions.py`

Add import at top:
```python
from app.middleware.usage_limit import check_usage_limit
```

Find the session creation endpoint (usually `@router.post("/")`) and add usage check at the beginning:

```python
@router.post("/", response_model=SessionResponse, status_code=201)
def create_session(
    request: SessionCreateRequest,
    db: Session = Depends(get_db),
    current_counselor: Counselor = Depends(get_current_counselor),
):
    """Create a new session"""
    # Check usage limits BEFORE creating session
    check_usage_limit(current_counselor)

    # ... rest of existing code ...
```

**Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/integration/test_session_usage_limit.py -v
```

Expected: PASS (1 test)

**Step 5: Run all session tests to ensure no regression**

```bash
poetry run pytest tests/integration/ -k session -v
```

Expected: All session-related tests pass

**Step 6: Commit**

```bash
git add app/api/sessions.py tests/integration/test_session_usage_limit.py
git commit -m "feat: enforce usage limits on session creation

Add usage limit check before creating sessions:
- Prepaid users: blocked if credits <= 0
- Subscription users: blocked if monthly limit exceeded
- Auto-resets usage period after 30 days
- Returns HTTP 429 with usage details when limit exceeded

Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>"
```

---

## Task 6: Update Documentation

**Files:**
- Modify: `PRD.md`
- Modify: `CHANGELOG.md`
- Modify: `CHANGELOG_zh-TW.md`
- Update: `TODO.md` (mark Issue #8 as done)

**Step 1: Update PRD.md**

Modify: `PRD.md`

Add to "## API Endpoints" section:

```markdown
### Usage Statistics
- `GET /api/v1/usage/stats` - Get current usage statistics
  - Prepaid: returns available_credits
  - Subscription: returns monthly usage (limit, used, remaining, %)
```

Add to "## Billing System" section (or create if doesn't exist):

```markdown
## Billing System

### Billing Modes

Two billing modes supported:

1. **Prepaid (储值制)**
   - Users buy credits upfront
   - Credits deducted based on usage time
   - Blocked when credits <= 0
   - Existing default mode

2. **Subscription (订阅制)**
   - Monthly fee (NT$100)
   - Usage limit: 6 hours/month (360 minutes)
   - Rolling 30-day period
   - Blocked when limit exceeded (HTTP 429)

### Monthly Usage Limits (Subscription Only)

- Limit: 360 minutes/month (6 hours)
- Cost basis: NT$14.53/hour × 6 hours = ~NT$87
- Period: Rolling 30 days from usage_period_start
- Auto-reset: Usage resets after 30 days
- Enforcement: Checked before session creation
```

**Step 2: Update CHANGELOG.md**

Modify: `CHANGELOG.md`

Add to [Unreleased] section:

```markdown
### Added
- Billing mode support (prepaid/subscription) for flexible payment models
- Monthly usage limits for subscription users (360 minutes/month)
- Usage statistics API endpoint (`GET /api/v1/usage/stats`)
- Rolling 30-day usage period with auto-reset
- HTTP 429 error when subscription limit exceeded

### Changed
- Session creation now checks usage limits based on billing mode
- Counselor model extended with billing mode and usage tracking fields

### Database
- Added `billing_mode` enum column to counselors table (prepaid/subscription)
- Added subscription usage tracking columns:
  - `monthly_usage_limit_minutes` (default: 360)
  - `monthly_minutes_used` (default: 0)
  - `usage_period_start` (rolling 30-day period)
- Migration: All existing users default to prepaid mode (backward compatible)
```

**Step 3: Update CHANGELOG_zh-TW.md**

Modify: `CHANGELOG_zh-TW.md`

Add same content in Traditional Chinese:

```markdown
### 新增
- 計費模式支援（儲值/訂閱）提供彈性付費模式
- 訂閱用戶每月使用上限（360 分鐘/月）
- 使用量統計 API 端點（`GET /api/v1/usage/stats`）
- 滾動 30 天使用週期與自動重置
- 訂閱超限時返回 HTTP 429 錯誤

### 變更
- Session 創建時根據計費模式檢查使用限制
- Counselor 模型擴充計費模式與使用追踪欄位

### 資料庫
- 新增 `billing_mode` 枚舉欄位至 counselors 表（prepaid/subscription）
- 新增訂閱使用追踪欄位：
  - `monthly_usage_limit_minutes`（預設：360）
  - `monthly_minutes_used`（預設：0）
  - `usage_period_start`（滾動 30 天週期）
- Migration：所有現有用戶預設為儲值模式（向後兼容）
```

**Step 4: Update TODO.md**

Modify: `TODO.md`

Find Issue #8 section and update:

```markdown
### 使用量限制
- [x] **每個月使用量隱藏上限設定** ✅ 已完成 (2026-01-31)
  - [x] 上限設定：6 小時/月 (360 分鐘)
  - [x] 計費模式：prepaid / subscription
  - [x] 重置週期：Rolling 30 天
  - [x] 超限行為：HTTP 429 + 詳細訊息
  - [x] API 端點：GET /api/v1/usage/stats
  - 實作：Middleware + UsageTracker service
  - 完成時間：2026-01-31
```

**Step 5: Commit**

```bash
git add PRD.md CHANGELOG.md CHANGELOG_zh-TW.md TODO.md
git commit -m "docs: document billing modes and usage limits

Update documentation for Issue #8 (monthly usage limits):
- PRD.md: Add billing system section with two modes
- CHANGELOG: Document new features and DB changes
- TODO.md: Mark Issue #8 as completed

Billing modes:
- Prepaid: existing credit-based system
- Subscription: new NT$100/month with 360 min limit

Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)

Co-Authored-By: Claude <noreply@anthropic.com>
Co-Authored-By: Happy <yesreply@happy.engineering>"
```

---

## Task 7: Update GitHub Issue #8

**Step 1: Add implementation summary to issue**

```bash
gh issue comment 8 --body "## ✅ 實作完成

**Commit Range**: See recent commits on staging branch
**部署**: staging branch
**測試**: Unit + Integration tests passing

### 實作內容

#### 1. 計費模式支援
\`\`\`python
billing_mode: prepaid | subscription

# Prepaid（儲值制）
- 檢查 available_credits > 0
- 扣除 credits 按使用時間

# Subscription（訂閱制）
- 檢查 subscription_expires_at > now()
- 檢查 monthly_minutes_used < 360
- Rolling 30 天週期自動重置
\`\`\`

#### 2. 使用量上限
\`\`\`yaml
上限: 6 小時/月 (360 分鐘)
成本: NT$87/月
重置: Rolling 30 天
超限: HTTP 429 Too Many Requests
\`\`\`

#### 3. API 端點
\`\`\`
GET /api/v1/usage/stats

Response (Subscription):
{
  \"billing_mode\": \"subscription\",
  \"monthly_limit_minutes\": 360,
  \"monthly_used_minutes\": 120,
  \"monthly_remaining_minutes\": 240,
  \"usage_percentage\": 33.33,
  \"is_limit_reached\": false,
  \"usage_period_start\": \"2026-01-21T00:00:00Z\",
  \"usage_period_end\": \"2026-02-20T00:00:00Z\"
}
\`\`\`

#### 4. Session 創建阻擋
\`\`\`
POST /api/v1/sessions

超限時返回:
HTTP 429 Too Many Requests
{
  \"detail\": {
    \"code\": \"MONTHLY_USAGE_LIMIT_EXCEEDED\",
    \"message\": \"您本月的使用時間已達上限（360分鐘）\",
    \"monthly_limit_minutes\": 360,
    \"monthly_used_minutes\": 365,
    \"reset_date\": \"2026-02-20T23:59:59Z\"
  }
}
\`\`\`

### 資料庫變更
- \`billing_mode\`: enum (prepaid/subscription)
- \`monthly_usage_limit_minutes\`: 360
- \`monthly_minutes_used\`: 0
- \`usage_period_start\`: timestamp

### 向後兼容
✅ 所有現有用戶自動設為 \`prepaid\` 模式
✅ 現有 credit 系統完全保留
✅ 可隨時切換計費模式

### 測試覆蓋
- Unit tests: UsageTracker, Middleware
- Integration tests: API endpoints, Session creation

### 下一步
🔴 **等待案主/iOS 開發者整合測試**

---
Generated with [Claude Code](https://claude.ai/code)
via [Happy](https://happy.engineering)"
```

---

## Testing & Verification

### Run Full Test Suite

```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific test categories
poetry run pytest tests/unit/test_usage_tracker.py -v
poetry run pytest tests/unit/test_usage_limit_middleware.py -v
poetry run pytest tests/integration/test_usage_api.py -v
poetry run pytest tests/integration/test_session_usage_limit.py -v
```

### Manual Testing

1. **Create subscription user**
```python
# In Python shell
from app.models.counselor import Counselor, BillingMode
from datetime import datetime, timedelta, timezone

counselor = Counselor(
    email="sub@test.com",
    username="subuser",
    hashed_password="...",
    tenant_id="test",
    billing_mode=BillingMode.SUBSCRIPTION,
    monthly_usage_limit_minutes=360,
    subscription_expires_at=datetime.now(timezone.utc) + timedelta(days=30)
)
```

2. **Test usage stats API**
```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/usage/stats
```

3. **Test session creation with limit**
```bash
# Set user to limit
UPDATE counselors SET monthly_minutes_used = 360 WHERE email = 'sub@test.com';

# Try to create session (should fail with 429)
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/sessions \
  -d '{"name":"Test","case_id":"..."}'
```

---

## Deployment Checklist

- [ ] All tests passing
- [ ] Migration created and tested
- [ ] Documentation updated (PRD, CHANGELOG, TODO)
- [ ] GitHub issue updated
- [ ] Code reviewed
- [ ] Merged to staging
- [ ] Run migration on staging: `alembic upgrade head`
- [ ] Verify existing users defaulted to prepaid mode
- [ ] Test both billing modes on staging
- [ ] Monitor for errors

---

## Rollback Plan

If issues arise:

```bash
# Rollback migration
alembic downgrade -1

# Or restore from backup
psql -U user -d dbname < backup.sql
```

The feature is backward compatible, so rollback should be safe.

---

**Plan Version**: 1.0
**Created**: 2026-01-31
**Estimated Time**: 3-4 hours
**Complexity**: Medium
