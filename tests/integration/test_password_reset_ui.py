"""
Integration tests for Password Reset UI pages

Test Coverage:
1. Forgot Password page (/forgot-password) - GET request
2. Reset Password page (/reset-password) - GET request
3. HTML content verification
4. Form elements verification
"""
import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
class TestForgotPasswordPage:
    """Test GET /forgot-password"""

    async def test_forgot_password_page_loads(
        self,
        async_client: AsyncClient,
    ):
        """Test that forgot password page loads successfully"""
        response = await async_client.get("/forgot-password")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")

    async def test_forgot_password_page_has_form(
        self,
        async_client: AsyncClient,
    ):
        """Test that forgot password page contains the required form elements"""
        response = await async_client.get("/forgot-password")

        html_content = response.text
        assert response.status_code == status.HTTP_200_OK

        # Check for form elements
        assert 'name="email"' in html_content or 'id="email"' in html_content
        assert 'name="tenant"' in html_content or 'id="tenant"' in html_content
        assert 'type="submit"' in html_content or "button" in html_content.lower()

        # Check for tenant options
        assert "career" in html_content
        assert "island" in html_content
        assert "test_tenant" in html_content

    async def test_forgot_password_page_has_title(
        self,
        async_client: AsyncClient,
    ):
        """Test that forgot password page has appropriate title"""
        response = await async_client.get("/forgot-password")

        html_content = response.text
        assert response.status_code == status.HTTP_200_OK

        # Check for page title (should contain password reset related text)
        assert "<title>" in html_content
        title_lower = html_content.lower()
        assert "password" in title_lower or "密碼" in html_content

    async def test_forgot_password_page_has_api_endpoint(
        self,
        async_client: AsyncClient,
    ):
        """Test that forgot password page references the correct API endpoint"""
        response = await async_client.get("/forgot-password")

        html_content = response.text
        assert response.status_code == status.HTTP_200_OK

        # Check for API endpoint reference
        assert "/api/v1/auth/password-reset/request" in html_content


@pytest.mark.asyncio
class TestResetPasswordPage:
    """Test GET /reset-password"""

    async def test_reset_password_page_loads(
        self,
        async_client: AsyncClient,
    ):
        """Test that reset password page loads successfully"""
        response = await async_client.get("/reset-password")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"].startswith("text/html")

    async def test_reset_password_page_has_form(
        self,
        async_client: AsyncClient,
    ):
        """Test that reset password page contains the required form elements"""
        response = await async_client.get("/reset-password")

        html_content = response.text
        assert response.status_code == status.HTTP_200_OK

        # Check for form elements
        assert 'name="token"' in html_content or 'id="token"' in html_content
        assert (
            'name="newPassword"' in html_content
            or 'id="newPassword"' in html_content
            or 'name="password"' in html_content
        )
        assert 'type="submit"' in html_content or "button" in html_content.lower()

        # Check for password type input
        assert 'type="password"' in html_content

    async def test_reset_password_page_has_title(
        self,
        async_client: AsyncClient,
    ):
        """Test that reset password page has appropriate title"""
        response = await async_client.get("/reset-password")

        html_content = response.text
        assert response.status_code == status.HTTP_200_OK

        # Check for page title
        assert "<title>" in html_content
        title_lower = html_content.lower()
        assert "password" in title_lower or "密碼" in html_content

    async def test_reset_password_page_has_api_endpoint(
        self,
        async_client: AsyncClient,
    ):
        """Test that reset password page references the correct API endpoint"""
        response = await async_client.get("/reset-password")

        html_content = response.text
        assert response.status_code == status.HTTP_200_OK

        # Check for API endpoint reference
        assert "/api/v1/auth/password-reset/confirm" in html_content

    async def test_reset_password_page_with_token_query_param(
        self,
        async_client: AsyncClient,
    ):
        """Test that reset password page accepts token as query parameter"""
        test_token = "test_token_12345"
        response = await async_client.get(f"/reset-password?token={test_token}")

        assert response.status_code == status.HTTP_200_OK
        html_content = response.text

        # Page should have JavaScript to handle token query parameter
        assert "URLSearchParams" in html_content
        assert "token" in html_content.lower()


@pytest.mark.asyncio
class TestPasswordResetUIFlow:
    """End-to-end UI flow tests"""

    async def test_forgot_password_to_reset_password_flow(
        self,
        async_client: AsyncClient,
    ):
        """Test that both pages load and have consistent styling"""
        # Load forgot password page
        response1 = await async_client.get("/forgot-password")
        assert response1.status_code == status.HTTP_200_OK
        html1 = response1.text

        # Load reset password page
        response2 = await async_client.get("/reset-password")
        assert response2.status_code == status.HTTP_200_OK
        html2 = response2.text

        # Both should use Tailwind CSS (consistent styling)
        assert "tailwindcss" in html1.lower() or "tailwind" in html1.lower()
        assert "tailwindcss" in html2.lower() or "tailwind" in html2.lower()

        # Both should be mobile-friendly (viewport meta tag)
        assert "viewport" in html1.lower()
        assert "viewport" in html2.lower()

    async def test_forgot_password_page_has_instructions(
        self,
        async_client: AsyncClient,
    ):
        """Test that forgot password page has user instructions"""
        response = await async_client.get("/forgot-password")

        html_content = response.text.lower()
        assert response.status_code == status.HTTP_200_OK

        # Should have some instructional text
        assert "email" in html_content

    async def test_reset_password_page_has_password_requirements(
        self,
        async_client: AsyncClient,
    ):
        """Test that reset password page shows password requirements"""
        response = await async_client.get("/reset-password")

        html_content = response.text.lower()
        assert response.status_code == status.HTTP_200_OK

        # Should mention minimum length requirement
        assert "8" in html_content or "eight" in html_content
