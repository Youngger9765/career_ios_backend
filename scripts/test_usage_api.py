#!/usr/bin/env python3
"""
Test usage stats API endpoint after migration.
"""
import requests
from pprint import pprint

BASE_URL = "http://localhost:8000/api"
USAGE_API_BASE = "http://localhost:8000/api/v1"

def test_usage_stats():
    """Test usage stats endpoint with migrated account"""

    # Login
    print("Logging in...")
    # Try test account
    test_accounts = [
        {"email": "migration-test@example.com", "password": "test123456", "tenant_id": "career"},
    ]

    login_response = None
    for account in test_accounts:
        print(f"Trying {account['email']}...")
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json=account
        )
        if response.status_code == 200:
            login_response = response
            print(f"✅ Login successful with {account['email']}")
            break

    if not login_response:

        print(f"❌ All login attempts failed")
        return

    token = login_response.json()["access_token"]

    # Get usage stats
    print("\nFetching usage stats...")
    stats_response = requests.get(
        f"{USAGE_API_BASE}/usage/stats",
        headers={"Authorization": f"Bearer {token}"}
    )

    if stats_response.status_code != 200:
        print(f"❌ Failed to get stats: {stats_response.status_code}")
        print(stats_response.text)
        return

    stats = stats_response.json()
    print("✅ Usage stats retrieved successfully\n")

    print("="*60)
    print("Usage Stats for purpleice9765@msn.com (career)")
    print("="*60)
    pprint(stats)

    # Verify expected values
    print("\n" + "="*60)
    print("Verification")
    print("="*60)

    checks = [
        ("billing_mode", "subscription", stats.get("billing_mode")),
        ("monthly_limit_minutes", 360, stats.get("monthly_limit_minutes")),
        ("monthly_used_minutes", 0, stats.get("monthly_used_minutes")),
    ]

    all_passed = True
    for field, expected, actual in checks:
        passed = actual == expected
        all_passed = all_passed and passed
        status = "✅" if passed else "❌"
        print(f"{status} {field}: expected={expected}, actual={actual}")

    if all_passed:
        print("\n✅ All checks passed! Migration successful.")
    else:
        print("\n❌ Some checks failed. Please investigate.")

if __name__ == "__main__":
    test_usage_stats()
