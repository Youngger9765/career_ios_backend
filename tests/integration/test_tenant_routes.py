"""
Integration tests for dynamic tenant routes

Test Coverage:
1. Dynamic tenant routes: /{tenant_id}/forgot-password, /{tenant_id}/reset-password
2. Valid tenant routing
3. Invalid tenant handling (404)
4. Tenant-specific content rendering
5. Backward compatibility with hardcoded routes
"""
import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDynamicTenantForgotPasswordRoute:
    """Test GET /{tenant_id}/forgot-password"""

    async def test_island_parents_forgot_password_route(
        self,
        async_client: AsyncClient,
    ):
        """Test dynamic route for island-parents forgot password"""
        response = await async_client.get("/island-parents/forgot-password")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")

        html_content = response.text
        # Check that tenant is auto-filled
        assert 'id="tenant"' in html_content or 'name="tenant"' in html_content
        # Check that default_tenant is set correctly
        assert 'value="island_parents"' in html_content or 'island_parents' in html_content

    async def test_career_forgot_password_route(
        self,
        async_client: AsyncClient,
    ):
        """Test dynamic route for career forgot password"""
        response = await async_client.get("/career/forgot-password")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")

        html_content = response.text
        # Check that tenant is auto-filled
        assert 'id="tenant"' in html_content or 'name="tenant"' in html_content
        # Check that default_tenant is set correctly
        assert 'value="career"' in html_content or 'career' in html_content

    async def test_island_forgot_password_route(
        self,
        async_client: AsyncClient,
    ):
        """Test dynamic route for island forgot password"""
        response = await async_client.get("/island/forgot-password")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")

        html_content = response.text
        # Check that tenant is auto-filled
        assert 'id="tenant"' in html_content or 'name="tenant"' in html_content
        # Check that default_tenant is set correctly
        assert 'value="island"' in html_content or 'island' in html_content

    async def test_invalid_tenant_forgot_password_route(
        self,
        async_client: AsyncClient,
    ):
        """Test that invalid tenant returns 404"""
        response = await async_client.get("/invalid-tenant/forgot-password")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Should return JSON error response
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower() or "Tenant not found" in data["detail"]

    async def test_empty_tenant_forgot_password_route(
        self,
        async_client: AsyncClient,
    ):
        """Test that empty tenant returns 404"""
        # This might match a different route, but should not match dynamic tenant route
        response = await async_client.get("//forgot-password")
        # Should return 404 or redirect, not 200
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_307_TEMPORARY_REDIRECT]


@pytest.mark.asyncio
class TestDynamicTenantResetPasswordRoute:
    """Test GET /{tenant_id}/reset-password"""

    async def test_island_parents_reset_password_route(
        self,
        async_client: AsyncClient,
    ):
        """Test dynamic route for island-parents reset password"""
        response = await async_client.get("/island-parents/reset-password")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")

        html_content = response.text
        # Check for reset password form elements
        assert 'id="token"' in html_content or 'name="token"' in html_content
        assert 'id="newPassword"' in html_content or 'name="newPassword"' in html_content

    async def test_career_reset_password_route(
        self,
        async_client: AsyncClient,
    ):
        """Test dynamic route for career reset password"""
        response = await async_client.get("/career/reset-password")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")

        html_content = response.text
        # Check for reset password form elements
        assert 'id="token"' in html_content or 'name="token"' in html_content

    async def test_island_reset_password_route(
        self,
        async_client: AsyncClient,
    ):
        """Test dynamic route for island reset password"""
        response = await async_client.get("/island/reset-password")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")

    async def test_invalid_tenant_reset_password_route(
        self,
        async_client: AsyncClient,
    ):
        """Test that invalid tenant returns 404"""
        response = await async_client.get("/invalid-tenant/reset-password")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower() or "Tenant not found" in data["detail"]

    async def test_reset_password_with_token_query_param(
        self,
        async_client: AsyncClient,
    ):
        """Test reset password route with token query parameter"""
        test_token = "test-token-123"
        response = await async_client.get(f"/island-parents/reset-password?token={test_token}")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        # Token should be auto-filled in the form
        assert test_token in html_content


@pytest.mark.asyncio
class TestBackwardCompatibility:
    """Test backward compatibility with hardcoded routes"""

    async def test_hardcoded_island_parents_forgot_password_still_works(
        self,
        async_client: AsyncClient,
    ):
        """Test that hardcoded /island-parents/forgot-password still works"""
        response = await async_client.get("/island-parents/forgot-password")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        assert 'id="tenant"' in html_content or 'name="tenant"' in html_content
        assert 'value="island_parents"' in html_content or 'island_parents' in html_content

    async def test_hardcoded_island_parents_reset_password_still_works(
        self,
        async_client: AsyncClient,
    ):
        """Test that hardcoded /island-parents/reset-password still works"""
        response = await async_client.get("/island-parents/reset-password")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        assert 'id="token"' in html_content or 'name="token"' in html_content

    async def test_generic_forgot_password_still_works(
        self,
        async_client: AsyncClient,
    ):
        """Test that generic /forgot-password route still works"""
        response = await async_client.get("/forgot-password")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        assert 'id="email"' in html_content or 'name="email"' in html_content

    async def test_generic_reset_password_still_works(
        self,
        async_client: AsyncClient,
    ):
        """Test that generic /reset-password route still works"""
        response = await async_client.get("/reset-password")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        assert 'id="token"' in html_content or 'name="token"' in html_content


@pytest.mark.asyncio
class TestTenantRouteEdgeCases:
    """Test edge cases for tenant routes"""

    async def test_tenant_route_case_sensitivity(
        self,
        async_client: AsyncClient,
    ):
        """Test that tenant routes are case sensitive"""
        # Lowercase should work
        response_lower = await async_client.get("/island-parents/forgot-password")
        assert response_lower.status_code == status.HTTP_200_OK

        # Uppercase should return 404
        response_upper = await async_client.get("/Island-Parents/forgot-password")
        assert response_upper.status_code == status.HTTP_404_NOT_FOUND

    async def test_tenant_route_with_extra_path_segments(
        self,
        async_client: AsyncClient,
    ):
        """Test that tenant routes don't match paths with extra segments"""
        # These should not match the dynamic route pattern
        response1 = await async_client.get("/island-parents/clients/forgot-password")
        # Should match clients route or return 404, not the forgot-password route
        assert response1.status_code != status.HTTP_200_OK or "clients" in response1.text.lower()

    async def test_multiple_valid_tenants(
        self,
        async_client: AsyncClient,
    ):
        """Test that all valid tenants work with dynamic routes"""
        valid_tenants = [
            ("island-parents", "island_parents"),
            ("career", "career"),
            ("island", "island"),
        ]

        for url_tenant, db_tenant in valid_tenants:
            response = await async_client.get(f"/{url_tenant}/forgot-password")
            assert response.status_code == status.HTTP_200_OK, f"{url_tenant} should work"
            html_content = response.text
            assert db_tenant in html_content or 'id="tenant"' in html_content


@pytest.mark.asyncio
class TestTenantRouteContent:
    """Test that tenant-specific routes render correct content"""

    async def test_forgot_password_has_correct_tenant_value(
        self,
        async_client: AsyncClient,
    ):
        """Test that forgot password page has correct tenant value"""
        test_cases = [
            ("island-parents", "island_parents"),
            ("career", "career"),
            ("island", "island"),
        ]

        for url_tenant, db_tenant in test_cases:
            response = await async_client.get(f"/{url_tenant}/forgot-password")
            assert response.status_code == status.HTTP_200_OK

            html_content = response.text
            # Check that tenant value is set correctly (as hidden input or in template)
            assert (
                f'value="{db_tenant}"' in html_content
                or f'"{db_tenant}"' in html_content
                or db_tenant in html_content
            ), f"Tenant {db_tenant} should be present in HTML for {url_tenant}"

    async def test_reset_password_accepts_token_param(
        self,
        async_client: AsyncClient,
    ):
        """Test that reset password route accepts token query parameter"""
        test_token = "test-reset-token-abc123"
        response = await async_client.get(
            f"/island-parents/reset-password?token={test_token}"
        )

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text
        # Token should be auto-filled in the form
        assert test_token in html_content

