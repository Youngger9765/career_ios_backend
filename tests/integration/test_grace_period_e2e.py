"""
End-to-end tests for 14-day account deletion grace period.
Covers ALL scenarios including purge anonymization.
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.main import app
from app.models.counselor import Counselor


def _make_counselor(db_session: Session, email: str = None, **kwargs) -> Counselor:
    """Helper: create and persist a test counselor, return it."""
    if email is None:
        email = f"grace_test_{uuid.uuid4().hex[:8]}@example.com"
    defaults = dict(
        id=uuid.uuid4(),
        email=email,
        username=None,
        full_name="Grace Test User",
        hashed_password=hash_password("Test1234"),
        tenant_id="test_tenant",
        role="counselor",
        is_active=True,
    )
    defaults.update(kwargs)
    counselor = Counselor(**defaults)
    db_session.add(counselor)
    db_session.commit()
    db_session.refresh(counselor)
    return counselor


class TestGracePeriodE2E:
    """Complete grace period test suite"""

    def test_scenario_1_delete_preserves_pii(self, db_session: Session):
        """Scenario 1: Delete does NOT anonymize PII immediately"""
        counselor = _make_counselor(db_session, phone="+1234567890")
        email = counselor.email

        with TestClient(app) as client:
            # Login to get token
            login_resp = client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": "Test1234",
                    "tenant_id": "test_tenant",
                },
            )
            assert login_resp.status_code == 200, f"Login failed: {login_resp.json()}"
            token = login_resp.json()["access_token"]

            # Delete account
            resp = client.post(
                "/api/auth/delete-account",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )
            assert resp.status_code == 200, f"Delete failed: {resp.json()}"
            assert "14 days" in resp.json()["message"]

        # Check DB: PII should be preserved during grace period
        db_session.expire_all()
        result = db_session.execute(
            select(Counselor).where(Counselor.id == counselor.id)
        )
        updated = result.scalar_one()

        assert updated.email == email  # NOT anonymized
        assert updated.is_active is False
        assert updated.deleted_at is not None
        assert updated.hashed_password is not None  # Password preserved

    def test_scenario_2_login_restores_within_grace_period(self, db_session: Session):
        """Scenario 2: Login within 14 days restores account"""
        counselor = _make_counselor(db_session)
        email = counselor.email

        with TestClient(app) as client:
            # Login to get token
            login_resp = client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": "Test1234",
                    "tenant_id": "test_tenant",
                },
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["access_token"]

            # Delete account
            resp = client.post(
                "/api/auth/delete-account",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )
            assert resp.status_code == 200

            # Login again (within grace period)
            resp2 = client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": "Test1234",
                    "tenant_id": "test_tenant",
                },
            )
            assert (
                resp2.status_code == 200
            ), f"Grace period login failed: {resp2.json()}"
            data = resp2.json()
            assert data["account_restored"] is True
            assert data["user"]["email"] == email
            assert data["user"]["is_active"] is True

        # Verify DB: account actually restored
        db_session.expire_all()
        restored = db_session.execute(
            select(Counselor).where(Counselor.id == counselor.id)
        ).scalar_one()
        assert restored.is_active is True
        assert restored.deleted_at is None

    def test_scenario_3_login_fails_after_grace_period(self, db_session: Session):
        """Scenario 3: Login after 14 days returns 403 permanently deleted"""
        # Create counselor already in expired grace period state
        counselor = _make_counselor(
            db_session,
            is_active=False,
            deleted_at=datetime.now(timezone.utc) - timedelta(days=15),
        )
        email = counselor.email

        with TestClient(app) as client:
            resp = client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": "Test1234",
                    "tenant_id": "test_tenant",
                },
            )
            assert (
                resp.status_code == 403
            ), f"Expected 403, got: {resp.status_code} {resp.json()}"
            assert "permanently deleted" in resp.json()["detail"]

    def test_scenario_4_purge_anonymizes_pii(self, db_session: Session):
        """Scenario 4: Purge endpoint anonymizes PII after grace period"""
        counselor = _make_counselor(
            db_session,
            full_name="Purge Target User",
            phone="+9876543210",
            is_active=False,
            deleted_at=datetime.now(timezone.utc) - timedelta(days=15),
        )
        original_email = counselor.email
        counselor_id = counselor.id

        with TestClient(app) as client:
            # Mock RevenueCat delete so purge doesn't fail on external call
            with patch(
                "app.services.external.revenuecat_service.delete_customer",
                return_value=True,
            ):
                resp = client.post(
                    "/api/internal/purge-deleted-accounts",
                    headers={"X-Internal-Key": ""},
                )
            assert resp.status_code == 200, f"Purge failed: {resp.json()}"
            purge_data = resp.json()
            assert (
                purge_data["purged"] >= 1
            ), f"Expected at least 1 purged, got: {purge_data}"

        # Verify PII is anonymized
        db_session.expire_all()
        result = db_session.execute(
            select(Counselor).where(Counselor.id == counselor_id)
        )
        anon = result.scalar_one()

        assert anon.email.startswith("deleted_"), f"Email not anonymized: {anon.email}"
        assert (
            original_email in anon.email
        ), f"Original email not embedded: {anon.email}"
        assert anon.username is None, "Username should be nullified"
        assert anon.full_name is None, "full_name should be nullified"
        assert anon.phone is None, "Phone should be nullified"

    def test_scenario_5_purge_preserves_row_and_metadata(self, db_session: Session):
        """Scenario 5: Purge does NOT delete DB row - 去識別化 not deletion"""
        counselor = _make_counselor(
            db_session,
            is_active=False,
            deleted_at=datetime.now(timezone.utc) - timedelta(days=15),
        )
        counselor_id = counselor.id
        original_tenant_id = counselor.tenant_id

        with TestClient(app) as client:
            with patch(
                "app.services.external.revenuecat_service.delete_customer",
                return_value=True,
            ):
                resp = client.post(
                    "/api/internal/purge-deleted-accounts",
                    headers={"X-Internal-Key": ""},
                )
            assert resp.status_code == 200

        # ROW STILL EXISTS
        db_session.expire_all()
        row = db_session.execute(
            select(Counselor).where(Counselor.id == counselor_id)
        ).scalar_one_or_none()

        assert row is not None, "Row should NOT be deleted from DB!"
        assert row.is_active is False, "Row should still be inactive"
        assert row.deleted_at is not None, "deleted_at should still be set"
        assert row.hashed_password is not None, "Password hash should be preserved"
        assert row.tenant_id == original_tenant_id, "tenant_id should be preserved"
        assert row.created_at is not None, "created_at metadata should be preserved"

    def test_purge_skips_accounts_still_in_grace_period(self, db_session: Session):
        """Bonus: Purge should NOT anonymize accounts still within 14-day grace period"""
        counselor = _make_counselor(
            db_session,
            is_active=False,
            deleted_at=datetime.now(timezone.utc)
            - timedelta(days=5),  # Only 5 days ago
        )
        original_email = counselor.email
        counselor_id = counselor.id

        with TestClient(app) as client:
            with patch(
                "app.services.external.revenuecat_service.delete_customer",
                return_value=True,
            ):
                resp = client.post(
                    "/api/internal/purge-deleted-accounts",
                    headers={"X-Internal-Key": ""},
                )
            assert resp.status_code == 200

        # PII should NOT be anonymized (still in grace period)
        db_session.expire_all()
        row = db_session.execute(
            select(Counselor).where(Counselor.id == counselor_id)
        ).scalar_one()

        assert (
            row.email == original_email
        ), f"Email should not be anonymized yet: {row.email}"
        assert not row.email.startswith(
            "deleted_"
        ), "Email should not be prefixed with 'deleted_'"

    def test_purge_skips_already_anonymized_accounts(self, db_session: Session):
        """Bonus: Purge should not double-anonymize already-purged accounts"""
        # Create an already-anonymized account
        counselor = _make_counselor(
            db_session,
            email="deleted_1700000000_already@example.com",
            is_active=False,
            deleted_at=datetime.now(timezone.utc) - timedelta(days=20),
        )
        counselor_id = counselor.id
        pre_purge_email = counselor.email

        with TestClient(app) as client:
            with patch(
                "app.services.external.revenuecat_service.delete_customer",
                return_value=True,
            ):
                resp = client.post(
                    "/api/internal/purge-deleted-accounts",
                    headers={"X-Internal-Key": ""},
                )
            assert resp.status_code == 200
            # Should report 0 newly purged (already anonymized)
            assert (
                resp.json()["purged"] == 0
            ), f"Should not re-purge already anonymized account, got: {resp.json()}"

        # Email unchanged
        db_session.expire_all()
        row = db_session.execute(
            select(Counselor).where(Counselor.id == counselor_id)
        ).scalar_one()
        assert (
            row.email == pre_purge_email
        ), "Already-anonymized email should not change"

    def test_purge_requires_valid_internal_key(self, db_session: Session):
        """Security: Purge endpoint rejects wrong internal key"""
        with TestClient(app) as client:
            resp = client.post(
                "/api/internal/purge-deleted-accounts",
                headers={"X-Internal-Key": "wrong-secret-key"},
            )
            assert (
                resp.status_code == 403
            ), f"Expected 403 with wrong key, got: {resp.status_code}"

    def test_delete_then_restore_then_delete_again(self, db_session: Session):
        """Scenario: Delete → restore → delete again (second deletion works correctly)"""
        counselor = _make_counselor(db_session)
        email = counselor.email

        with TestClient(app) as client:
            # First login
            login_resp = client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": "Test1234",
                    "tenant_id": "test_tenant",
                },
            )
            token = login_resp.json()["access_token"]

            # First deletion
            del_resp = client.post(
                "/api/auth/delete-account",
                headers={"Authorization": f"Bearer {token}"},
                json={},
            )
            assert del_resp.status_code == 200

            # Restore via login
            restore_resp = client.post(
                "/api/auth/login",
                json={
                    "email": email,
                    "password": "Test1234",
                    "tenant_id": "test_tenant",
                },
            )
            assert restore_resp.status_code == 200
            assert restore_resp.json()["account_restored"] is True
            new_token = restore_resp.json()["access_token"]

            # Second deletion
            del_resp2 = client.post(
                "/api/auth/delete-account",
                headers={"Authorization": f"Bearer {new_token}"},
                json={},
            )
            assert (
                del_resp2.status_code == 200
            ), f"Second delete failed: {del_resp2.json()}"
            assert "14 days" in del_resp2.json()["message"]

        # Verify: account is in deletion state again
        db_session.expire_all()
        row = db_session.execute(
            select(Counselor).where(Counselor.id == counselor.id)
        ).scalar_one()
        assert row.is_active is False
        assert row.deleted_at is not None
        assert row.email == email  # PII still intact (grace period)
