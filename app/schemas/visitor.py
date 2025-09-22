from typing import Optional, List
from app.schemas.base import BaseSchema, BaseResponse


class VisitorBase(BaseSchema):
    code: str
    nickname: Optional[str] = None
    age_range: Optional[str] = None
    gender: Optional[str] = None
    tags: List[str] = []
    notes: Optional[str] = None


class VisitorCreate(VisitorBase):
    pass


class VisitorUpdate(BaseSchema):
    nickname: Optional[str] = None
    age_range: Optional[str] = None
    gender: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class VisitorResponse(BaseResponse, VisitorBase):
    pass