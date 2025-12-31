"""
Check test@island.com account details
"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.counselor import Counselor


def check_account():
    db = SessionLocal()
    try:
        # Check test@island.com in island_parents tenant
        counselor = db.execute(
            select(Counselor).where(
                Counselor.email == "test@island.com",
                Counselor.tenant_id == "island_parents",
            )
        ).scalar_one_or_none()

        if counselor:
            print("✓ Account found:")
            print(f"  Email: {counselor.email}")
            print(f"  Username: {counselor.username}")
            print(f"  Tenant: {counselor.tenant_id}")
            print(f"  Full Name: {counselor.full_name}")
            print(f"  Is Active: {counselor.is_active}")
            print(f"  Role: {counselor.role}")
            print(f"  Hashed Password: {counselor.hashed_password[:50]}...")
        else:
            print("✗ Account not found!")

            # Check if it exists in other tenants
            other_counselor = db.execute(
                select(Counselor).where(Counselor.email == "test@island.com")
            ).scalar_one_or_none()

            if other_counselor:
                print(f"\n⚠️  Found in different tenant: {other_counselor.tenant_id}")

    finally:
        db.close()


if __name__ == "__main__":
    check_account()
