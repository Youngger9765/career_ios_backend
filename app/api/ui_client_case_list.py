"""
UI-Driven API for Client-Case List
客戶個案列表 - 結合 Client + Case + Session 資料，優化前端顯示
"""
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.case import Case, CaseStatus
from app.models.client import Client
from app.models.counselor import Counselor
from app.models.session import Session as SessionModel

router = APIRouter(prefix="/api/v1/ui", tags=["UI APIs"])


# ============================================================================
# Request/Response Models (UI-Optimized)
# ============================================================================


class CreateClientCaseRequest(BaseModel):
    """建立客戶+個案請求（UI 友善版本）"""

    # Client 必填欄位
    name: str = Field(..., min_length=1, max_length=100, description="客戶姓名")
    email: EmailStr = Field(..., description="Email")
    gender: str = Field(..., description="性別：男/女/其他/不便透露")
    birth_date: date = Field(..., description="生日（西元年）")
    phone: str = Field(..., description="手機號碼")
    identity_option: str = Field(..., description="身份選項（學生/社會新鮮人/轉職者/在職者/其他）")
    current_status: str = Field(..., description="目前現況")

    # Client 選填欄位
    nickname: Optional[str] = Field(None, description="暱稱")
    notes: Optional[str] = Field(None, description="備註")
    education: Optional[str] = Field(None, description="學歷")
    occupation: Optional[str] = Field(None, description="職業")
    location: Optional[str] = Field(None, description="地點")

    # Case 選填欄位
    case_summary: Optional[str] = Field(None, description="個案摘要")
    case_goals: Optional[str] = Field(None, description="個案目標")
    problem_description: Optional[str] = Field(None, description="問題敘述")


class CreateClientCaseResponse(BaseModel):
    """建立客戶+個案回應"""

    # Client 資訊
    client_id: UUID
    client_code: str
    client_name: str
    client_email: str

    # Case 資訊
    case_id: UUID
    case_number: str
    case_status: str

    # Metadata
    created_at: datetime
    message: str = "客戶與個案建立成功"

    class Config:
        from_attributes = True


class UpdateClientCaseRequest(BaseModel):
    """更新客戶+個案請求"""

    # Client 欄位 (all optional)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    phone: Optional[str] = None
    identity_option: Optional[str] = None
    current_status: Optional[str] = None
    nickname: Optional[str] = None
    notes: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    location: Optional[str] = None

    # Case 欄位 (all optional)
    case_status: Optional[str] = Field(None, description="個案狀態: active/completed/suspended/referred")
    case_summary: Optional[str] = None
    case_goals: Optional[str] = None
    problem_description: Optional[str] = None


class ClientCaseListItem(BaseModel):
    """客戶個案列表項目（UI 最佳化）"""

    # IDs
    client_id: UUID
    case_id: UUID
    counselor_id: UUID

    # Client 基本資訊
    client_name: str = Field(..., description="客戶姓名")
    client_code: str = Field(..., description="客戶代碼")
    client_email: str = Field(..., description="客戶 Email")

    # Client 狀態資訊
    identity_option: str = Field(..., description="身分選項（學生/社會新鮮人/轉職者/在職者/其他）")
    current_status: str = Field(..., description="當前狀況")

    # Case 資訊
    case_number: str = Field(..., description="個案編號")
    case_status: str = Field(..., description="個案狀態（英文）")
    case_status_label: str = Field(..., description="個案狀態（中文）")

    # Session 資訊
    last_session_date: Optional[datetime] = Field(None, description="最後諮詢日期")
    last_session_date_display: Optional[str] = Field(None, description="最後諮詢日期（顯示格式）")
    total_sessions: int = Field(0, description="總會談次數")

    # 時間戳記
    case_created_at: datetime = Field(..., description="個案建立時間")
    case_updated_at: Optional[datetime] = Field(None, description="個案更新時間")

    class Config:
        from_attributes = True


class ClientCaseListResponse(BaseModel):
    """客戶個案列表回應"""

    items: List[ClientCaseListItem]
    total: int
    skip: int
    limit: int


# ============================================================================
# Helper Functions
# ============================================================================


def _generate_client_code(db: Session, tenant_id: str) -> str:
    """
    Generate unique client code in format C0001, C0002, etc.

    Args:
        db: Database session
        tenant_id: Tenant ID

    Returns:
        Generated client code
    """
    # Find the highest existing code number for this tenant
    result = db.execute(
        select(Client.code)
        .where(Client.tenant_id == tenant_id)
        .where(Client.code.like("C%"))
        .order_by(Client.code.desc())
    )
    codes = result.scalars().all()

    # Extract numbers from codes and find max
    max_num = 0
    for code in codes:
        if code.startswith("C") and code[1:].isdigit():
            num = int(code[1:])
            if num > max_num:
                max_num = num

    # Generate next code
    next_num = max_num + 1
    return f"C{next_num:04d}"


def _generate_case_number(db: Session, tenant_id: str) -> str:
    """
    Generate unique case number in format CASE0001, CASE0002, etc.

    Args:
        db: Database session
        tenant_id: Tenant ID

    Returns:
        Generated case number
    """
    # Find the highest existing case number for this tenant (exclude deleted)
    result = db.execute(
        select(Case.case_number)
        .where(Case.tenant_id == tenant_id)
        .where(Case.case_number.like("CASE%"))
        .where(Case.deleted_at.is_(None))
        .order_by(Case.case_number.desc())
    )
    numbers = result.scalars().all()

    # Extract numbers and find max
    max_num = 0
    for num_str in numbers:
        if num_str.startswith("CASE") and num_str[4:].isdigit():
            num = int(num_str[4:])
            if num > max_num:
                max_num = num

    # Generate next number
    next_num = max_num + 1
    return f"CASE{next_num:04d}"


def _map_case_status_to_label(status: CaseStatus) -> str:
    """將 Case Status 映射為中文標籤"""
    status_map = {
        CaseStatus.ACTIVE: "進行中",
        CaseStatus.COMPLETED: "已完成",
        CaseStatus.SUSPENDED: "暫停中",
        CaseStatus.REFERRED: "已轉介",
    }
    return status_map.get(status, "未知")


def _format_session_date(dt: Optional[datetime]) -> Optional[str]:
    """格式化會談日期為顯示格式：2026/01/22 19:30"""
    if not dt:
        return None
    return dt.strftime("%Y/%m/%d %H:%M")


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/client-case", response_model=CreateClientCaseResponse, status_code=status.HTTP_201_CREATED)
def create_client_and_case(
    request: CreateClientCaseRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> CreateClientCaseResponse:
    """
    建立客戶與個案（一次完成）

    **功能說明：**
    - 同時建立 Client 和 Case
    - 自動生成 Client Code (C0001) 和 Case Number (CASE0001)
    - Client 和 Case 自動關聯

    **使用場景：**
    - 新客戶諮詢時，一次建立客戶和個案
    - Mobile App "建立新個案" 表單

    **注意事項：**
    - Email 不需要在 tenant 內唯一（同一客戶可能有多個 case）
    - Client Code 和 Case Number 自動生成
    """
    try:
        # Step 1: Generate Client Code
        client_code = _generate_client_code(db, tenant_id)

        # Step 2: Check if email already exists (soft-deleted excluded)
        existing_client = db.execute(
            select(Client).where(
                Client.email == request.email,
                Client.tenant_id == tenant_id,
                Client.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if existing_client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email {request.email} already exists for this tenant"
            )

        # Step 3: Create Client
        new_client = Client(
            code=client_code,
            name=request.name,
            nickname=request.nickname,
            email=request.email,
            gender=request.gender,
            birth_date=request.birth_date,
            phone=request.phone,
            identity_option=request.identity_option,
            current_status=request.current_status,
            education=request.education,
            occupation=request.occupation,
            location=request.location,
            notes=request.notes,
            counselor_id=current_user.id,
            tenant_id=tenant_id,
        )
        db.add(new_client)
        db.flush()  # Get client.id without committing

        # Step 4: Generate Case Number
        case_number = _generate_case_number(db, tenant_id)

        # Step 5: Create Case
        new_case = Case(
            case_number=case_number,
            client_id=new_client.id,
            counselor_id=current_user.id,
            tenant_id=tenant_id,
            status=CaseStatus.ACTIVE,
            summary=request.case_summary,
            goals=request.case_goals,
            problem_description=request.problem_description,
        )
        db.add(new_case)

        # Step 6: Commit transaction
        db.commit()
        db.refresh(new_client)
        db.refresh(new_case)

        # Step 7: Return response
        return CreateClientCaseResponse(
            client_id=new_client.id,
            client_code=new_client.code,
            client_name=new_client.name,
            client_email=new_client.email,
            case_id=new_case.id,
            case_number=new_case.case_number,
            case_status=new_case.status.value,
            created_at=new_client.created_at,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create client and case: {str(e)}"
        )


@router.get("/client-case-list", response_model=ClientCaseListResponse)
def get_client_case_list(
    skip: int = Query(0, ge=0, description="跳過筆數"),
    limit: int = Query(100, ge=1, le=500, description="每頁筆數"),
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> ClientCaseListResponse:
    """
    取得客戶個案列表（UI 最佳化版本）

    **功能說明：**
    - 結合 Client + Case + Session 資料
    - 顯示每個客戶的第一個 Case 資訊
    - 包含最後諮詢日期和總會談次數
    - 按最後諮詢日期排序（最新的在前）

    **回應欄位：**
    - `client_name`: 客戶姓名（黃先生）
    - `client_email`: 客戶 Email
    - `identity_option`: 身分（在職中/求職）
    - `case_status_label`: 個案狀態（已完成/未開始/進行中）
    - `last_session_date_display`: 最後諮詢（2026/01/22 19:30）
    - `total_sessions`: 總會談次數

    **使用場景：**
    - Console 個案列表頁面
    - iOS App 個案列表
    """
    # Step 1: 查詢所有 clients 和他們的第一個 case
    # 使用 subquery 找出每個 client 的第一個 case (按 created_at 最早)
    case_subquery = (
        select(
            Case.client_id,
            func.min(Case.created_at).label("first_case_created_at")
        )
        .where(
            Case.tenant_id == tenant_id,
            Case.deleted_at.is_(None),
        )
        .group_by(Case.client_id)
        .subquery()
    )

    # Step 2: Join clients with their first case
    query = (
        select(Client, Case)
        .join(
            case_subquery,
            Client.id == case_subquery.c.client_id
        )
        .join(
            Case,
            (Case.client_id == Client.id) &
            (Case.created_at == case_subquery.c.first_case_created_at) &
            (Case.deleted_at.is_(None))
        )
        .where(
            Client.tenant_id == tenant_id,
            Client.deleted_at.is_(None),
        )
    )

    # Step 3: Count total items
    count_query = select(func.count()).select_from(
        select(Client.id)
        .join(case_subquery, Client.id == case_subquery.c.client_id)
        .where(
            Client.tenant_id == tenant_id,
            Client.deleted_at.is_(None),
        )
        .subquery()
    )
    total = db.execute(count_query).scalar() or 0

    # Step 4: Execute query with pagination
    result = db.execute(query.offset(skip).limit(limit))
    client_case_pairs = result.all()

    # Step 5: Build response items
    items = []
    for client, case in client_case_pairs:
        # Get session info for this case
        session_stats = db.execute(
            select(
                func.count(SessionModel.id).label("total_sessions"),
                func.max(SessionModel.session_date).label("last_session_date"),
            )
            .where(
                SessionModel.case_id == case.id,
                SessionModel.deleted_at.is_(None),
            )
        ).first()

        total_sessions = session_stats.total_sessions if session_stats else 0
        last_session_date = session_stats.last_session_date if session_stats else None

        # Build item
        item = ClientCaseListItem(
            client_id=client.id,
            case_id=case.id,
            counselor_id=client.counselor_id,
            client_name=client.name,
            client_code=client.code,
            client_email=client.email,
            identity_option=client.identity_option,
            current_status=client.current_status,
            case_number=case.case_number,
            case_status=case.status.value,
            case_status_label=_map_case_status_to_label(case.status),
            last_session_date=last_session_date,
            last_session_date_display=_format_session_date(last_session_date),
            total_sessions=total_sessions,
            case_created_at=case.created_at,
            case_updated_at=case.updated_at,
        )
        items.append(item)

    # Step 6: Sort by last_session_date (newest first, None at the end)
    # Use timezone-aware datetime.min to avoid comparison errors
    from datetime import timezone
    min_datetime = datetime.min.replace(tzinfo=timezone.utc)
    items.sort(
        key=lambda x: x.last_session_date if x.last_session_date else min_datetime,
        reverse=True
    )

    return ClientCaseListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.patch("/client-case/{case_id}", response_model=CreateClientCaseResponse)
def update_client_and_case(
    case_id: UUID,
    request: UpdateClientCaseRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> CreateClientCaseResponse:
    """
    更新客戶與個案資料

    **功能說明：**
    - 同時更新 Client 和 Case
    - 所有欄位都是選填，只更新提供的欄位
    - Case 狀態可更新為 active/completed/suspended/referred

    **使用場景：**
    - 編輯個案資料
    - 更新個案狀態
    - 修改客戶基本資料
    """
    try:
        # Step 1: Find case by ID
        case = db.execute(
            select(Case)
            .where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )

        # Step 2: Find associated client
        client = db.execute(
            select(Client)
            .where(
                Client.id == case.client_id,
                Client.tenant_id == tenant_id,
                Client.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {case.client_id} not found"
            )

        # Step 3: Update Client fields (only if provided)
        client_updated = False
        if request.name is not None:
            client.name = request.name
            client_updated = True
        if request.email is not None:
            # Check if email already exists (for another client)
            existing_client = db.execute(
                select(Client).where(
                    Client.email == request.email,
                    Client.tenant_id == tenant_id,
                    Client.id != client.id,
                    Client.deleted_at.is_(None),
                )
            ).scalar_one_or_none()
            if existing_client:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email {request.email} already exists for another client"
                )
            client.email = request.email
            client_updated = True
        if request.gender is not None:
            client.gender = request.gender
            client_updated = True
        if request.birth_date is not None:
            client.birth_date = request.birth_date
            client_updated = True
        if request.phone is not None:
            client.phone = request.phone
            client_updated = True
        if request.identity_option is not None:
            client.identity_option = request.identity_option
            client_updated = True
        if request.current_status is not None:
            client.current_status = request.current_status
            client_updated = True
        if request.nickname is not None:
            client.nickname = request.nickname
            client_updated = True
        if request.notes is not None:
            client.notes = request.notes
            client_updated = True
        if request.education is not None:
            client.education = request.education
            client_updated = True
        if request.occupation is not None:
            client.occupation = request.occupation
            client_updated = True
        if request.location is not None:
            client.location = request.location
            client_updated = True

        # Step 4: Update Case fields (only if provided)
        case_updated = False
        if request.case_status is not None:
            try:
                case.status = CaseStatus(request.case_status)
                case_updated = True
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid case_status: {request.case_status}. Must be one of: active, completed, suspended, referred"
                )
        if request.case_summary is not None:
            case.summary = request.case_summary
            case_updated = True
        if request.case_goals is not None:
            case.goals = request.case_goals
            case_updated = True
        if request.problem_description is not None:
            case.problem_description = request.problem_description
            case_updated = True

        # Step 5: Commit if any changes were made
        if client_updated or case_updated:
            db.commit()
            db.refresh(client)
            db.refresh(case)

        # Step 6: Return response
        return CreateClientCaseResponse(
            client_id=client.id,
            client_code=client.code,
            client_name=client.name,
            client_email=client.email,
            case_id=case.id,
            case_number=case.case_number,
            case_status=case.status.value,
            created_at=client.created_at,
            message="客戶與個案更新成功",
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update client and case: {str(e)}"
        )


@router.delete("/client-case/{case_id}", status_code=status.HTTP_200_OK)
def delete_client_case(
    case_id: UUID,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    刪除個案（軟刪除）

    **功能說明：**
    - 軟刪除 Case（設定 deleted_at）
    - 不刪除 Client（一個 Client 可能有多個 Cases）
    - 只有 counselor 本人可以刪除自己的個案

    **使用場景：**
    - 結束個案並歸檔
    - 錯誤建立的個案需要刪除

    **注意事項：**
    - 這是軟刪除，資料不會真正消失
    - Client 不會被刪除，只刪除 Case
    """
    try:
        # Step 1: Find case by ID
        case = db.execute(
            select(Case)
            .where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found"
            )

        # Step 2: Check ownership (only allow counselor to delete their own cases)
        if case.counselor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own cases"
            )

        # Step 3: Soft delete (set deleted_at timestamp)
        from datetime import datetime, timezone
        case.deleted_at = datetime.now(timezone.utc)

        # Step 4: Commit
        db.commit()

        return {
            "message": "Case deleted successfully",
            "case_id": str(case_id),
            "case_number": case.case_number,
            "deleted_at": case.deleted_at.isoformat(),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete case: {str(e)}"
        )
