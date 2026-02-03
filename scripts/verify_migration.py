#!/usr/bin/env python3
"""
Verify migration results by checking account billing mode and subscription fields.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.counselor import BillingMode, Counselor


def verify_migration():
    """Verify migration results"""
    db = SessionLocal()

    try:
        # Check purpleice9765@msn.com in career tenant
        test_account = db.execute(
            select(Counselor).where(
                Counselor.email == "purpleice9765@msn.com",
                Counselor.tenant_id == "career"
            )
        ).scalar_one_or_none()

        if not test_account:
            print("❌ Test account not found")
            return

        print("\n" + "="*60)
        print("Migration Verification - purpleice9765@msn.com (career)")
        print("="*60)
        print(f"Email: {test_account.email}")
        print(f"Tenant ID: {test_account.tenant_id}")
        print(f"Billing Mode: {test_account.billing_mode}")
        print(f"Monthly Usage Limit (minutes): {test_account.monthly_usage_limit_minutes}")
        print(f"Monthly Minutes Used: {test_account.monthly_minutes_used}")
        print(f"Usage Period Start: {test_account.usage_period_start}")
        print(f"Available Credits (preserved): {test_account.available_credits}")

        # Check all accounts
        print("\n" + "="*60)
        print("All Accounts Summary")
        print("="*60)

        all_counselors = db.execute(select(Counselor)).scalars().all()

        subscription_count = sum(
            1 for c in all_counselors
            if c.billing_mode == BillingMode.SUBSCRIPTION.value
        )
        prepaid_count = sum(
            1 for c in all_counselors
            if c.billing_mode == BillingMode.PREPAID.value
        )

        print(f"Total Accounts: {len(all_counselors)}")
        print(f"Subscription Mode: {subscription_count}")
        print(f"Prepaid Mode: {prepaid_count}")

        if prepaid_count > 0:
            print("\n⚠️  Warning: Found remaining prepaid accounts:")
            prepaid_accounts = [
                c for c in all_counselors
                if c.billing_mode == BillingMode.PREPAID.value
            ]
            for account in prepaid_accounts:
                print(f"  • {account.email} ({account.tenant_id})")
        else:
            print("\n✅ All accounts successfully migrated to subscription mode!")

    finally:
        db.close()


if __name__ == "__main__":
    verify_migration()
