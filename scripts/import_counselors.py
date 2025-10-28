#!/usr/bin/env python
"""
Import counselors from whitelist

Usage:
    python scripts/import_counselors.py counselors.csv

CSV format:
    email,username,full_name,password,role,tenant_id
    john@example.com,john,John Doe,password123,counselor,career
"""
import asyncio
import csv
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Settings
from app.core.security import hash_password
from app.models.counselor import Counselor


async def import_counselors_from_csv(csv_path: str):
    """
    Import counselors from CSV file

    Args:
        csv_path: Path to CSV file with counselor data
    """
    settings = Settings()

    # Create async engine
    db_url = str(settings.DATABASE_URL).replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url, echo=True)

    # Create session
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                email = row["email"]

                # Check if counselor already exists
                result = await session.execute(
                    select(Counselor).where(Counselor.email == email)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"⏭️  Skipping {email} (already exists)")
                    continue

                # Create new counselor
                counselor = Counselor(
                    id=uuid4(),
                    email=email,
                    username=row["username"],
                    full_name=row["full_name"],
                    hashed_password=hash_password(row["password"]),
                    role=row.get("role", "counselor"),
                    tenant_id=row.get("tenant_id", "career"),
                    is_active=True,
                )

                session.add(counselor)
                print(f"✅ Added {email}")

            await session.commit()
            print(f"\n🎉 Import completed!")

    await engine.dispose()


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/import_counselors.py counselors.csv")
        sys.exit(1)

    csv_path = sys.argv[1]

    if not Path(csv_path).exists():
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)

    asyncio.run(import_counselors_from_csv(csv_path))


if __name__ == "__main__":
    main()
