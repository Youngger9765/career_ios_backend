"""
Integration tests for password reset flows with email verification

Tests the interaction between password reset and email verification:
1. Verified user can login with password
2. Verified user password reset keeps email_verified = True
3. Unverified user password reset sets email_verified = True (NEW FEATURE)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email_verification import create_verification_token
from app.core.security import hash_password
from app.models.counselor import Counselor, CounselorRole
from app.models.password_reset import PasswordResetToken


@pytest.mark.asyncio
class TestPasswordResetFlows:
    """Test password reset flows with email verification interaction"""

    async def test_verified_user_can_login_with_password(
        self,
        async_client: AsyncClient,
        db_session: Session,
        monkeypatch,
    ):
        """場景 1: 驗證信可以用 → 用戶用本來的帳密可以登入"""
        # 1. Enable email verification
        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", True)

        # 2. Mock email service
        with patch("app.api.auth.EmailSenderService") as mock_service:
            mock_service.return_value.send_verification_email = AsyncMock()

            # 3. Register user
            response = await async_client.post(
                "/api/auth/register",
                json={
                    "email": "test@example.com",
                    "password": "Password123!@#$",  # Min 12 chars
                    "tenant_id": "test_tenant",
                },
            )
            assert response.status_code == 201

        # 4. Get verification token
        verification_token = create_verification_token("test@example.com", "test_tenant")

        # 5. Verify email
        response = await async_client.post(
            "/api/auth/verify-email",
            json={"token": verification_token},
        )
        assert response.status_code == 200

        # 6. Login with original password
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "test@example.com",
                "password": "Password123!@#$",  # Same password as registration
                "tenant_id": "test_tenant",
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_verified_user_password_reset_keeps_verification(
        self,
        async_client: AsyncClient,
        db_session: Session,
        monkeypatch,
    ):
        """場景 2: 已驗證用戶忘記密碼 → 重設後 email_verified 保持 True"""
        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", True)

        # 1. Create verified user
        counselor = Counselor(
            email="verified@example.com",
            username="verified",
            full_name="Verified User",
            hashed_password=hash_password("OldPassword123!"),
            tenant_id="test_tenant",
            role=CounselorRole.COUNSELOR,
            is_active=True,
            email_verified=True,  # Already verified
            phone="+886912345678",
        )
        db_session.add(counselor)
        db_session.commit()

        # 2. Request password reset
        with patch("app.services.external.email_sender.email_sender.send_password_reset_email") as mock:
            mock.return_value = AsyncMock()
            response = await async_client.post(
                "/api/v1/auth/password-reset/request",
                json={
                    "email": "verified@example.com",
                    "tenant_id": "test_tenant",
                },
            )
            assert response.status_code == 200

        # 3. Get verification code from DB
        reset_record = db_session.query(PasswordResetToken).filter(
            PasswordResetToken.email == "verified@example.com"
        ).first()
        verification_code = reset_record.verification_code

        # 4. Confirm password reset
        new_password = "NewPassword123!"
        response = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "verification_code": verification_code,
                "email": "verified@example.com",
                "tenant_id": "test_tenant",
                "new_password": new_password,
            },
        )
        assert response.status_code == 200

        # 5. Verify email_verified is still True
        db_session.refresh(counselor)
        assert counselor.email_verified is True

        # 6. Can login with new password
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "verified@example.com",
                "password": new_password,
                "tenant_id": "test_tenant",
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_unverified_user_password_reset_verifies_email(
        self,
        async_client: AsyncClient,
        db_session: Session,
        monkeypatch,
    ):
        """場景 3: 未驗證用戶忘記密碼 → 重設後 email_verified 變 True，可登入"""
        monkeypatch.setattr(settings, "ENABLE_EMAIL_VERIFICATION", True)

        # 1. Create unverified user
        counselor = Counselor(
            email="unverified@example.com",
            username="unverified",
            full_name="Unverified User",
            hashed_password=hash_password("OldPassword123!"),
            tenant_id="test_tenant",
            role=CounselorRole.COUNSELOR,
            is_active=True,
            email_verified=False,  # Not verified
            phone="+886912345678",
        )
        db_session.add(counselor)
        db_session.commit()

        # 2. Cannot login (403 Forbidden)
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "unverified@example.com",
                "password": "OldPassword123!",
                "tenant_id": "test_tenant",
            },
        )
        assert response.status_code == 403
        assert "Email not verified" in response.json()["detail"]

        # 3. Request password reset
        with patch("app.services.external.email_sender.email_sender.send_password_reset_email") as mock:
            mock.return_value = AsyncMock()
            response = await async_client.post(
                "/api/v1/auth/password-reset/request",
                json={
                    "email": "unverified@example.com",
                    "tenant_id": "test_tenant",
                },
            )
            assert response.status_code == 200

        # 4. Get verification code from DB
        reset_record = db_session.query(PasswordResetToken).filter(
            PasswordResetToken.email == "unverified@example.com"
        ).first()
        verification_code = reset_record.verification_code

        # 5. Confirm password reset
        new_password = "NewPassword123!"
        response = await async_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "verification_code": verification_code,
                "email": "unverified@example.com",
                "tenant_id": "test_tenant",
                "new_password": new_password,
            },
        )
        assert response.status_code == 200

        # 6. Verify email_verified is now True (NEW FEATURE)
        db_session.refresh(counselor)
        assert counselor.email_verified is True

        # 7. Can login with new password (not blocked by 403)
        response = await async_client.post(
            "/api/auth/login",
            json={
                "email": "unverified@example.com",
                "password": new_password,
                "tenant_id": "test_tenant",
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
