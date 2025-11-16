"""
Field configuration schemas for dynamic form generation
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Field input types"""
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    TEXTAREA = "textarea"
    NUMBER = "number"
    BOOLEAN = "boolean"


class FieldSchema(BaseModel):
    """Individual field configuration"""

    key: str = Field(..., description="Field key (matches model field)")
    label: str = Field(..., description="Display label")
    type: FieldType = Field(..., description="Input type")
    required: bool = Field(default=False, description="Whether field is required")
    placeholder: Optional[str] = Field(None, description="Placeholder text")
    options: Optional[List[str]] = Field(None, description="Options for select fields")
    default_value: Optional[Any] = Field(None, description="Default value")
    help_text: Optional[str] = Field(None, description="Help text or description")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Validation rules")
    order: int = Field(default=0, description="Display order")


class FieldSection(BaseModel):
    """Group of related fields"""

    title: str = Field(..., description="Section title")
    description: Optional[str] = Field(None, description="Section description")
    fields: List[FieldSchema] = Field(..., description="Fields in this section")
    order: int = Field(default=0, description="Section display order")


class FormSchema(BaseModel):
    """Complete form configuration"""

    form_type: str = Field(..., description="Form type: client or case")
    tenant_id: str = Field(..., description="Tenant identifier")
    sections: List[FieldSection] = Field(..., description="Form sections")
