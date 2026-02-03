"""
Password strength validation module.

Enforces strong password requirements to prevent weak passwords
and common password attacks.
"""

import re
from typing import List

# Top 20 most common passwords to block
COMMON_PASSWORDS = {
    "password123!",
    "qwerty123!",
    "admin123!",
    "welcome123!",
    "letmein123!",
    "password1!",
    "123456",
    "password",
    "12345678",
    "qwerty",
    "123456789",
    "12345",
    "1234",
    "111111",
    "1234567",
    "dragon",
    "123123",
    "baseball",
    "abc123",
    "football",
}


def validate_password_strength(password: str) -> None:
    """
    Validate password strength requirements.

    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Not a common password

    Args:
        password: The password to validate

    Raises:
        ValueError: If password does not meet requirements, with detailed error message
    """
    errors: List[str] = []

    # Check minimum length
    if len(password) < 12:
        errors.append("Password must be at least 12 characters long")

    # Check for uppercase
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    # Check for lowercase
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    # Check for digit
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    # Check for special character
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};"\'\\|,.<>?/~`]', password):
        errors.append("Password must contain at least one special character")

    # Check against common passwords (case-insensitive)
    if password.lower() in COMMON_PASSWORDS:
        errors.append("Password is too common. Please choose a more unique password")

    if errors:
        error_message = "Password validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        raise ValueError(error_message)
