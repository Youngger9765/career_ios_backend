"""Usage API endpoints for billing and usage tracking."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.counselor import Counselor
from app.schemas.usage import UsageStatsResponse
from app.services.billing.usage_tracker import UsageTracker

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/stats", response_model=UsageStatsResponse)
def get_usage_stats(
    current_user: Counselor = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageStatsResponse:
    """
    Get usage statistics for the current authenticated counselor.

    Auto-resets expired usage periods for subscription mode before returning stats.

    Returns:
        UsageStatsResponse with billing mode and relevant usage data
    """
    tracker = UsageTracker()

    # Auto-reset if period expired (commits to DB if changes made)
    tracker.reset_if_period_expired(current_user)

    # If reset occurred, commit changes to DB
    if db.is_modified(current_user):
        db.commit()
        db.refresh(current_user)

    # Get usage stats
    stats = tracker.get_usage_stats(current_user)

    # Convert to response model
    return UsageStatsResponse(**stats)
