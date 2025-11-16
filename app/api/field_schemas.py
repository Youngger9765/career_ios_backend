"""
Field Schema API - Returns tenant-specific form configurations for iOS
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.config.field_configs import get_field_config
from app.core.deps import get_tenant_id
from app.schemas.field_config import FormSchema

router = APIRouter(prefix="/api/v1/field-schemas", tags=["Field Schemas"])


@router.get("/client", response_model=FormSchema)
def get_client_field_schema(
    tenant_id: str = Depends(get_tenant_id),
) -> FormSchema:
    """
    Get client form field configuration for current tenant

    Returns the complete field schema including:
    - Field types (text, email, select, etc.)
    - Required/optional status
    - Validation rules
    - Display order
    - Help text

    Args:
        tenant_id: Tenant identifier (injected from auth)

    Returns:
        Client form schema configuration

    Raises:
        HTTPException: 404 if tenant configuration not found

    Example Response:
        {
          "form_type": "client",
          "tenant_id": "career",
          "sections": [
            {
              "title": "基本資料",
              "description": "個案基本資訊",
              "order": 1,
              "fields": [
                {
                  "key": "name",
                  "label": "姓名",
                  "type": "text",
                  "required": true,
                  "placeholder": "請輸入真實姓名",
                  "help_text": "使用者的真實姓名",
                  "order": 1
                },
                ...
              ]
            },
            ...
          ]
        }
    """
    try:
        return get_field_config(tenant_id, "client")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/case", response_model=FormSchema)
def get_case_field_schema(
    tenant_id: str = Depends(get_tenant_id),
) -> FormSchema:
    """
    Get case form field configuration for current tenant

    Returns the complete field schema for case creation/editing

    Args:
        tenant_id: Tenant identifier (injected from auth)

    Returns:
        Case form schema configuration

    Raises:
        HTTPException: 404 if tenant configuration not found

    Example Response:
        {
          "form_type": "case",
          "tenant_id": "career",
          "sections": [
            {
              "title": "個案基本資訊",
              "description": "個案編號與狀態",
              "order": 1,
              "fields": [
                {
                  "key": "case_number",
                  "label": "個案編號",
                  "type": "text",
                  "required": true,
                  ...
                }
              ]
            }
          ]
        }
    """
    try:
        return get_field_config(tenant_id, "case")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get("/{form_type}", response_model=FormSchema)
def get_field_schema_by_type(
    form_type: str,
    tenant_id: str = Depends(get_tenant_id),
) -> FormSchema:
    """
    Get field schema for any form type

    Generic endpoint to get field configuration by form type

    Args:
        form_type: Form type ('client' or 'case')
        tenant_id: Tenant identifier (injected from auth)

    Returns:
        Form schema configuration

    Raises:
        HTTPException: 404 if tenant or form type not found
    """
    try:
        return get_field_config(tenant_id, form_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
