"""
Credit System Pydantic Schemas
"""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# CreditRate Schemas
# ============================================================================


class CreditRateBase(BaseModel):
    """Base schema for credit rate"""

    rule_name: str = Field(..., max_length=50, description="Rule identifier")
    calculation_method: str = Field(
        default="per_second",
        description="Calculation method: per_second, per_minute, tiered",
    )
    rate_config: Dict[str, Any] = Field(..., description="Rate configuration JSON")
    effective_from: datetime = Field(..., description="Effective date")


class CreditRateCreate(CreditRateBase):
    """Schema for creating credit rate"""

    pass


class CreditRateResponse(CreditRateBase):
    """Schema for credit rate response"""

    id: UUID
    version: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# CreditLog Schemas
# ============================================================================


class CreditLogBase(BaseModel):
    """Base schema for credit log"""

    credits_delta: int = Field(..., description="Credit change amount")
    transaction_type: str = Field(..., description="Transaction type")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw transaction data")
    rate_snapshot: Optional[Dict[str, Any]] = Field(
        None, description="Rate configuration snapshot"
    )
    calculation_details: Optional[Dict[str, Any]] = Field(
        None, description="Calculation details"
    )


class CreditLogCreate(CreditLogBase):
    """Schema for creating credit log"""

    counselor_id: UUID
    session_id: Optional[UUID] = None


class CreditLogResponse(CreditLogBase):
    """Schema for credit log response"""

    id: UUID
    counselor_id: UUID
    session_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Admin Request/Response Schemas
# ============================================================================


class CounselorCreditInfo(BaseModel):
    """Counselor information with credit balance"""

    id: UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    tenant_id: str
    total_credits: int
    credits_used: int
    available_credits: int
    subscription_expires_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminAddCreditsRequest(BaseModel):
    """Admin request to add/remove credits"""

    credits_delta: int = Field(
        ..., description="Credits to add (positive) or remove (negative)"
    )
    transaction_type: str = Field(
        ..., description="Transaction type: purchase, admin_adjustment, refund"
    )
    notes: Optional[str] = Field(None, description="Admin notes for this transaction")


class AdminAddCreditsResponse(BaseModel):
    """Admin response after adding credits"""

    success: bool
    message: str
    credit_log: CreditLogResponse
    new_balance: int


# ============================================================================
# Calculation Response Schema
# ============================================================================


class CreditCalculationResult(BaseModel):
    """Credit calculation result"""

    credits: int = Field(..., description="Calculated credits")
    rate_snapshot: Dict[str, Any] = Field(..., description="Rate configuration used")
    calculation_details: Dict[str, Any] = Field(..., description="Detailed breakdown")
