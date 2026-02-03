"""
Verification code generation utility

Generates cryptographically secure 6-digit verification codes.
"""
import secrets


def generate_verification_code() -> str:
    """
    Generate a cryptographically secure 6-digit verification code.

    Uses secrets.randbelow() for cryptographic strength, ensuring uniform
    distribution across the entire 000000-999999 range.

    Returns:
        str: 6-digit code (zero-padded if necessary)

    Example:
        >>> code = generate_verification_code()
        >>> len(code)
        6
        >>> code.isdigit()
        True
    """
    # Generate random number from 0 to 999999
    code_int = secrets.randbelow(1_000_000)

    # Zero-pad to ensure 6 digits (e.g., 123 -> "000123")
    return f"{code_int:06d}"
