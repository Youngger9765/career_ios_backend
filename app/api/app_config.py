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
        "data_usage_url": settings.ISLAND_PARENTS_DATA_USAGE_URL,
        "help_url": settings.ISLAND_PARENTS_HELP_URL,
        "faq_url": settings.ISLAND_PARENTS_FAQ_URL,
        "contact_url": settings.ISLAND_PARENTS_CONTACT_URL,
    },
    "career": {
        "terms_url": settings.APP_TERMS_URL,
        "privacy_url": settings.APP_PRIVACY_URL,
        "landing_page_url": settings.APP_LANDING_PAGE_URL,
        "data_usage_url": settings.APP_DATA_USAGE_URL,
        "help_url": settings.APP_HELP_URL,
        "faq_url": settings.APP_FAQ_URL,
        "contact_url": settings.APP_CONTACT_URL,
    },
}


@router.get("/config/{tenant}", response_model=AppConfigResponse)
def get_app_config(tenant: str):
    """
    Get app configuration for specific tenant

    - **tenant**: Tenant identifier (e.g., 'island_parents', 'career')

    Returns essential URLs for iOS client:
    - terms_url: Terms of Service URL
    - privacy_url: Privacy Policy URL
    - landing_page_url: Marketing/Landing page URL
    - data_usage_url: Data Usage Guide URL
    - help_url: User Guide / Help URL
    - faq_url: FAQ (Frequently Asked Questions) URL
    - contact_url: Contact Us URL

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
        data_usage_url=tenant_config["data_usage_url"],
        help_url=tenant_config["help_url"],
        faq_url=tenant_config["faq_url"],
        contact_url=tenant_config["contact_url"],
    )
