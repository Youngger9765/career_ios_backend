"""
Internal API endpoints (not exposed to public)
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.counselor import Counselor
from app.services.external import revenuecat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post("/purge-deleted-accounts")
def purge_deleted_accounts(
    request: Request,
    db: Session = Depends(get_db),
    x_internal_key: str = Header(..., alias="X-Internal-Key"),
):
    """
    Purge accounts that have been in deletion state for more than 14 days.
    Called by Cloud Scheduler daily.

    Requires X-Internal-Key header for authentication.
    """
    # Verify internal API key
    if x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal key")

    cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.ACCOUNT_DELETION_GRACE_PERIOD_DAYS
    )

    result = db.execute(
        select(Counselor).where(
            Counselor.deleted_at.isnot(None),
            Counselor.deleted_at <= cutoff,
            Counselor.is_active == False,  # noqa: E712
            # Only purge accounts where email is NOT already anonymized
            ~Counselor.email.startswith("deleted_"),
        )
    )
    accounts = result.scalars().all()

    purged = 0
    failed = 0

    for account in accounts:
        try:
            original_email = account.email
            user_id = str(account.id)

            # Anonymize PII
            timestamp = int(datetime.now(timezone.utc).timestamp())
            account.email = f"deleted_{timestamp}_{account.email}"
            account.username = None
            account.full_name = None
            account.phone = None

            db.commit()

            # RevenueCat delete (fire and forget)
            rc_success = revenuecat_service.delete_customer(original_email, user_id)
            if rc_success:
                logger.info("RevenueCat purged for user_id=%s", user_id)
            else:
                logger.warning("RevenueCat purge failed for user_id=%s", user_id)

            purged += 1
            logger.info("Purged account: %s (id=%s)", original_email, user_id)

        except Exception as e:
            db.rollback()
            failed += 1
            logger.error("Failed to purge account id=%s: %s", str(account.id), str(e))

    return {
        "purged": purged,
        "failed": failed,
        "message": f"Purge complete. {purged} accounts anonymized, {failed} failed.",
    }
