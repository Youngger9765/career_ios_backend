"""
Admin Credit Management API Endpoints
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.counselor import Counselor, CounselorRole
from app.models.credit_log import CreditLog
from app.models.credit_rate import CreditRate
from app.schemas.credit import (
    AdminAddCreditsRequest,
    AdminAddCreditsResponse,
    CounselorCreditInfo,
    CreditLogResponse,
    CreditRateCreate,
    CreditRateResponse,
)
from app.services.credit_billing import CreditBillingService

router = APIRouter(prefix="/admin/credits", tags=["admin-credits"])


def require_admin(current_user: Counselor = Depends(get_current_user)) -> Counselor:
    """Verify current user is admin"""
    if current_user.role != CounselorRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def resolve_tenant_id(
    current_admin: Counselor,
    requested_tenant_id: Optional[str],
) -> str:
    """Resolve and validate tenant_id for admin access."""
    if requested_tenant_id is None:
        return current_admin.tenant_id
    if requested_tenant_id != current_admin.tenant_id:
        raise HTTPException(
            status_code=403,
            detail=f"Admin not allowed to access tenant '{requested_tenant_id}'",
        )
    return requested_tenant_id


@router.get("/members", response_model=List[CounselorCreditInfo])
async def list_members_with_credits(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    db: Session = Depends(get_db),
    current_admin: Counselor = Depends(require_admin),
):
    """
    List all counselors with credit information.
    Admin only. Filtered by tenant if authorized.
    """
    target_tenant_id = resolve_tenant_id(current_admin, tenant_id)

    # Automatically filter by admin's tenant_id
    counselors = (
        db.query(Counselor).filter(Counselor.tenant_id == target_tenant_id).all()
    )

    return [
        CounselorCreditInfo(
            id=c.id,
            email=c.email,
            full_name=c.full_name,
            phone=c.phone,
            tenant_id=c.tenant_id,
            total_credits=c.total_credits,
            credits_used=c.credits_used,
            available_credits=c.available_credits,
            subscription_expires_at=c.subscription_expires_at,
        )
        for c in counselors
    ]


@router.post("/members/{counselor_id}/add", response_model=AdminAddCreditsResponse)
async def add_credits_to_member(
    counselor_id: UUID,
    request: AdminAddCreditsRequest,
    db: Session = Depends(get_db),
    current_admin: Counselor = Depends(require_admin),
):
    """
    Add credits to a counselor account.
    Admin only. Automatically filtered by admin's tenant.

    Supports positive (add credits) and negative (remove credits) values.
    """
    # Verify counselor belongs to admin's tenant
    counselor = (
        db.query(Counselor)
        .filter(
            Counselor.id == counselor_id, Counselor.tenant_id == current_admin.tenant_id
        )
        .first()
    )

    if not counselor:
        raise HTTPException(
            status_code=404, detail="Counselor not found in your tenant"
        )

    billing_service = CreditBillingService(db)

    try:
        # Prepare raw_data with admin notes
        raw_data = {"notes": request.notes} if request.notes else None

        # Add credits
        credit_log = billing_service.add_credits(
            counselor_id=counselor_id,
            credits_delta=request.credits_delta,
            transaction_type=request.transaction_type,
            raw_data=raw_data,
        )

        # Get new balance
        balance = billing_service.get_counselor_balance(counselor_id)

        return AdminAddCreditsResponse(
            success=True,
            message=f"Successfully {'added' if request.credits_delta > 0 else 'removed'} {abs(request.credits_delta)} credits",
            credit_log=CreditLogResponse.model_validate(credit_log),
            new_balance=balance["available_credits"],
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/logs", response_model=List[CreditLogResponse])
async def get_credit_logs(
    counselor_id: Optional[UUID] = Query(None, description="Filter by counselor ID"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    transaction_type: Optional[str] = Query(
        None, description="Filter by transaction type"
    ),
    limit: int = Query(100, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, description="Number of logs to skip"),
    db: Session = Depends(get_db),
    current_admin: Counselor = Depends(require_admin),
):
    """
    Get credit transaction history.
    Admin only. Filtered by tenant if authorized.

    Supports filtering by counselor_id and transaction_type.
    """
    target_tenant_id = resolve_tenant_id(current_admin, tenant_id)

    # Join with Counselor to filter by tenant_id
    query = (
        db.query(CreditLog)
        .join(Counselor, CreditLog.counselor_id == Counselor.id)
        .filter(Counselor.tenant_id == target_tenant_id)
    )

    if counselor_id:
        query = query.filter(CreditLog.counselor_id == counselor_id)
    if transaction_type:
        query = query.filter(CreditLog.transaction_type == transaction_type)

    logs = query.order_by(CreditLog.created_at.desc()).offset(offset).limit(limit).all()
    return [CreditLogResponse.model_validate(log) for log in logs]


@router.post("/rates", response_model=CreditRateResponse)
async def create_billing_rate(
    request: CreditRateCreate,
    db: Session = Depends(get_db),
    current_admin: Counselor = Depends(require_admin),
):
    """
    Create or update a billing rate (creates new version).
    Admin only. Automatically filtered by admin's tenant.

    If a rate with the same rule_name exists, creates a new version
    and deactivates the old version.
    """
    # Note: CreditRate is global (not tenant-specific) in current schema
    # This endpoint remains unchanged but renamed parameter for consistency
    # If tenant-specific rates are needed, CreditRate model needs tenant_id column

    # Check if rule exists
    existing = (
        db.query(CreditRate)
        .filter(CreditRate.rule_name == request.rule_name)
        .order_by(CreditRate.version.desc())
        .first()
    )

    # Determine version
    version = (existing.version + 1) if existing else 1

    # Create new rate
    new_rate = CreditRate(
        rule_name=request.rule_name,
        calculation_method=request.calculation_method,
        rate_config=request.rate_config,
        version=version,
        is_active=True,
        effective_from=request.effective_from,
    )

    # Deactivate old versions
    if existing:
        db.query(CreditRate).filter(CreditRate.rule_name == request.rule_name).update(
            {"is_active": False}
        )

    db.add(new_rate)
    db.commit()
    db.refresh(new_rate)

    return CreditRateResponse.model_validate(new_rate)


@router.get("/rates", response_model=List[CreditRateResponse])
async def list_billing_rates(
    rule_name: Optional[str] = Query(None, description="Filter by rule name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_admin: Counselor = Depends(require_admin),
):
    """
    List billing rates.
    Admin only. Automatically filtered by admin's tenant.

    Supports filtering by rule_name and is_active.
    """
    # Note: CreditRate is global (not tenant-specific) in current schema
    # This endpoint remains unchanged but renamed parameter for consistency
    # If tenant-specific rates are needed, CreditRate model needs tenant_id column

    query = db.query(CreditRate)

    if rule_name:
        query = query.filter(CreditRate.rule_name == rule_name)
    if is_active is not None:
        query = query.filter(CreditRate.is_active == is_active)

    rates = query.order_by(CreditRate.rule_name, CreditRate.version.desc()).all()
    return [CreditRateResponse.model_validate(rate) for rate in rates]
