"""
Integration tests for Admin Credit Management APIs
Following TDD approach - these tests define the expected behavior
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest


class TestAdminCreditMembers:
    """Test /api/v1/admin/credits/members endpoints"""

    def test_list_members_with_credit_info_success(
        self, client, admin_token, test_counselors
    ):
        """Admin can list all counselors with credit information"""
        response = client.get(
            "/api/v1/admin/credits/members",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify credit fields are present
        member = data[0]
        assert "id" in member
        assert "email" in member
        assert "full_name" in member
        assert "phone" in member
        assert "tenant_id" in member
        assert "total_credits" in member
        assert "credits_used" in member
        assert "available_credits" in member
        assert "subscription_expires_at" in member

    def test_list_members_filter_by_tenant(self, client, admin_token, test_counselors):
        """Admin can filter members by tenant_id"""
        response = client.get(
            "/api/v1/admin/credits/members?tenant_id=island_parents",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        # All returned members should be from island_parents tenant
        for member in data:
            assert member["tenant_id"] == "island_parents"

    def test_list_members_unauthorized(self, client, counselor_token):
        """Non-admin cannot list members"""
        response = client.get(
            "/api/v1/admin/credits/members",
            headers={"Authorization": f"Bearer {counselor_token}"},
        )

        assert response.status_code == 403
        assert "admin" in response.json()["detail"].lower()


class TestAdminAddCredits:
    """Test /api/v1/admin/credits/members/{counselor_id}/add endpoint"""

    def test_add_credits_purchase_success(self, client, admin_token, test_counselor_id):
        """Admin can add credits (purchase type)"""
        request_data = {
            "credits_delta": 1000,
            "transaction_type": "purchase",
            "notes": "Test purchase of 1000 credits",
        }

        response = client.post(
            f"/api/v1/admin/credits/members/{test_counselor_id}/add",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "credit_log" in data
        assert data["credit_log"]["credits_delta"] == 1000
        assert data["credit_log"]["transaction_type"] == "purchase"
        assert data["new_balance"] == 1000

    def test_add_credits_admin_adjustment(self, client, admin_token, test_counselor_id):
        """Admin can add credits (admin adjustment)"""
        request_data = {
            "credits_delta": 500,
            "transaction_type": "admin_adjustment",
            "notes": "Admin adjustment +500",
        }

        response = client.post(
            f"/api/v1/admin/credits/members/{test_counselor_id}/add",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["credit_log"]["transaction_type"] == "admin_adjustment"

    def test_add_credits_negative_adjustment(
        self, client, admin_token, test_counselor_with_credits
    ):
        """Admin can remove credits (negative adjustment)"""
        counselor_id = test_counselor_with_credits["id"]

        request_data = {
            "credits_delta": -200,
            "transaction_type": "admin_adjustment",
            "notes": "Remove 200 credits",
        }

        response = client.post(
            f"/api/v1/admin/credits/members/{counselor_id}/add",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["credit_log"]["credits_delta"] == -200

    def test_add_credits_unauthorized(self, client, counselor_token, test_counselor_id):
        """Non-admin cannot add credits"""
        request_data = {
            "credits_delta": 1000,
            "transaction_type": "purchase",
        }

        response = client.post(
            f"/api/v1/admin/credits/members/{test_counselor_id}/add",
            headers={"Authorization": f"Bearer {counselor_token}"},
            json=request_data,
        )

        assert response.status_code == 403

    def test_add_credits_invalid_counselor(self, client, admin_token):
        """Adding credits to non-existent counselor returns 404"""
        fake_id = str(uuid4())
        request_data = {
            "credits_delta": 1000,
            "transaction_type": "purchase",
        }

        response = client.post(
            f"/api/v1/admin/credits/members/{fake_id}/add",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 404


class TestAdminCreditLogs:
    """Test /api/v1/admin/credits/logs endpoint"""

    def test_view_credit_logs_all(self, client, admin_token, credit_transactions):
        """Admin can view all credit transactions"""
        response = client.get(
            "/api/v1/admin/credits/logs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Verify log structure
        log = data[0]
        assert "id" in log
        assert "counselor_id" in log
        assert "credits_delta" in log
        assert "transaction_type" in log
        assert "raw_data" in log
        assert "rate_snapshot" in log
        assert "calculation_details" in log
        assert "created_at" in log

    def test_view_credit_logs_filter_by_counselor(
        self, client, admin_token, test_counselor_id, credit_transactions
    ):
        """Admin can filter logs by counselor_id"""
        response = client.get(
            f"/api/v1/admin/credits/logs?counselor_id={test_counselor_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        # All logs should belong to specified counselor
        for log in data:
            assert log["counselor_id"] == str(test_counselor_id)

    def test_view_credit_logs_filter_by_type(
        self, client, admin_token, credit_transactions
    ):
        """Admin can filter logs by transaction_type"""
        response = client.get(
            "/api/v1/admin/credits/logs?transaction_type=purchase",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        # All logs should be purchase type
        for log in data:
            assert log["transaction_type"] == "purchase"

    def test_view_credit_logs_pagination(
        self, client, admin_token, credit_transactions
    ):
        """Admin can paginate credit logs"""
        response = client.get(
            "/api/v1/admin/credits/logs?limit=5&offset=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_view_credit_logs_unauthorized(self, client, counselor_token):
        """Non-admin cannot view credit logs"""
        response = client.get(
            "/api/v1/admin/credits/logs",
            headers={"Authorization": f"Bearer {counselor_token}"},
        )

        assert response.status_code == 403


class TestAdminBillingRates:
    """Test /api/v1/admin/credits/rates endpoints"""

    def test_create_billing_rate_success(self, client, admin_token):
        """Admin can create new billing rate"""
        request_data = {
            "rule_name": "voice_call",
            "calculation_method": "per_second",
            "rate_config": {"credits_per_second": 0.0278},
            "effective_from": datetime.utcnow().isoformat(),
        }

        response = client.post(
            "/api/v1/admin/credits/rates",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rule_name"] == "voice_call"
        assert data["calculation_method"] == "per_second"
        assert data["version"] == 1
        assert data["is_active"] is True

    def test_update_billing_rate_creates_new_version(
        self, client, admin_token, existing_billing_rate
    ):
        """Updating billing rate creates new version and deactivates old"""
        request_data = {
            "rule_name": existing_billing_rate["rule_name"],
            "calculation_method": "per_second",
            "rate_config": {"credits_per_second": 0.03},  # Updated rate
            "effective_from": datetime.utcnow().isoformat(),
        }

        response = client.post(
            "/api/v1/admin/credits/rates",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == existing_billing_rate["version"] + 1
        assert data["is_active"] is True

    def test_list_billing_rates(self, client, admin_token, billing_rates):
        """Admin can list all billing rates"""
        response = client.get(
            "/api/v1/admin/credits/rates",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_list_billing_rates_filter_by_rule_name(
        self, client, admin_token, billing_rates
    ):
        """Admin can filter rates by rule_name"""
        response = client.get(
            "/api/v1/admin/credits/rates?rule_name=voice_call",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for rate in data:
            assert rate["rule_name"] == "voice_call"

    def test_list_billing_rates_filter_by_active(
        self, client, admin_token, billing_rates
    ):
        """Admin can filter rates by is_active"""
        response = client.get(
            "/api/v1/admin/credits/rates?is_active=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        for rate in data:
            assert rate["is_active"] is True

    def test_billing_rate_unauthorized(self, client, counselor_token):
        """Non-admin cannot manage billing rates"""
        request_data = {
            "rule_name": "test",
            "calculation_method": "per_second",
            "rate_config": {"credits_per_second": 1},
            "effective_from": datetime.utcnow().isoformat(),
        }

        response = client.post(
            "/api/v1/admin/credits/rates",
            headers={"Authorization": f"Bearer {counselor_token}"},
            json=request_data,
        )

        assert response.status_code == 403


class TestCrossTenantSupport:
    """Test that credit system works universally across all tenants"""

    def test_credits_work_for_all_tenants(
        self, client, admin_token, counselors_all_tenants
    ):
        """Verify same credit mechanism works for career, island, island_parents"""
        for tenant_counselor in counselors_all_tenants:
            counselor_id = tenant_counselor["id"]
            tenant_id = tenant_counselor["tenant_id"]

            # Add credits
            request_data = {
                "credits_delta": 500,
                "transaction_type": "purchase",
                "notes": f"Test for {tenant_id}",
            }

            response = client.post(
                f"/api/v1/admin/credits/members/{counselor_id}/add",
                headers={"Authorization": f"Bearer {admin_token}"},
                json=request_data,
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_credit_isolation_by_counselor(
        self, client, admin_token, counselors_all_tenants
    ):
        """Credits are isolated per counselor, not shared"""
        counselor1 = counselors_all_tenants[0]
        counselor2 = counselors_all_tenants[1]

        # Add credits to counselor1
        client.post(
            f"/api/v1/admin/credits/members/{counselor1['id']}/add",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"credits_delta": 1000, "transaction_type": "purchase"},
        )

        # Check counselor2 has no credits
        response = client.get(
            "/api/v1/admin/credits/members",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        members = response.json()
        counselor2_data = next(m for m in members if m["id"] == str(counselor2["id"]))
        assert counselor2_data["total_credits"] == 0


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def admin_token(client, db_session):
    """Create admin user and return auth token"""
    from app.core.security import hash_password
    from app.models.counselor import Counselor, CounselorRole

    admin = Counselor(
        email="admin@test.com",
        username="admin",
        full_name="Admin User",
        hashed_password=hash_password("admin123"),
        tenant_id="career",
        role=CounselorRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def counselor_token(client, db_session):
    """Create regular counselor and return auth token"""
    from app.core.security import hash_password
    from app.models.counselor import Counselor, CounselorRole

    counselor = Counselor(
        email="counselor@test.com",
        username="counselor",
        full_name="Regular Counselor",
        hashed_password=hash_password("counselor123"),
        tenant_id="career",
        role=CounselorRole.COUNSELOR,
        is_active=True,
    )
    db_session.add(counselor)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "counselor", "password": "counselor123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def test_counselors(db_session):
    """Create test counselors for all three tenants"""
    from app.core.security import hash_password
    from app.models.counselor import Counselor, CounselorRole

    counselors = []
    for tenant_id in ["career", "island", "island_parents"]:
        counselor = Counselor(
            email=f"test_{tenant_id}@test.com",
            username=f"test_{tenant_id}",
            full_name=f"Test {tenant_id.title()}",
            hashed_password=hash_password("test123"),
            tenant_id=tenant_id,
            role=CounselorRole.COUNSELOR,
            is_active=True,
            total_credits=0,
            credits_used=0,
        )
        db_session.add(counselor)
        counselors.append(counselor)

    db_session.commit()
    return counselors


@pytest.fixture
def test_counselor_id(test_counselors):
    """Return ID of first test counselor"""
    return test_counselors[0].id


@pytest.fixture
def test_counselor_with_credits(db_session, test_counselors):
    """Create counselor with existing credits"""
    counselor = test_counselors[0]
    counselor.total_credits = 1000
    counselor.credits_used = 0
    db_session.commit()
    db_session.refresh(counselor)
    return {"id": counselor.id, "total_credits": 1000}


@pytest.fixture
def counselors_all_tenants(test_counselors):
    """Return counselors from all three tenants"""
    return [
        {"id": c.id, "tenant_id": c.tenant_id, "email": c.email}
        for c in test_counselors
    ]


@pytest.fixture
def credit_transactions(db_session, test_counselors):
    """Create sample credit transactions"""
    from app.models.credit_log import CreditLog

    transactions = []
    for counselor in test_counselors[:2]:
        # Purchase
        log1 = CreditLog(
            counselor_id=counselor.id,
            credits_delta=1000,
            transaction_type="purchase",
            raw_data={"notes": "Initial purchase"},
        )
        db_session.add(log1)
        transactions.append(log1)

        # Usage
        log2 = CreditLog(
            counselor_id=counselor.id,
            credits_delta=-100,
            transaction_type="usage",
            raw_data={"duration_seconds": 3600},
        )
        db_session.add(log2)
        transactions.append(log2)

    db_session.commit()
    return transactions


@pytest.fixture
def billing_rates(db_session):
    """Create sample billing rates"""
    from app.models.credit_rate import CreditRate

    rates = [
        CreditRate(
            rule_name="voice_call",
            calculation_method="per_second",
            rate_config={"credits_per_second": 0.0278},
            version=1,
            is_active=True,
            effective_from=datetime.utcnow() - timedelta(days=30),
        ),
        CreditRate(
            rule_name="text_session",
            calculation_method="per_minute",
            rate_config={"credits_per_minute": 10},
            version=1,
            is_active=True,
            effective_from=datetime.utcnow() - timedelta(days=30),
        ),
    ]

    for rate in rates:
        db_session.add(rate)

    db_session.commit()
    return rates


@pytest.fixture
def existing_billing_rate(billing_rates):
    """Return first billing rate"""
    return {
        "rule_name": billing_rates[0].rule_name,
        "version": billing_rates[0].version,
    }
