"""
App Config Schemas
"""
from pydantic import BaseModel


class AppConfigResponse(BaseModel):
    """Response schema for app configuration endpoint"""

    terms_url: str
    privacy_url: str
    landing_page_url: str
    data_usage_url: str
    help_url: str
    faq_url: str
    contact_url: str

    model_config = {"from_attributes": True}
