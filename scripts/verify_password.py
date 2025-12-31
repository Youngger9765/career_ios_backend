"""
Verify password for test@island.com
"""

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import verify_password
from app.models.counselor import Counselor


def verify():
    db = SessionLocal()
    try:
        counselor = db.execute(
            select(Counselor).where(
                Counselor.email == "test@island.com",
                Counselor.tenant_id == "island_parents",
            )
        ).scalar_one_or_none()

        if not counselor:
            print("✗ Account not found")
            return

        # Try common passwords
        passwords_to_try = ["12345678", "test12345", "password", "test1234"]

        print("Testing passwords...")
        for pwd in passwords_to_try:
            is_valid = verify_password(pwd, counselor.hashed_password)
            status = "✓ CORRECT" if is_valid else "✗ wrong"
            print(f"  {pwd}: {status}")
            if is_valid:
                print(f"\n✅ Correct password: {pwd}")
                return

        print("\n❌ None of the passwords matched")

    finally:
        db.close()


if __name__ == "__main__":
    verify()
