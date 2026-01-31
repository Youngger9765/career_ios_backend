"""
App Config API
Provides dynamic configuration for iOS client
No authentication required (public endpoint)
"""
from fastapi import APIRouter

from app.core.config import settings
from app.schemas.app_config import AppConfigResponse

router = APIRouter()


@router.get("/config", response_model=AppConfigResponse)
def get_app_config():
    """
    Get app configuration

    Returns dynamic URLs and settings for iOS client
    No authentication required - public endpoint
    """
    return AppConfigResponse(
        terms_url=settings.APP_TERMS_URL,
        privacy_url=settings.APP_PRIVACY_URL,
        landing_page_url=settings.APP_LANDING_PAGE_URL,
        help_url=settings.APP_HELP_URL,
        forgot_password_url=settings.APP_FORGOT_PASSWORD_URL,
        base_url=settings.APP_BASE_URL,
        version=settings.APP_CONFIG_VERSION,
        maintenance_mode=settings.APP_MAINTENANCE_MODE,
    )
