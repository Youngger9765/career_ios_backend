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
    identity_option: str = Field(
        ..., description="身份選項（學生/社會新鮮人/轉職者/在職者/其他）"
    )
    current_status: str = Field(..., description="目前現況")

    # Client 選填欄位
    education: Optional[str] = Field(None, description="學歷")
    current_job: Optional[str] = Field(None, description="您的現職（職業／年資）")
    career_status: Optional[str] = Field(None, description="職涯現況")
    has_consultation_history: Optional[str] = Field(None, description="過往諮詢經驗")
    has_mental_health_history: Optional[str] = Field(
        None, description="心理或精神醫療史"
    )
    location: Optional[str] = Field(None, description="居住地區")
    notes: Optional[str] = Field(None, description="備註")

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
    case_status: int

    # Metadata
    created_at: datetime
    message: str = "客戶與個案建立成功"

    class Config:
        from_attributes = True


class ClientCaseDetailResponse(BaseModel):
    """客戶個案詳細資訊回應（用於單一個案查詢）"""

    # Client 資訊
    client_id: UUID
    client_name: str
    client_code: str
    client_email: str
    gender: str
    birth_date: date
    phone: str
    identity_option: str
    current_status: str
    nickname: Optional[str] = None
    education: Optional[str] = None
    occupation: Optional[str] = None
    current_job: Optional[str] = None
    career_status: Optional[str] = None
    has_consultation_history: Optional[str] = None
    has_mental_health_history: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

    # Case 資訊
    case_id: UUID
    case_number: str
    case_status: int
    case_status_label: str
    case_summary: Optional[str] = None
    case_goals: Optional[str] = None
    problem_description: Optional[str] = None

    # Metadata
    counselor_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

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
    education: Optional[str] = None
    current_job: Optional[str] = None
    career_status: Optional[str] = None
    has_consultation_history: Optional[str] = None
    has_mental_health_history: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

    # Case 欄位 (all optional)
    case_status: Optional[str] = Field(
        None, description="個案狀態: 0=未開始, 1=進行中, 2=已完成"
    )
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
    identity_option: str = Field(
        ..., description="身分選項（學生/社會新鮮人/轉職者/在職者/其他）"
    )
    current_status: str = Field(..., description="當前狀況")

    # Case 資訊
    case_number: str = Field(..., description="個案編號")
    case_status: int = Field(
        ..., description="個案狀態（整數：0=未開始, 1=進行中, 2=已完成）"
    )
    case_status_label: str = Field(..., description="個案狀態（中文）")

    # Session 資訊
    last_session_date: Optional[datetime] = Field(None, description="最後諮詢日期")
    last_session_date_display: Optional[str] = Field(
        None, description="最後諮詢日期（顯示格式）"
    )
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
    # Find the highest existing case number for this tenant (include all, even deleted)
    result = db.execute(
        select(Case.case_number)
        .where(Case.tenant_id == tenant_id)
        .where(Case.case_number.like("CASE%"))
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
        CaseStatus.NOT_STARTED: "未開始",
        CaseStatus.IN_PROGRESS: "進行中",
        CaseStatus.COMPLETED: "已完成",
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


@router.post(
    "/client-case",
    response_model=CreateClientCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="創建客戶與個案（iOS 使用）",
    description="""
    ## 一次性創建客戶（Client）和個案（Case）

    **用途**: iOS App 創建新個案時使用，一個 API 完成客戶和個案的創建

    **自動生成**:
    - 客戶代碼（code）: C0001, C0002...（租戶內唯一）
    - 個案編號（case_number）: CASE-20251124-001...（租戶內唯一）

    **必填欄位**:
    - name, email, gender, birth_date, phone
    - identity_option, current_status

    **選填欄位**: education, current_job, case 相關欄位等

    **返回**: 創建的客戶 ID 和個案 ID
    """,
)
def create_client_and_case(
    request: CreateClientCaseRequest,
    current_user: Counselor = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_id),
    db: Session = Depends(get_db),
) -> CreateClientCaseResponse:
    """
    建立客戶與個案（一次完成）- iOS 使用

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
                detail=f"Email {request.email} already exists for this tenant",
            )

        # Step 3: Create Client
        new_client = Client(
            code=client_code,
            name=request.name,
            email=request.email,
            gender=request.gender,
            birth_date=request.birth_date,
            phone=request.phone,
            identity_option=request.identity_option,
            current_status=request.current_status,
            # Optional fields
            education=request.education,
            current_job=request.current_job,
            career_status=request.career_status,
            has_consultation_history=request.has_consultation_history,
            has_mental_health_history=request.has_mental_health_history,
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
            status=CaseStatus.NOT_STARTED,
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
        # Handle status (compatible with both int and enum)
        status_value = (
            new_case.status
            if isinstance(new_case.status, int)
            else new_case.status.value
        )

        return CreateClientCaseResponse(
            client_id=new_client.id,
            client_code=new_client.code,
            client_name=new_client.name,
            client_email=new_client.email,
            case_id=new_case.id,
            case_number=new_case.case_number,
            case_status=status_value,
            created_at=new_client.created_at,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create client and case: {str(e)}",
        )


@router.get(
    "/client-case-list",
    response_model=ClientCaseListResponse,
    summary="列出所有客戶個案（iOS 使用）",
    description="""
    ## 獲取個案列表（Client + Case + Session 統計）

    **用途**: iOS App 個案列表頁面使用

    **返回內容**:
    - 個案基本資訊（case_id, case_number, status）
    - 客戶資訊（client_id, client_name, client_email）
    - 會談統計（session_count, latest_session_date）

    **分頁參數**:
    - skip: 跳過筆數（默認 0）
    - limit: 每頁筆數（默認 100，最大 500）

    **排序**: 按創建時間倒序（最新的在前）
    """,
)
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
        select(Case.client_id, func.min(Case.created_at).label("first_case_created_at"))
        .where(
            Case.tenant_id == tenant_id,
            Case.deleted_at.is_(None),
        )
        .group_by(Case.client_id)
        .subquery()
    )

    # Step 2: Create session stats subquery (to avoid N+1)
    session_stats_subquery = (
        select(
            SessionModel.case_id,
            func.count(SessionModel.id).label("total_sessions"),
            func.max(SessionModel.session_date).label("last_session_date"),
        )
        .where(SessionModel.deleted_at.is_(None))
        .group_by(SessionModel.case_id)
        .subquery()
    )

    # Step 3: Join clients with their first case and session stats
    query = (
        select(
            Client,
            Case,
            session_stats_subquery.c.total_sessions,
            session_stats_subquery.c.last_session_date,
        )
        .join(case_subquery, Client.id == case_subquery.c.client_id)
        .join(
            Case,
            (Case.client_id == Client.id)
            & (Case.created_at == case_subquery.c.first_case_created_at)
            & (Case.deleted_at.is_(None)),
        )
        .outerjoin(session_stats_subquery, Case.id == session_stats_subquery.c.case_id)
        .where(
            Client.tenant_id == tenant_id,
            Client.deleted_at.is_(None),
        )
    )

    # Step 4: Count total items
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

    # Step 5: Execute query with pagination
    result = db.execute(query.offset(skip).limit(limit))
    rows = result.all()

    # Step 6: Build response items
    items = []
    for client, case, total_sessions, last_session_date in rows:
        # Session stats already fetched via JOIN (no N+1 query)
        total_sessions = total_sessions or 0

        # Handle status (compatible with old string data and new IntEnum)
        if isinstance(case.status, int):
            status_value = case.status
            status_enum = CaseStatus(case.status)
        elif isinstance(case.status, CaseStatus):
            status_value = case.status.value
            status_enum = case.status
        else:
            # Legacy string data - convert to integer
            status_map = {
                "ACTIVE": CaseStatus.NOT_STARTED,
                "IN_PROGRESS": CaseStatus.IN_PROGRESS,
                "COMPLETED": CaseStatus.COMPLETED,
                "SUSPENDED": CaseStatus.IN_PROGRESS,
                "REFERRED": CaseStatus.COMPLETED,
                "NOT_STARTED": CaseStatus.NOT_STARTED,
            }
            status_enum = status_map.get(
                str(case.status).upper(), CaseStatus.NOT_STARTED
            )
            status_value = status_enum.value

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
            case_status=status_value,
            case_status_label=_map_case_status_to_label(status_enum),
            last_session_date=last_session_date,
            last_session_date_display=_format_session_date(last_session_date),
            total_sessions=total_sessions,
            case_created_at=case.created_at,
            case_updated_at=case.updated_at,
        )
        items.append(item)

    # Step 7: Sort by last_session_date (newest first, None at the end)
    # Handle both timezone-aware and timezone-naive datetimes
    from datetime import timezone

    min_datetime = datetime.min.replace(tzinfo=timezone.utc)

    def sort_key(item):
        if item.last_session_date is None:
            return min_datetime
        # Convert to timezone-aware if needed
        dt = item.last_session_date
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    items.sort(key=sort_key, reverse=True)

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
    """
    獲取單一客戶個案詳細資訊

    **功能說明：**
    - 返回指定個案的完整 Client + Case 資訊
    - 用於 iOS 更新表單載入現有資料
    - 包含所有可編輯欄位

    **使用場景：**
    - iOS 進入更新畫面時，先調用此 API 獲取現有資料
    - 顯示個案詳情頁面
    """
    try:
        # Find case by ID with joined client
        case = db.execute(
            select(Case)
            .options(joinedload(Case.client))
            .where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found",
            )

        client = case.client
        if not client or client.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client for case {case_id} not found",
            )

        # Get case status label
        status_labels = {
            0: "未開始",
            1: "進行中",
            2: "已完成",
        }
        status_value = (
            case.status if isinstance(case.status, int) else case.status.value
        )
        status_label = status_labels.get(status_value, "未知")

        return ClientCaseDetailResponse(
            # Client fields
            client_id=client.id,
            client_name=client.name,
            client_code=client.code,
            client_email=client.email,
            gender=client.gender,
            birth_date=client.birth_date,
            phone=client.phone,
            identity_option=client.identity_option,
            current_status=client.current_status,
            nickname=client.nickname,
            education=client.education,
            occupation=client.occupation,
            current_job=client.current_job,
            career_status=client.career_status,
            has_consultation_history=client.has_consultation_history,
            has_mental_health_history=client.has_mental_health_history,
            location=client.location,
            notes=client.notes,
            # Case fields
            case_id=case.id,
            case_number=case.case_number,
            case_status=status_value,
            case_status_label=status_label,
            case_summary=case.summary,
            case_goals=case.goals,
            problem_description=case.problem_description,
            # Metadata
            counselor_id=case.counselor_id,
            created_at=case.created_at,
            updated_at=case.updated_at,
        )

    except HTTPException:
        raise
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
            select(Case).where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found",
            )

        # Step 2: Find associated client
        client = db.execute(
            select(Client).where(
                Client.id == case.client_id,
                Client.tenant_id == tenant_id,
                Client.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client {case.client_id} not found",
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
                    detail=f"Email {request.email} already exists for another client",
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
        if request.education is not None:
            client.education = request.education
            client_updated = True
        if request.current_job is not None:
            client.current_job = request.current_job
            client_updated = True
        if request.career_status is not None:
            client.career_status = request.career_status
            client_updated = True
        if request.has_consultation_history is not None:
            client.has_consultation_history = request.has_consultation_history
            client_updated = True
        if request.has_mental_health_history is not None:
            client.has_mental_health_history = request.has_mental_health_history
            client_updated = True
        if request.location is not None:
            client.location = request.location
            client_updated = True
        if request.notes is not None:
            client.notes = request.notes
            client_updated = True

        # Step 4: Update Case fields (only if provided)
        case_updated = False
        if request.case_status is not None:
            try:
                # Accept both integer and string (for backward compatibility)
                if isinstance(request.case_status, int):
                    case.status = CaseStatus(request.case_status)
                else:
                    # Try to parse as integer if it's a string
                    case.status = CaseStatus(int(request.case_status))
                case_updated = True
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid case_status: {request.case_status}. Must be 0 (未開始), 1 (進行中), or 2 (已完成)",
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
        # Handle status (compatible with both int and enum)
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

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
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
            select(Case).where(
                Case.id == case_id,
                Case.tenant_id == tenant_id,
                Case.deleted_at.is_(None),
            )
        ).scalar_one_or_none()

        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case {case_id} not found",
            )

        # Step 2: Check ownership (only allow counselor to delete their own cases)
        if case.counselor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own cases",
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
            detail=f"Failed to delete case: {str(e)}",
        )
