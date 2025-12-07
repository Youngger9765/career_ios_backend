#!/usr/bin/env python3
"""
Seed database with initial test data
"""
from datetime import date

from sqlalchemy.orm import Session

from app.core.database import engine
from app.core.security import hash_password
from app.models.client import Client
from app.models.counselor import Counselor, CounselorRole


def seed_database():
    """Seed database with initial test data"""
    with Session(engine) as db:
        # Create test counselors for both tenants
        counselors = [
            Counselor(
                email="admin@career.com",
                username="career_admin",
                full_name="Career Admin",
                hashed_password=hash_password("password123"),
                role=CounselorRole.ADMIN,
                tenant_id="career",
                is_active=True,
            ),
            Counselor(
                email="counselor@career.com",
                username="career_counselor",
                full_name="Career Counselor",
                hashed_password=hash_password("password123"),
                role=CounselorRole.COUNSELOR,
                tenant_id="career",
                is_active=True,
            ),
            Counselor(
                email="admin@island.com",
                username="island_admin",
                full_name="Island Admin",
                hashed_password=hash_password("password123"),
                role=CounselorRole.ADMIN,
                tenant_id="island",
                is_active=True,
            ),
            Counselor(
                email="counselor@island.com",
                username="island_counselor",
                full_name="Island Counselor",
                hashed_password=hash_password("password123"),
                role=CounselorRole.COUNSELOR,
                tenant_id="island",
                is_active=True,
            ),
        ]

        for counselor in counselors:
            db.add(counselor)

        db.commit()
        print("✅ Created 4 test counselors")

        # Get counselor IDs for client creation
        career_counselor = (
            db.query(Counselor).filter_by(email="counselor@career.com").first()
        )
        island_counselor = (
            db.query(Counselor).filter_by(email="counselor@island.com").first()
        )

        # Create test clients
        clients = [
            Client(
                code="C001",
                name="張三",
                email="zhang@example.com",
                gender="男",
                birth_date=date(1995, 5, 15),
                identity_option="在職者",
                current_status="尋求職涯轉換",
                phone="0912345678",
                education="大學",
                current_job="軟體工程師",
                career_status="轉職準備",
                counselor_id=career_counselor.id,
                tenant_id="career",
            ),
            Client(
                code="C002",
                name="李四",
                email="li@example.com",
                gender="女",
                birth_date=date(2000, 8, 20),
                identity_option="學生",
                current_status="準備升學",
                phone="0923456789",
                education="高中",
                counselor_id=island_counselor.id,
                tenant_id="island",
            ),
            Client(
                code="C003",
                name="王五",
                email="wang@example.com",
                gender="其他",
                birth_date=date(1992, 3, 10),
                identity_option="轉職者",
                current_status="探索新方向",
                phone="0934567890",
                education="研究所",
                current_job="產品經理",
                career_status="探索中",
                has_consultation_history="是",
                counselor_id=career_counselor.id,
                tenant_id="career",
            ),
        ]

        for client in clients:
            db.add(client)

        db.commit()
        print("✅ Created 3 test clients")

        print("\n" + "=" * 50)
        print("Database seeded successfully!")
        print("=" * 50)
        print("\nTest Accounts:")
        print("\nCareer Tenant:")
        print("  Admin: admin@career.com / password123")
        print("  Counselor: counselor@career.com / password123")
        print("\nIsland Tenant:")
        print("  Admin: admin@island.com / password123")
        print("  Counselor: counselor@island.com / password123")
        print("=" * 50)


if __name__ == "__main__":
    seed_database()
