"""
Billing Reports API - GCP Cost Analysis and Email Reports
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from app.core.config import settings
from app.services.billing_analyzer import billing_analyzer
from app.services.email_sender import email_sender

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])
logger = logging.getLogger(__name__)


def verify_admin_key(x_admin_key: Optional[str] = Header(None)) -> bool:
    """Verify admin API key for billing endpoints"""
    if not settings.API_ADMIN_KEY:
        # If no admin key is configured, allow access (dev mode)
        logger.warning("API_ADMIN_KEY not configured, allowing access")
        return True

    if not x_admin_key or x_admin_key != settings.API_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing admin API key")

    return True


@router.get("/report", response_model=Dict[str, Any])
async def get_billing_report(_: bool = Depends(verify_admin_key)):
    """
    Generate and return latest billing report

    Requires admin authentication via X-Admin-Key header.

    Returns:
        Complete billing report with cost data and AI insights
    """
    try:
        report = await billing_analyzer.generate_full_report()
        return report
    except Exception as e:
        logger.error(f"Failed to generate billing report: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate billing report: {str(e)}"
        )


@router.post("/send-report")
async def send_billing_report(
    to_email: Optional[str] = None, _: bool = Depends(verify_admin_key)
):
    """
    Generate billing report and email it

    Requires admin authentication via X-Admin-Key header.

    Args:
        to_email: Optional recipient email (defaults to configured email)

    Returns:
        Success message with report summary
    """
    try:
        # Generate report
        report = await billing_analyzer.generate_full_report()

        # Send email
        success = await email_sender.send_billing_report(report, to_email)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Email sending failed (check SMTP configuration)",
            )

        summary = report.get("summary", {})
        return {
            "status": "success",
            "message": "Billing report sent successfully",
            "to_email": to_email or email_sender.default_to_email,
            "summary": {
                "total_cost": summary.get("total_cost"),
                "currency": summary.get("currency"),
                "date_range": summary.get("date_range"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send billing report: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to send billing report: {str(e)}"
        )


@router.get("/costs/7days")
async def get_7day_costs(_: bool = Depends(verify_admin_key)):
    """
    Get raw cost data for last 7 days

    Requires admin authentication via X-Admin-Key header.

    Returns:
        List of daily cost records with service breakdown
    """
    try:
        cost_data = await billing_analyzer.get_7_day_cost_trend()
        summary = await billing_analyzer.get_summary_stats(cost_data)

        return {"summary": summary, "data": cost_data, "count": len(cost_data)}

    except Exception as e:
        logger.error(f"Failed to fetch cost data: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch cost data: {str(e)}"
        )
