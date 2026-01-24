"""
Unit tests for tenant utility functions
"""
import pytest

from app.utils.tenant import (
    VALID_TENANTS,
    detect_tenant_from_path,
    get_tenant_url_path,
    normalize_tenant_from_url,
    validate_tenant,
)


class TestValidateTenant:
    """Test validate_tenant function"""

    def test_validate_valid_tenants(self):
        """Test that all valid tenants pass validation"""
        for tenant in VALID_TENANTS:
            assert validate_tenant(tenant) is True, f"{tenant} should be valid"

    def test_validate_invalid_tenant(self):
        """Test that invalid tenants fail validation"""
        invalid_tenants = ["invalid", "unknown", "test", "", "none"]
        for tenant in invalid_tenants:
            assert validate_tenant(tenant) is False, f"{tenant} should be invalid"

    def test_validate_case_sensitive(self):
        """Test that validation is case sensitive"""
        assert validate_tenant("island_parents") is True
        assert validate_tenant("Island_Parents") is False
        assert validate_tenant("ISLAND_PARENTS") is False


class TestDetectTenantFromPath:
    """Test detect_tenant_from_path function"""

    def test_detect_tenant_from_valid_paths(self):
        """Test detecting tenant from valid URL paths"""
        test_cases = [
            ("/island-parents/login", "island_parents"),
            ("/island-parents/forgot-password", "island_parents"),
            ("/island-parents/reset-password", "island_parents"),
            ("/island-parents/clients", "island_parents"),
            ("/career/login", "career"),
            ("/career/forgot-password", "career"),
            ("/island/session", "island"),
            ("/island/mode", "island"),
        ]
        for path, expected_tenant in test_cases:
            result = detect_tenant_from_path(path)
            assert result == expected_tenant, f"{path} should detect {expected_tenant}"

    def test_detect_tenant_from_invalid_paths(self):
        """Test detecting tenant from invalid paths returns None"""
        invalid_paths = [
            "/invalid/login",
            "/unknown/path",
            "/",
            "/api/v1/auth/login",
            "/forgot-password",  # Generic path without tenant
            "/reset-password",  # Generic path without tenant
        ]
        for path in invalid_paths:
            result = detect_tenant_from_path(path)
            assert result is None, f"{path} should return None"

    def test_normalize_tenant_from_url(self):
        """Test normalization of URL format to database format"""
        test_cases = [
            ("island-parents", "island_parents"),
            ("career", "career"),
            ("island", "island"),
        ]
        for url_tenant, expected_db_tenant in test_cases:
            result = normalize_tenant_from_url(url_tenant)
            assert result == expected_db_tenant, f"{url_tenant} should normalize to {expected_db_tenant}"

    def test_get_tenant_url_path(self):
        """Test getting URL path from database format"""
        test_cases = [
            ("island_parents", "island-parents"),
            ("career", "career"),
            ("island", "island"),
        ]
        for db_tenant, expected_url_path in test_cases:
            result = get_tenant_url_path(db_tenant)
            assert result == expected_url_path, f"{db_tenant} should map to {expected_url_path}"

    def test_detect_tenant_path_prefix_matching(self):
        """Test that path detection uses prefix matching"""
        # Should match even with additional path segments
        assert detect_tenant_from_path("/island-parents/clients/123/edit") == "island_parents"
        assert detect_tenant_from_path("/career/reports/abc") == "career"
        assert detect_tenant_from_path("/island/session/xyz/mode") == "island"

    def test_detect_tenant_case_sensitive(self):
        """Test that path detection is case sensitive"""
        assert detect_tenant_from_path("/island-parents/login") == "island_parents"
        assert detect_tenant_from_path("/Island-Parents/login") is None
        assert detect_tenant_from_path("/ISLAND-PARENTS/login") is None


class TestTenantUtilsIntegration:
    """Integration tests for tenant utility functions"""

    def test_round_trip_conversion(self):
        """Test that URL format and DB format can be converted back and forth"""
        test_cases = [
            ("island_parents", "island-parents"),
            ("career", "career"),
            ("island", "island"),
        ]
        for db_tenant, url_tenant in test_cases:
            # DB → URL
            url_result = get_tenant_url_path(db_tenant)
            assert url_result == url_tenant, f"DB {db_tenant} → URL should be {url_tenant}"

            # URL → DB
            db_result = normalize_tenant_from_url(url_tenant)
            assert db_result == db_tenant, f"URL {url_tenant} → DB should be {db_tenant}"

            # Validate both formats
            assert validate_tenant(db_tenant) is True, f"DB format {db_tenant} should be valid"
            assert validate_tenant(normalize_tenant_from_url(url_tenant)) is True, f"URL format {url_tenant} should be valid after normalization"

    def test_path_detection_with_validation(self):
        """Test that path detection works with validation"""
        paths = [
            "/island-parents/login",
            "/career/forgot-password",
            "/island/reset-password",
        ]
        for path in paths:
            detected = detect_tenant_from_path(path)
            assert detected is not None, f"Should detect tenant from {path}"
            assert validate_tenant(detected) is True, f"Detected tenant {detected} should be valid"

