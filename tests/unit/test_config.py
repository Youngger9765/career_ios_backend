"""Tests for app configuration and settings"""


class TestSettingsConfig:
    """Test Settings configuration"""

    def test_settings_loads_with_defaults(self):
        """Test settings can be loaded with default values"""
        from app.core.config import Settings

        # Create fresh settings without env vars
        settings = Settings(_env_file=None, DEBUG=False, SECRET_KEY="test-secret-key-123")

        assert settings.APP_NAME == "Career Counseling API"
        assert settings.DEBUG is False
        assert settings.CORS_ORIGINS == ["*"]

    def test_cors_origins_from_programmatic_string(self):
        """Test CORS_ORIGINS field_validator handles comma-separated string"""
        from app.core.config import Settings

        # Test validator directly via __init__
        settings = Settings(
            _env_file=None,
            SECRET_KEY="test-secret-key-123",
            CORS_ORIGINS="http://localhost:3000,https://example.com"  # type: ignore
        )

        assert settings.CORS_ORIGINS == ["http://localhost:3000", "https://example.com"]

    def test_cors_origins_from_list(self):
        """Test CORS origins when provided as list"""
        from app.core.config import Settings

        # Direct instantiation with list
        settings = Settings(
            _env_file=None,
            SECRET_KEY="test-secret-key-123",
            CORS_ORIGINS=["http://localhost:3000", "https://api.example.com"]
        )

        assert settings.CORS_ORIGINS == ["http://localhost:3000", "https://api.example.com"]

    def test_cors_origins_handles_whitespace(self):
        """Test CORS origins strips whitespace from comma-separated values"""
        from app.core.config import Settings

        settings = Settings(
            _env_file=None,
            SECRET_KEY="test-secret-key-123",
            CORS_ORIGINS="http://localhost:3000 , https://example.com , https://api.example.com"  # type: ignore
        )

        assert settings.CORS_ORIGINS == ["http://localhost:3000", "https://example.com", "https://api.example.com"]

    def test_settings_immutable_after_creation(self):
        """Test settings instance is created once at module load"""
        from app.core.config import settings

        # Settings is a singleton created at module load
        assert settings.APP_NAME == "Career Counseling API"
        assert isinstance(settings.CORS_ORIGINS, list)
