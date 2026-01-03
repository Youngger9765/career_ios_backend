"""
UI Client-Case Schemas
UI-optimized request/response models for client-case management
"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class CreateClientCaseRequest(BaseModel):
    """建立客戶+個案請求（UI 友善版本）"""

    # Client 必填欄位
    name: str = Field(..., min_length=1, max_length=100, description="客戶姓名")
    email: Optional[EmailStr] = Field(None, description="Email (選填，親子版可留空)")
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
    client_email: Optional[str] = None  # 選填，親子版可留空

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
    client_email: Optional[str] = None  # 選填，親子版可留空
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
    client_email: Optional[str] = Field(None, description="客戶 Email (選填)")

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
