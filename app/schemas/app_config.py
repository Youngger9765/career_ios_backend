"""
App Config Schemas
"""
from pydantic import BaseModel


class AppConfigResponse(BaseModel):
    """Response schema for app configuration endpoint"""

    terms_url: str
    privacy_url: str
    landing_page_url: str
    help_url: str
    forgot_password_url: str
    base_url: str
    version: str
    maintenance_mode: bool

    model_config = {"from_attributes": True}
