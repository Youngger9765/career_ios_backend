"""
Tenant utility functions for routing and validation

如何新增租戶：
1. 在 VALID_TENANTS 列表中加入新租戶（資料庫格式：snake_case）
2. 在 TENANT_URL_MAP 字典中加入對應的 URL 格式（kebab-case）
3. （可選）在 app/services/external/email_sender.py 的 tenant_names 中加入顯示名稱

範例：新增 "new_tenant" 租戶
  VALID_TENANTS = [..., "new_tenant"]
  TENANT_URL_MAP = {..., "new_tenant": "new-tenant"}

注意：URL 使用連字號（kebab-case），資料庫/程式碼使用底線（snake_case）
"""
from typing import Optional

# Valid tenant IDs (資料庫格式：snake_case)
VALID_TENANTS = ["island_parents", "island", "career"]

# Tenant ID to URL path mapping (URL 格式：kebab-case)
TENANT_URL_MAP = {
    "island_parents": "island-parents",
    "island": "island",
    "career": "career",
}

# Reverse mapping: URL path to tenant ID
URL_TO_TENANT_MAP = {v: k for k, v in TENANT_URL_MAP.items()}

# Validate that VALID_TENANTS and TENANT_URL_MAP are consistent
assert set(VALID_TENANTS) == set(TENANT_URL_MAP.keys()), (
    f"VALID_TENANTS and TENANT_URL_MAP must have the same keys. "
    f"VALID_TENANTS: {VALID_TENANTS}, "
    f"TENANT_URL_MAP keys: {list(TENANT_URL_MAP.keys())}"
)


def validate_tenant(tenant_id: str) -> bool:
    """
    Validate if tenant_id is valid

    Args:
        tenant_id: Tenant ID in database format (snake_case, e.g., "island_parents")

    Returns:
        True if valid, False otherwise
    """
    return tenant_id in VALID_TENANTS


def normalize_tenant_from_url(url_tenant: str) -> Optional[str]:
    """
    Convert URL tenant format (kebab-case) to database format (snake_case)

    Args:
        url_tenant: Tenant ID from URL (e.g., "island-parents")

    Returns:
        Normalized tenant ID (e.g., "island_parents") or None if invalid
    """
    return URL_TO_TENANT_MAP.get(url_tenant)


def get_tenant_url_path(tenant_id: str) -> Optional[str]:
    """
    Convert database tenant format (snake_case) to URL format (kebab-case)

    Args:
        tenant_id: Tenant ID in database format (e.g., "island_parents")

    Returns:
        URL path format (e.g., "island-parents") or None if invalid
    """
    return TENANT_URL_MAP.get(tenant_id)


def detect_tenant_from_path(path: str) -> Optional[str]:
    """
    Extract tenant from URL path

    Args:
        path: URL path (e.g., "/island-parents/login")

    Returns:
        Tenant ID in database format (e.g., "island_parents") or None
    """
    for url_path, tenant_id in URL_TO_TENANT_MAP.items():
        if path.startswith(f"/{url_path}"):
            return tenant_id
    return None

