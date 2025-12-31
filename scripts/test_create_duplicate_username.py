"""
Test creating a counselor with duplicate username across different tenants.
"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.counselor import Counselor, CounselorRole


def test_duplicate_username():
    """Test creating kkk@kkk.com in island_parents tenant"""
    db = SessionLocal()

    try:
        # Check if kkk@kkk.com already exists in career tenant
        career_counselor = db.execute(
            select(Counselor).where(
                Counselor.email == "kkk@kkk.com", Counselor.tenant_id == "career"
            )
        ).scalar_one_or_none()

        if career_counselor:
            print("✓ Found kkk@kkk.com in career tenant:")
            print(f"  - Username: {career_counselor.username}")
            print(f"  - Email: {career_counselor.email}")
            print(f"  - Tenant: {career_counselor.tenant_id}")
        else:
            print("✗ kkk@kkk.com not found in career tenant")
            return

        # Check if kkk@kkk.com already exists in island_parents tenant
        island_counselor = db.execute(
            select(Counselor).where(
                Counselor.email == "kkk@kkk.com",
                Counselor.tenant_id == "island_parents",
            )
        ).scalar_one_or_none()

        if island_counselor:
            print("\n✓ kkk@kkk.com already exists in island_parents tenant")
            print(f"  - Username: {island_counselor.username}")
            print(f"  - Email: {island_counselor.email}")
            print(f"  - Tenant: {island_counselor.tenant_id}")
            print(
                "\n✅ Test PASSED: Same email+username can exist in different tenants!"
            )
            return

        # Try to create kkk@kkk.com in island_parents tenant
        print("\n➤ Attempting to create kkk@kkk.com in island_parents tenant...")
        new_counselor = Counselor(
            email="kkk@kkk.com",
            username="kkk",
            full_name="KKK Island Parent",
            phone="0909876543",
            hashed_password=hash_password("12345678"),
            tenant_id="island_parents",
            role=CounselorRole.COUNSELOR,
            is_active=True,
            available_credits=1000.0,
        )

        db.add(new_counselor)
        db.commit()
        db.refresh(new_counselor)

        print("✅ SUCCESS! Created kkk@kkk.com in island_parents tenant")
        print(f"  - ID: {new_counselor.id}")
        print(f"  - Username: {new_counselor.username}")
        print(f"  - Email: {new_counselor.email}")
        print(f"  - Tenant: {new_counselor.tenant_id}")
        print("\n✅ Test PASSED: Username uniqueness constraint is working correctly!")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n✗ Test FAILED: Username constraint issue still exists")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    test_duplicate_username()
