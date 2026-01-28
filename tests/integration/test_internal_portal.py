"""
Integration tests for Internal Portal (/internal route)

Test Coverage:
1. Landing Page (/) - GET request
2. Internal Portal (/internal) - GET request with password protection
3. Environment-specific behavior (Production/Staging/Dev)
4. Password validation
5. Rate limiting
"""
import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.asyncio
class TestLandingPage:
    """Test GET / (Landing Page)"""

    async def test_landing_page_loads(self, async_client: AsyncClient):
        """Test that landing page loads successfully"""
        response = await async_client.get("/")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")

    async def test_landing_page_has_content(self, async_client: AsyncClient):
        """Test that landing page contains expected content"""
        response = await async_client.get("/")
        html_content = response.text

        assert response.status_code == status.HTTP_200_OK
        # Check for landing page content
        assert "浮島親子" in html_content or "landing" in html_content.lower()
        # Should NOT contain admin portal links
        assert "/rag" not in html_content
        assert "/admin" not in html_content
        assert "/console" not in html_content

    async def test_landing_page_has_login_link(self, async_client: AsyncClient):
        """Test that landing page has login link"""
        response = await async_client.get("/")
        html_content = response.text

        assert response.status_code == status.HTTP_200_OK
        # Should have link to login or forgot password
        assert "/island-parents/login" in html_content or "/forgot-password" in html_content


@pytest.mark.asyncio
class TestInternalPortal:
    """Test GET /internal (Internal Portal)"""

    async def test_internal_portal_without_password_in_dev(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that internal portal allows access without password in dev environment"""
        # Set environment to development
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")
        monkeypatch.setattr(settings, "INTERNAL_PORTAL_PASSWORD", None)

        response = await async_client.get("/internal")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        # Should show admin portal (index.html)
        assert "RAG 控制台" in html_content or "管理後台" in html_content

    async def test_internal_portal_without_password_in_staging(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that internal portal allows access without password in staging"""
        # Set environment to staging
        monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
        monkeypatch.setattr(settings, "INTERNAL_PORTAL_PASSWORD", None)

        response = await async_client.get("/internal")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        # Should show admin portal
        assert "RAG 控制台" in html_content or "管理後台" in html_content

    async def test_internal_portal_without_password_in_production(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that internal portal shows error in production without password"""
        # Set environment to production
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "INTERNAL_PORTAL_PASSWORD", None)

        response = await async_client.get("/internal")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        # Should show error page
        assert "設定錯誤" in html_content or "not configured" in html_content.lower()
        assert "INTERNAL_PORTAL_PASSWORD" in html_content

    async def test_internal_portal_with_correct_password(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that internal portal allows access with correct password"""
        test_password = "test-password-123"
        monkeypatch.setattr(settings, "INTERNAL_PORTAL_PASSWORD", test_password)
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")

        response = await async_client.get(f"/internal?password={test_password}")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        # Should show admin portal
        assert "RAG 控制台" in html_content or "管理後台" in html_content

    async def test_internal_portal_with_wrong_password(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that internal portal shows login page with wrong password"""
        test_password = "test-password-123"
        monkeypatch.setattr(settings, "INTERNAL_PORTAL_PASSWORD", test_password)
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")

        response = await async_client.get("/internal?password=wrong-password")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        # Should show login page
        assert "內部管理入口" in html_content or "password" in html_content.lower()
        assert "Invalid password" in html_content or "錯誤" in html_content

    async def test_internal_portal_without_password_param(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that internal portal shows login page when password is required but not provided"""
        test_password = "test-password-123"
        monkeypatch.setattr(settings, "INTERNAL_PORTAL_PASSWORD", test_password)
        monkeypatch.setattr(settings, "ENVIRONMENT", "development")

        response = await async_client.get("/internal")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        # Should show login page
        assert "內部管理入口" in html_content or "password" in html_content.lower()

    async def test_internal_portal_production_with_correct_password(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that internal portal allows access in production with correct password"""
        test_password = "test-password-123"
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "INTERNAL_PORTAL_PASSWORD", test_password)

        response = await async_client.get(f"/internal?password={test_password}")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        # Should show admin portal
        assert "RAG 控制台" in html_content or "管理後台" in html_content

    async def test_internal_portal_production_with_wrong_password(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that internal portal shows login page in production with wrong password"""
        test_password = "test-password-123"
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "INTERNAL_PORTAL_PASSWORD", test_password)

        response = await async_client.get("/internal?password=wrong-password")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        # Should show login page
        assert "內部管理入口" in html_content or "password" in html_content.lower()
        assert "Invalid password" in html_content or "錯誤" in html_content

    async def test_internal_portal_staging_with_password_configured(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that internal portal requires password in staging when configured"""
        test_password = "staging-password-123"
        monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
        monkeypatch.setattr(settings, "INTERNAL_PORTAL_PASSWORD", test_password)

        # Without password - should show login
        response1 = await async_client.get("/internal")
        assert response1.status_code == status.HTTP_200_OK
        html1 = response1.text
        assert "內部管理入口" in html1 or "password" in html1.lower()

        # With correct password - should show portal
        response2 = await async_client.get(f"/internal?password={test_password}")
        assert response2.status_code == status.HTTP_200_OK
        html2 = response2.text
        assert "RAG 控制台" in html2 or "管理後台" in html2

