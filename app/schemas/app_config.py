"""
App Config Schemas
"""
from pydantic import BaseModel


class AppConfigResponse(BaseModel):
    """Response schema for app configuration endpoint - simplified to 3 fields only"""

    terms_url: str
    privacy_url: str
    landing_page_url: str

    model_config = {"from_attributes": True}
