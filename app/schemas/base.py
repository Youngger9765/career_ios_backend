from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class BaseSchema(BaseModel):
    class Config:
        from_attributes = True


class BaseResponse(BaseSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime | None = None