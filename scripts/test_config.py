"""
Central Configuration for Test Scripts

Re-exports settings from app.core.config for consistency.
All test scripts should import from here instead of duplicating config.

Usage:
    from test_config import settings, API_BASE_URL
"""

import sys
from pathlib import Path

# Add project root to path to allow importing app module
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings  # noqa: E402

# Common test configurations
API_BASE_URL_STAGING = "https://career-app-api-staging-kxaznpplqq-uc.a.run.app/api/v1"
API_BASE_URL_LOCAL = "http://localhost:8000/api/v1"

# Default to staging for test scripts
API_BASE_URL = API_BASE_URL_STAGING

# Re-export settings for convenience
__all__ = ["settings", "API_BASE_URL", "API_BASE_URL_STAGING", "API_BASE_URL_LOCAL"]
