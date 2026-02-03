"""
Integration test to verify usage tracking works end-to-end.
Tests that monthly_minutes_used is correctly tracked when sessions are created.
"""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.counselor import Counselor, BillingMode
from app.models.client import Client
from app.core.security import hash_password

client = TestClient(app)


class TestUsageTrackingVerification:
    """Verify that usage tracking works correctly for subscription mode."""

    def test_usage_tracking_complete_flow(self, db_session: Session, monkeypatch):
        """Test complete flow: register -> create client -> create session -> verify usage."""
        # Monkeypatch datetime for consistent testing
        monkeypatch.setenv("TESTING", "1")

        # Step 1: Create subscription account directly (bypass registration flow)
        counselor = Counselor(
            email="usage_verify@example.com",
            username="usage_verify",
            hashed_password=hash_password("SecurePassword123!"),
            tenant_id="test_tenant",
            billing_mode=BillingMode.SUBSCRIPTION,
            monthly_usage_limit_minutes=360,
            monthly_minutes_used=0,
            usage_period_start=datetime.now(timezone.utc),
            is_active=True,
            email_verified=True
        )
        db_session.add(counselor)
        db_session.commit()

        # Login to get token
        login_response = client.post("/api/auth/login", json={
            "email": "usage_verify@example.com",
            "password": "SecurePassword123!",
            "tenant_id": "test_tenant"
        })
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Check initial usage stats (should be 0)
        response = client.get("/api/v1/usage/stats", headers=headers)
        assert response.status_code == 200
        initial_stats = response.json()
        
        print(f"\n📊 Initial Usage Stats:")
        print(f"   Billing Mode: {initial_stats['billing_mode']}")
        print(f"   Monthly Limit: {initial_stats.get('monthly_limit_minutes')} minutes")
        print(f"   Used: {initial_stats.get('monthly_used_minutes')} minutes")
        print(f"   Remaining: {initial_stats.get('monthly_remaining_minutes')} minutes")
        
        assert initial_stats["billing_mode"] == "subscription"
        assert initial_stats["monthly_limit_minutes"] == 360
        assert initial_stats["monthly_used_minutes"] == 0
        assert initial_stats["monthly_remaining_minutes"] == 360
        assert initial_stats["is_limit_reached"] is False
        
        # Step 3: Create a client
        client_data = {
            "name": "Usage Test Client",
            "code": "USAGE001",
            "email": "usageclient@example.com",
            "gender": "male",
            "birth_date": "2000-01-01",
            "phone": "+886912345678",
            "identity_option": "學生",
            "current_status": "探索中"
        }
        
        response = client.post("/api/v1/clients", json=client_data, headers=headers)
        if response.status_code != 201:
            print(f"\n❌ Client creation failed: {response.status_code}")
            try:
                print(f"Error: {response.json()}")
            except:
                print(f"Raw response: {response.text}")
        assert response.status_code == 201
        client_obj = response.json()
        client_id = client_obj["id"]
        
        print(f"\n✅ Client created: {client_id}")

        # Step 3.5: Create a case for the client
        case_data = {
            "client_id": client_id,
            "description": "Usage tracking test case"
        }

        response = client.post("/api/v1/cases", json=case_data, headers=headers)
        if response.status_code != 201:
            print(f"\n❌ Case creation failed: {response.status_code}")
            print(f"Error: {response.json()}")
        assert response.status_code == 201
        case_obj = response.json()
        case_id = case_obj["id"]

        print(f"✅ Case created: {case_id}")

        # Step 4: Create a 20-minute session
        session_data = {
            "case_id": case_id,
            "client_id": client_id,
            "duration_minutes": 20,
            "session_date": datetime.now(timezone.utc).isoformat(),
            "notes": "Test session for usage tracking"
        }
        
        response = client.post("/api/v1/sessions", json=session_data, headers=headers)
        if response.status_code != 201:
            print(f"\n❌ Session creation failed: {response.status_code}")
            print(f"Error: {response.json()}")
        assert response.status_code == 201
        session_obj = response.json()
        
        print(f"\n✅ Session created: {session_obj['id']}")
        print(f"   Duration: {session_obj['duration_minutes']} minutes")
        
        # Step 5: Verify usage stats updated correctly
        response = client.get("/api/v1/usage/stats", headers=headers)
        assert response.status_code == 200
        updated_stats = response.json()
        
        print(f"\n📊 Updated Usage Stats:")
        print(f"   Used: {updated_stats.get('monthly_used_minutes')} minutes")
        print(f"   Remaining: {updated_stats.get('monthly_remaining_minutes')} minutes")
        print(f"   Usage %: {updated_stats.get('usage_percentage'):.1f}%")
        
        assert updated_stats["monthly_used_minutes"] == 20, \
            f"Expected 20 minutes used, got {updated_stats['monthly_used_minutes']}"
        assert updated_stats["monthly_remaining_minutes"] == 340, \
            f"Expected 340 minutes remaining, got {updated_stats['monthly_remaining_minutes']}"
        assert updated_stats["usage_percentage"] == pytest.approx(5.56, rel=0.1), \
            f"Expected ~5.56% usage, got {updated_stats['usage_percentage']}"
        assert updated_stats["is_limit_reached"] is False
        
        # Step 6: Create another session (60 minutes)
        session_data_2 = {
            "case_id": case_id,
            "client_id": client_id,
            "duration_minutes": 60,
            "session_date": datetime.now(timezone.utc).isoformat(),
            "notes": "Second test session"
        }
        
        response = client.post("/api/v1/sessions", json=session_data_2, headers=headers)
        assert response.status_code == 201
        
        print(f"\n✅ Second session created (60 minutes)")
        
        # Step 7: Verify cumulative usage
        response = client.get("/api/v1/usage/stats", headers=headers)
        assert response.status_code == 200
        final_stats = response.json()
        
        print(f"\n📊 Final Usage Stats:")
        print(f"   Used: {final_stats.get('monthly_used_minutes')} minutes")
        print(f"   Remaining: {final_stats.get('monthly_remaining_minutes')} minutes")
        print(f"   Usage %: {final_stats.get('usage_percentage'):.1f}%")
        
        assert final_stats["monthly_used_minutes"] == 80, \
            f"Expected 80 minutes total, got {final_stats['monthly_used_minutes']}"
        assert final_stats["monthly_remaining_minutes"] == 280, \
            f"Expected 280 minutes remaining, got {final_stats['monthly_remaining_minutes']}"
        assert final_stats["usage_percentage"] == pytest.approx(22.22, rel=0.1)
        
        print(f"\n🎉 ✅ ✅ ✅ USAGE TRACKING VERIFIED SUCCESSFULLY!")
        print(f"   Initial: 0 min → After 20 min session: 20 min → After 60 min session: 80 min")
        print(f"   Remaining correctly calculated: 360 - 80 = 280 minutes")


    def test_usage_limit_enforcement(self, db_session: Session, monkeypatch):
        """Test that sessions are blocked when usage limit is reached."""
        monkeypatch.setenv("TESTING", "1")
        
        # Create a subscription account at limit
        counselor = Counselor(
            email="at_limit@example.com",
            username="at_limit",
            hashed_password=hash_password("SecurePassword123!"),
            tenant_id="test_tenant",
            billing_mode=BillingMode.SUBSCRIPTION,
            monthly_usage_limit_minutes=360,
            monthly_minutes_used=360,  # At limit
            usage_period_start=datetime.now(timezone.utc),
            is_active=True,
            email_verified=True
        )
        db_session.add(counselor)
        db_session.commit()
        db_session.refresh(counselor)  # Ensure ID is populated

        # Create client with required fields
        test_client = Client(
            counselor_id=counselor.id,
            tenant_id="test_tenant",
            name="Test Client",
            code="LIMIT001",
            email="limitclient@example.com",
            gender="male",  # Required field
            birth_date=datetime(2000, 1, 1).date(),  # Required field
            phone="+886912345678",  # Required field
            identity_option="學生",
            current_status="探索中"
        )
        db_session.add(test_client)
        db_session.commit()
        db_session.refresh(test_client)  # Ensure ID is set

        # Create case for the client
        from app.models.case import Case
        test_case = Case(
            counselor_id=counselor.id,
            client_id=test_client.id,
            tenant_id="test_tenant",
            case_number=1,
            status="active"
        )
        db_session.add(test_case)
        db_session.commit()
        db_session.refresh(test_case)

        # Login
        login_response = client.post("/api/auth/login", json={
            "email": "at_limit@example.com",
            "password": "SecurePassword123!",
            "tenant_id": "test_tenant"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to create session - should be blocked
        session_data = {
            "case_id": str(test_case.id),
            "client_id": str(test_client.id),
            "duration_minutes": 10,
            "session_date": datetime.now(timezone.utc).isoformat(),
            "notes": "Should be blocked"
        }
        
        response = client.post("/api/v1/sessions", json=session_data, headers=headers)
        assert response.status_code == 429
        error = response.json()
        assert error["code"] == "MONTHLY_USAGE_LIMIT_EXCEEDED"
        
        print(f"\n✅ Usage limit enforcement works correctly!")
        print(f"   Session blocked when limit (360/360 minutes) reached")
