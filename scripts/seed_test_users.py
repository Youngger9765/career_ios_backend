#!/usr/bin/env python3
"""
Seed script to create test users for all three roles.

Creates:
- parent_test@example.com (COUNSELOR role)
- teacher_test@example.com (SUPERVISOR role)
- student_test@example.com (COUNSELOR role)

All accounts use password: test1234
Default tenant: test_tenant
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.counselor import Counselor, CounselorRole


def seed_test_users():
    """Create test user accounts if they don't exist"""
    db = SessionLocal()

    # Define test users
    test_users = [
        {
            "email": "parent_test@example.com",
            "username": "parent_test",
            "full_name": "Test Parent",
            "password": "test1234",
            "role": CounselorRole.COUNSELOR,
            "tenant_id": "test_tenant",
        },
        {
            "email": "teacher_test@example.com",
            "username": "teacher_test",
            "full_name": "Test Teacher",
            "password": "test1234",
            "role": CounselorRole.SUPERVISOR,
            "tenant_id": "test_tenant",
        },
        {
            "email": "student_test@example.com",
            "username": "student_test",
            "full_name": "Test Student",
            "password": "test1234",
            "role": CounselorRole.COUNSELOR,
            "tenant_id": "test_tenant",
        },
    ]

    created_count = 0
    skipped_count = 0

    try:
        for user_data in test_users:
            # Check if user already exists (by email + tenant_id)
            existing_user = db.execute(
                select(Counselor).where(
                    Counselor.email == user_data["email"],
                    Counselor.tenant_id == user_data["tenant_id"],
                )
            ).scalar_one_or_none()

            if existing_user:
                print(f"⏭️  Skipped: {user_data['email']} (already exists)")
                skipped_count += 1
                continue

            # Create new user
            counselor = Counselor(
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data["full_name"],
                hashed_password=hash_password(user_data["password"]),
                role=user_data["role"],
                tenant_id=user_data["tenant_id"],
                is_active=True,
            )

            db.add(counselor)
            db.commit()
            db.refresh(counselor)

            print(f"✅ Created: {user_data['email']} (role: {user_data['role'].value})")
            created_count += 1

        # Summary
        print("\n" + "=" * 60)
        print(f"✅ Seed completed: {created_count} created, {skipped_count} skipped")
        print("=" * 60)

        if created_count > 0:
            print("\nTest Accounts (password: test1234):")
            print("  - parent_test@example.com (COUNSELOR)")
            print("  - teacher_test@example.com (SUPERVISOR)")
            print("  - student_test@example.com (COUNSELOR)")
            print("\nTenant: test_tenant")
            print("=" * 60)

    except IntegrityError as e:
        db.rollback()
        print(f"❌ Database integrity error: {e}")
        print("This may happen if username already exists.")
    except Exception as e:
        db.rollback()
        print(f"❌ Unexpected error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_test_users()
