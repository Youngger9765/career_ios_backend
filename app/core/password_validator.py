"""
Password validation module.

Rules: minimum 8 characters, at least one letter, at least one digit.
No uppercase or special character requirement.
"""

import re
from typing import Any, Dict, List

# Common passwords to block (case-insensitive check)
COMMON_PASSWORDS = {
    "password123",
    "qwerty123",
    "admin123",
    "welcome123",
    "letmein123",
    "password1",
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


def get_password_rules() -> Dict[str, Any]:
    """Return current password rules for client display."""
    return {
        "min_length": 8,
        "require_letter": True,
        "require_digit": True,
        "require_uppercase": False,
        "require_special_char": False,
    }


def check_password_rules(password: str) -> Dict[str, Any]:
    """
    Check password against all rules and return structured result.

    Returns dict with: valid, rules, checks
    """
    checks: List[Dict[str, Any]] = []

    checks.append({
        "rule": "min_length",
        "message": "Password must be at least 8 characters",
        "passed": len(password) >= 8,
    })

    checks.append({
        "rule": "require_letter",
        "message": "Password must contain at least one letter (a-z)",
        "passed": bool(re.search(r"[a-zA-Z]", password)),
    })

    checks.append({
        "rule": "require_digit",
        "message": "Password must contain at least one digit (0-9)",
        "passed": bool(re.search(r"\d", password)),
    })

    checks.append({
        "rule": "not_common",
        "message": "Password must not be a commonly used password",
        "passed": password.lower() not in COMMON_PASSWORDS,
    })

    all_passed = all(c["passed"] for c in checks)

    return {
        "valid": all_passed,
        "rules": get_password_rules(),
        "checks": checks,
    }


def validate_password_strength(password: str) -> None:
    """
    Validate password strength. Raises ValueError if invalid.

    Used by Pydantic field validators for backwards compatibility.

    Rules:
    - Minimum 8 characters
    - At least one letter (a-z, case insensitive)
    - At least one digit (0-9)
    - Not a common password

    Args:
        password: The password to validate

    Raises:
        ValueError: If password does not meet requirements
    """
    result = check_password_rules(password)
    if not result["valid"]:
        failed = [c["message"] for c in result["checks"] if not c["passed"]]
        raise ValueError(
            "Password validation failed: " + "; ".join(failed)
        )
