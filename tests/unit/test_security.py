"""
Unit tests for security functions (password hashing, JWT tokens)
TDD - Write tests first, then implement
"""
from datetime import datetime, timedelta

from jose import jwt


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password_returns_different_hash(self):
        """Hashing same password twice should return different hashes (salt)"""
        from app.core.security import hash_password

        password = "test_password_123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert hash1 != password
        assert hash2 != password

    def test_verify_password_correct(self):
        """Verify correct password returns True"""
        from app.core.security import hash_password, verify_password

        password = "correct_password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Verify incorrect password returns False"""
        from app.core.security import hash_password, verify_password

        password = "correct_password"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False


class TestJWTTokens:
    """Test JWT token creation and validation"""

    def test_create_access_token(self):
        """Create access token with user data"""
        from app.core.security import create_access_token

        data = {"sub": "user@example.com", "tenant_id": "career"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiration(self):
        """Create token with custom expiration"""
        from app.core.security import create_access_token

        data = {"sub": "user@example.com"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)

        # Decode to check expiration
        from app.core.config import Settings

        settings = Settings()
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        assert "exp" in payload
        # Check expiration exists and is a future timestamp
        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.now()  # Use local time to match fromtimestamp
        time_diff = (exp_time - now).total_seconds()
        # Should be close to 15 minutes (900 seconds), allow wider tolerance
        assert 850 < time_diff < 950  # ~15 minutes (with tolerance for execution time)

    def test_decode_valid_token(self):
        """Decode valid token returns payload"""
        from app.core.security import create_access_token, decode_token

        data = {"sub": "user@example.com", "tenant_id": "career"}
        token = create_access_token(data)

        payload = decode_token(token)

        assert payload is not None
        assert payload["sub"] == "user@example.com"
        assert payload["tenant_id"] == "career"

    def test_decode_invalid_token(self):
        """Decode invalid token returns None"""
        from app.core.security import decode_token

        invalid_token = "invalid.token.here"
        payload = decode_token(invalid_token)

        assert payload is None

    def test_decode_expired_token(self):
        """Decode expired token returns None"""
        from app.core.security import create_access_token, decode_token

        data = {"sub": "user@example.com"}
        # Create token that expires immediately
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))

        payload = decode_token(token)

        assert payload is None
