#!/usr/bin/env python3
"""Create a test account for API testing"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.counselor import Counselor, BillingMode
from app.core.security import hash_password

db = SessionLocal()
try:
    # Check if account exists
    existing = db.execute(
        select(Counselor).where(
            Counselor.email == "migration-test@example.com",
            Counselor.tenant_id == "career"
        )
    ).scalar_one_or_none()

    if existing:
        print("Account already exists, updating password...")
        existing.hashed_password = hash_password("test123456")
        existing.is_active = True
        existing.email_verified = True
        db.commit()
        print("✅ Account updated")
    else:
        print("Creating new test account...")
        account = Counselor(
            email="migration-test@example.com",
            tenant_id="career",
            hashed_password=hash_password("test123456"),
            full_name="Migration Test",
            billing_mode=BillingMode.SUBSCRIPTION.value,
            monthly_usage_limit_minutes=360,
            monthly_minutes_used=0,
            usage_period_start=datetime.utcnow(),
            is_active=True,
            email_verified=True,
        )
        db.add(account)
        db.commit()
        print("✅ Account created")

    print("\nTest credentials:")
    print("  Email: migration-test@example.com")
    print("  Password: test123456")
    print("  Tenant: career")

finally:
    db.close()
