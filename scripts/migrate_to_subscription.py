#!/usr/bin/env python3
"""
Migrate all accounts from prepaid to subscription billing mode.

Usage:
    # Dry run (preview changes)
    python scripts/migrate_to_subscription.py

    # Execute migration
    python scripts/migrate_to_subscription.py --execute
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.counselor import BillingMode, Counselor


def migrate_to_subscription(dry_run: bool = True) -> None:
    """
    Migrate all prepaid accounts to subscription mode.

    Args:
        dry_run: If True, only preview changes without committing
    """
    db = SessionLocal()
    migration_count = 0

    try:
        # Find all prepaid accounts
        prepaid_counselors = db.execute(
            select(Counselor).where(
                Counselor.billing_mode == BillingMode.PREPAID.value
            )
        ).scalars().all()

        print(f"\n{'='*60}")
        print(f"Migration: Prepaid → Subscription")
        print(f"{'='*60}")
        print(f"Found {len(prepaid_counselors)} prepaid accounts to migrate\n")

        if not prepaid_counselors:
            print("✅ No prepaid accounts found. All accounts already in subscription mode.")
            return

        # Show preview
        print("Accounts to migrate:")
        print(f"{'Email':<40} {'Current Credits':<15} {'Tenant ID'}")
        print("-" * 60)
        for counselor in prepaid_counselors:
            print(
                f"{counselor.email:<40} "
                f"{counselor.available_credits:<15.2f} "
                f"{counselor.tenant_id}"
            )
        print()

        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
            print("\nMigration plan for each account:")
            print("  • billing_mode: prepaid → subscription")
            print("  • monthly_usage_limit_minutes: → 360 (6 hours)")
            print("  • monthly_minutes_used: → 0")
            print("  • usage_period_start: → NOW()")
            print("  • available_credits: PRESERVED (not deleted)")
            print("\nRun with --execute to apply changes")
            return

        # Confirm before proceeding
        print("⚠️  EXECUTE MODE - Changes will be committed to database")
        confirm = input(f"\nMigrate {len(prepaid_counselors)} accounts? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Migration cancelled")
            return

        print("\nMigrating accounts...\n")

        # Migrate each account
        now = datetime.utcnow()
        for counselor in prepaid_counselors:
            # Update billing mode and subscription fields
            counselor.billing_mode = BillingMode.SUBSCRIPTION.value
            counselor.monthly_usage_limit_minutes = 360  # 6 hours
            counselor.monthly_minutes_used = 0
            counselor.usage_period_start = now
            # Note: available_credits preserved but not used in subscription mode

            migration_count += 1
            print(
                f"✅ [{migration_count}/{len(prepaid_counselors)}] "
                f"Migrated: {counselor.email}"
            )

        # Commit transaction
        db.commit()

        print(f"\n{'='*60}")
        print(f"✅ Successfully migrated {migration_count} accounts")
        print(f"{'='*60}")
        print("\nNext steps:")
        print("  1. Verify with test account: purpleice9765@msn.com")
        print("  2. Test GET /api/v1/usage/stats endpoint")
        print("  3. Check monthly_limit_minutes = 360")
        print("  4. Check monthly_used_minutes = 0")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        print("Database rolled back - no changes applied")
        raise
    finally:
        db.close()


def main():
    """Main entry point"""
    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN MODE (Preview Only)")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("EXECUTE MODE (Will Apply Changes)")
        print("="*60)

    migrate_to_subscription(dry_run=dry_run)


if __name__ == "__main__":
    main()
