#!/usr/bin/env python3
"""Check account details"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.counselor import Counselor
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()
try:
    account = db.execute(
        select(Counselor).where(
            Counselor.email == "purpleice9765@msn.com",
            Counselor.tenant_id == "career"
        )
    ).scalar_one_or_none()

    if account:
        print(f"Email: {account.email}")
        print(f"Tenant: {account.tenant_id}")
        print(f"Active: {account.is_active}")
        print(f"Has password: {bool(account.hashed_password)}")

        # Test if default password works
        test_passwords = ["password123", "testpassword", "test123"]
        for pwd in test_passwords:
            if pwd_context.verify(pwd, account.hashed_password):
                print(f"✅ Password is: {pwd}")
                break
        else:
            print("❌ None of the test passwords work")
            print("Need to reset password")
finally:
    db.close()
