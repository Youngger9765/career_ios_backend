"""
App Config API
Provides dynamic configuration for iOS client
No authentication required (public endpoint)
"""
from typing import Dict

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.schemas.app_config import AppConfigResponse

router = APIRouter()


# Tenant configuration mapping for scalability
TENANT_CONFIGS: Dict[str, Dict[str, str]] = {
    "island_parents": {
        "terms_url": settings.ISLAND_PARENTS_TERMS_URL,
        "privacy_url": settings.ISLAND_PARENTS_PRIVACY_URL,
        "landing_page_url": settings.ISLAND_PARENTS_LANDING_PAGE_URL,
        "help_url": settings.ISLAND_PARENTS_HELP_URL,
        "forgot_password_url": settings.ISLAND_PARENTS_FORGOT_PASSWORD_URL,
    },
    "career": {
        "terms_url": settings.APP_TERMS_URL,
        "privacy_url": settings.APP_PRIVACY_URL,
        "landing_page_url": settings.APP_LANDING_PAGE_URL,
        "help_url": settings.APP_HELP_URL,
        "forgot_password_url": settings.APP_FORGOT_PASSWORD_URL,
    },
}


@router.get("/config/{tenant}", response_model=AppConfigResponse)
def get_app_config(tenant: str):
    """
    Get app configuration for specific tenant

    - **tenant**: Tenant identifier (e.g., 'island_parents', 'career')

    Returns dynamic URLs and settings for iOS client
    No authentication required - public endpoint
    """
    # Get tenant config or raise 404
    tenant_config = TENANT_CONFIGS.get(tenant)
    if not tenant_config:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant}' not found")

    return AppConfigResponse(
        terms_url=tenant_config["terms_url"],
        privacy_url=tenant_config["privacy_url"],
        landing_page_url=tenant_config["landing_page_url"],
        help_url=tenant_config["help_url"],
        forgot_password_url=tenant_config["forgot_password_url"],
        base_url=settings.APP_BASE_URL,
        version=settings.APP_CONFIG_VERSION,
        maintenance_mode=settings.APP_MAINTENANCE_MODE,
    )
