"""
Unit tests for RevenueCat service
"""
# Import directly from the module file to avoid triggering app/services/__init__.py
# which would try to connect to the database.
from unittest.mock import MagicMock, patch
from urllib.parse import unquote

import httpx

# Ensure the module is importable without triggering app.services.__init__ chain
import app.services.external.revenuecat_service as _rc_module

delete_customer = _rc_module.delete_customer

# Patch target: the `settings` object imported inside delete_customer
_SETTINGS_PATCH = "app.services.external.revenuecat_service.settings"
_HTTPX_CLIENT_PATCH = "app.services.external.revenuecat_service.httpx.Client"


class TestRevenueCatDeleteCustomer:
    """Tests for revenuecat_service.delete_customer"""

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_delete_customer_success_200(self):
        """Successful delete — API returns 200 — should return True."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = "rc_secret_key_test"

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(
                return_value=mock_client_instance
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_instance.delete.return_value = mock_response

            result = delete_customer(
                "allen@example.com", "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        assert result is True

    def test_delete_customer_success_204(self):
        """Successful delete — API returns 204 — should return True."""
        mock_response = MagicMock()
        mock_response.status_code = 204

        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = "rc_secret_key_test"

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(
                return_value=mock_client_instance
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_instance.delete.return_value = mock_response

            result = delete_customer(
                "allen@example.com", "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        assert result is True

    # ------------------------------------------------------------------
    # API error responses
    # ------------------------------------------------------------------

    def test_delete_customer_api_returns_404(self):
        """API returns 404 — should return False, not raise."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = "rc_secret_key_test"

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(
                return_value=mock_client_instance
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_instance.delete.return_value = mock_response

            result = delete_customer(
                "allen@example.com", "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        assert result is False

    def test_delete_customer_api_returns_500(self):
        """API returns 500 — should return False, not raise."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = "rc_secret_key_test"

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(
                return_value=mock_client_instance
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_instance.delete.return_value = mock_response

            result = delete_customer(
                "allen@example.com", "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        assert result is False

    # ------------------------------------------------------------------
    # Network / exception errors
    # ------------------------------------------------------------------

    def test_delete_customer_network_error(self):
        """Network error (httpx exception) — should return False, not raise."""
        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = "rc_secret_key_test"

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(
                return_value=mock_client_instance
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_instance.delete.side_effect = httpx.ConnectError(
                "Connection refused"
            )

            result = delete_customer(
                "allen@example.com", "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        assert result is False

    def test_delete_customer_timeout_error(self):
        """Timeout error — should return False, not raise."""
        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = "rc_secret_key_test"

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(
                return_value=mock_client_instance
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_instance.delete.side_effect = httpx.TimeoutException(
                "Request timed out"
            )

            result = delete_customer(
                "allen@example.com", "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        assert result is False

    # ------------------------------------------------------------------
    # Missing secret key
    # ------------------------------------------------------------------

    def test_delete_customer_missing_secret_key_none(self):
        """REVENUECAT_SECRET_KEY is None — should return False without making HTTP call."""
        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = None

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            result = delete_customer(
                "allen@example.com", "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        mock_client_cls.assert_not_called()
        assert result is False

    def test_delete_customer_missing_secret_key_empty_string(self):
        """REVENUECAT_SECRET_KEY is empty string — should return False without making HTTP call."""
        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = ""

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            result = delete_customer(
                "allen@example.com", "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            )

        mock_client_cls.assert_not_called()
        assert result is False

    # ------------------------------------------------------------------
    # app_user_id construction and URL encoding
    # ------------------------------------------------------------------

    def test_delete_customer_url_encoding(self):
        """app_user_id is URL-encoded in the request path (@ → %40, | → %7C)."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = "rc_secret_key_test"

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(
                return_value=mock_client_instance
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_instance.delete.return_value = mock_response

            delete_customer("allen@example.com", "a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx")

            call_args = mock_client_instance.delete.call_args
            called_url = call_args[0][0]  # first positional arg

        # '@' → %40, '|' → %7C
        assert (
            "%40" in called_url
        ), f"Expected '@' to be encoded as %40 in URL: {called_url}"
        assert (
            "%7C" in called_url
        ), f"Expected '|' to be encoded as %7C in URL: {called_url}"
        assert "allen" in called_url
        assert "a1b2c3d4" in called_url

    def test_delete_customer_app_user_id_format(self):
        """Verifies the decoded URL path ends with '{email}|{user_id}'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        captured_urls: list = []

        def capture_delete(url, **kwargs):
            captured_urls.append(url)
            return mock_response

        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = "rc_secret_key_test"

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(
                return_value=mock_client_instance
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_instance.delete.side_effect = capture_delete

            delete_customer("user@test.com", "uuid-1234")

        assert len(captured_urls) == 1
        decoded_url = unquote(captured_urls[0])
        # The decoded URL should end with the un-encoded app_user_id
        assert decoded_url.endswith(
            "user@test.com|uuid-1234"
        ), f"Decoded URL did not end with expected app_user_id: {decoded_url}"

    def test_delete_customer_correct_authorization_header(self):
        """The Authorization header uses 'Bearer {secret_key}'."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_settings = MagicMock()
        mock_settings.REVENUECAT_SECRET_KEY = "my_test_secret"

        with patch(_SETTINGS_PATCH, mock_settings), patch(
            _HTTPX_CLIENT_PATCH
        ) as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(
                return_value=mock_client_instance
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_instance.delete.return_value = mock_response

            delete_customer("user@test.com", "uuid-5678")

            call_kwargs = mock_client_instance.delete.call_args[1]
            headers = call_kwargs["headers"]

        assert headers["Authorization"] == "Bearer my_test_secret"
        assert headers["Content-Type"] == "application/json"
