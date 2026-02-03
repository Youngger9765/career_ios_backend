"""
Unit tests for verification code generation utility
"""
import pytest

from app.utils.verification_code import generate_verification_code


class TestVerificationCodeGeneration:
    """Test verification code generation"""

    def test_code_length(self):
        """Test that generated code is exactly 6 digits"""
        code = generate_verification_code()
        assert len(code) == 6

    def test_code_numeric(self):
        """Test that generated code contains only digits"""
        code = generate_verification_code()
        assert code.isdigit()

    def test_code_uniqueness(self):
        """Test that multiple generated codes are different"""
        codes = [generate_verification_code() for _ in range(100)]
        unique_codes = set(codes)
        # At least 95% should be unique (allowing for rare collisions)
        assert len(unique_codes) >= 95

    def test_code_range(self):
        """Test that code is in valid range (000000-999999)"""
        for _ in range(10):
            code = generate_verification_code()
            code_int = int(code)
            assert 0 <= code_int <= 999999
