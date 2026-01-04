"""
UI-Driven API for Client-Case List
客戶個案列表 - 結合 Client + Case + Session 資料，優化前端顯示
Refactored: Business logic moved to ClientCaseService, schemas to ui_client_case.py
"""
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.counselor import Counselor
from app.schemas.ui_client_case import (
    FIELD_LABELS,
    ClientCaseDetailResponse,
    ClientCaseListItem,
    ClientCaseListResponse,
    CreateClientCaseRequest,
    CreateClientCaseResponse,
    UpdateClientCaseRequest,
    validate_client_case_by_tenant,
)
from app.services.client_case_service import ClientCaseService

router = APIRouter(prefix="/api/v1/ui", tags=["UI APIs"])


# ============================================================================
# API Endpoints
# ============================================================================


@router.post(
    "/client-case",
    response_model=CreateClientCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="創建客戶與個案（多租戶動態欄位）",
)
def create_client_and_case(
    request: CreateClientCaseRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> CreateClientCaseResponse:
    """
    Create client and case atomically

    必填欄位根據租戶不同：
    - career: name, email, gender, birth_date, phone, identity_option, current_status
    - island: name, email, phone, gender, birth_date, identity_option, current_status
    - island_parents: name, grade, relationship (其他都選填)
    """
    try:
        # 根據租戶驗證必填欄位
        request_data = request.model_dump()
        missing_fields = validate_client_case_by_tenant(request_data, tenant_id)

        if missing_fields:
            # 轉換成中文欄位名稱
            missing_labels = [FIELD_LABELS.get(f, f) for f in missing_fields]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"缺少必填欄位：{', '.join(missing_labels)}",
            )

        service = ClientCaseService(db)

        # Island Parents 特有欄位存到 other_info JSON
        other_info = {}
        if request.grade:
            other_info["grade"] = request.grade
        if request.relationship:
            other_info["relationship"] = request.relationship

        # 為 island_parents 租戶設定默認值（避免 NOT NULL 約束失敗）
        gender = request.gender
        birth_date = request.birth_date
        phone = request.phone
        identity_option = request.identity_option
        current_status = request.current_status

        if tenant_id == "island_parents":
            # 設定默認值給資料庫必填但親子版選填的欄位
            gender = gender or "不願透露"
            birth_date = birth_date or __import__("datetime").date(2015, 1, 1)
            phone = phone or "0000000000"
            identity_option = identity_option or "其他"
            current_status = current_status or "親子對話"

        # Prepare client data
        client_data = {
            "name": request.name,
            "email": request.email,
            "gender": gender,
            "birth_date": birth_date,
            "phone": phone,
            "identity_option": identity_option,
            "current_status": current_status,
            "education": request.education,
            "current_job": request.current_job,
            "career_status": request.career_status,
            "has_consultation_history": request.has_consultation_history,
            "has_mental_health_history": request.has_mental_health_history,
            "location": request.location,
            "notes": request.notes,
            "other_info": other_info if other_info else None,
        }

        # Prepare case data
        case_data = {
            "summary": request.case_summary,
            "goals": request.case_goals,
            "problem_description": request.problem_description,
        }

        client, case = service.create_client_and_case(
            tenant_id=tenant_id,
            counselor=current_user,
            client_data=client_data,
            case_data=case_data,
        )

        status_value = (
            case.status if isinstance(case.status, int) else case.status.value
        )

        return CreateClientCaseResponse(
            client_id=client.id,
            client_code=client.code,
            client_name=client.name,
            client_email=client.email,
            case_id=case.id,
            case_number=case.case_number,
            case_status=status_value,
            created_at=client.created_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create client and case: {str(e)}",
        )


@router.get(
    "/client-case-list",
    response_model=ClientCaseListResponse,
    summary="列出所有客戶個案（iOS 使用）",
)
def get_client_case_list(
    skip: int = Query(0, ge=0, description="跳過筆數"),
    limit: int = Query(100, ge=1, le=500, description="每頁筆數"),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ClientCaseListResponse:
    """List all client-cases with session stats"""
    service = ClientCaseService(db)
    items_data, total = service.list_client_cases(
        tenant_id=tenant_id,
        counselor_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    # Convert dict items to Pydantic models
    items = [ClientCaseListItem(**item) for item in items_data]

    return ClientCaseListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/client-case/{case_id}", response_model=ClientCaseDetailResponse)
def get_client_case_detail(
    case_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ClientCaseDetailResponse:
    """Get single client-case detail"""
    try:
        service = ClientCaseService(db)
        detail = service.get_client_case_detail(
            case_id=case_id, tenant_id=tenant_id, counselor_id=current_user.id
        )
        return ClientCaseDetailResponse(**detail)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get client-case detail: {str(e)}",
        )


@router.patch("/client-case/{case_id}", response_model=CreateClientCaseResponse)
def update_client_and_case(
    case_id: UUID,
    request: UpdateClientCaseRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> CreateClientCaseResponse:
    """Update client and case data"""
    try:
        service = ClientCaseService(db)

        # Prepare client updates (only non-None fields)
        client_updates = {
            k: v
            for k, v in {
                "name": request.name,
                "email": request.email,
                "gender": request.gender,
                "birth_date": request.birth_date,
                "phone": request.phone,
                "identity_option": request.identity_option,
                "current_status": request.current_status,
                "education": request.education,
                "current_job": request.current_job,
                "career_status": request.career_status,
                "has_consultation_history": request.has_consultation_history,
                "has_mental_health_history": request.has_mental_health_history,
                "location": request.location,
                "notes": request.notes,
            }.items()
            if v is not None
        }

        # Prepare case updates
        case_updates = {
            k: v
            for k, v in {
                "status": request.case_status,
                "summary": request.case_summary,
                "goals": request.case_goals,
                "problem_description": request.problem_description,
            }.items()
            if v is not None
        }

        client, case = service.update_client_and_case(
            case_id=case_id,
            tenant_id=tenant_id,
            counselor_id=current_user.id,
            client_updates=client_updates if client_updates else None,
            case_updates=case_updates if case_updates else None,
        )

        status_value = (
            case.status if isinstance(case.status, int) else case.status.value
        )

        return CreateClientCaseResponse(
            client_id=client.id,
            client_code=client.code,
            client_name=client.name,
            client_email=client.email,
            case_id=case.id,
            case_number=case.case_number,
            case_status=status_value,
            created_at=client.created_at,
            message="客戶與個案更新成功",
        )

    except ValueError as e:
        error_msg = str(e)
        # Differentiate between not found and bad input
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update client and case: {str(e)}",
        )


@router.delete("/client-case/{case_id}", status_code=status.HTTP_200_OK)
def delete_client_case(
    case_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Soft-delete case (client remains)"""
    try:
        service = ClientCaseService(db)
        return service.delete_case(
            case_id=case_id,
            tenant_id=tenant_id,
            counselor=current_user,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete case: {str(e)}",
        )
