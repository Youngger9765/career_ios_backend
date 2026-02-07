"""
Admin Dashboard API - AI Monitoring Dashboard
Provides analytics for AI usage, costs, tokens, and user activity
"""
import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.counselor import Counselor, CounselorRole
from app.models.session_analysis_log import SessionAnalysisLog
from app.models.session_usage import SessionUsage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/dashboard", tags=["admin-dashboard"])


def require_admin(current_user: Counselor = Depends(get_current_user)) -> Counselor:
    """Verify current user is admin"""
    if current_user.role != CounselorRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_time_filter(time_range: Literal["day", "week", "month"]) -> datetime:
    """Get datetime filter based on time range"""
    now = datetime.now(timezone.utc)
    if time_range == "day":
        return now - timedelta(days=1)
    elif time_range == "week":
        return now - timedelta(days=7)
    elif time_range == "month":
        return now - timedelta(days=30)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid time_range. Must be 'day', 'week', or 'month'",
        )


@router.get("/summary")
def get_summary(
    time_range: Literal["day", "week", "month"] = Query("day"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Get summary statistics for dashboard

    Returns:
        - total_tokens: Sum of all tokens used
        - total_cost_usd: Sum of estimated costs
        - total_sessions: Count of unique sessions
        - active_users: Count of unique counselors
    """
    start_time = get_time_filter(time_range)

    # Build base query
    query = select(SessionUsage).where(SessionUsage.created_at >= start_time)
    if tenant_id:
        query = query.where(SessionUsage.tenant_id == tenant_id)

    # Get aggregated statistics
    stats_query = select(
        func.coalesce(func.sum(SessionUsage.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(SessionUsage.estimated_cost_usd), 0).label("total_cost"),
        func.count(func.distinct(SessionUsage.session_id)).label("total_sessions"),
        func.count(func.distinct(SessionUsage.counselor_id)).label("active_users"),
    ).select_from(SessionUsage).where(SessionUsage.created_at >= start_time)

    if tenant_id:
        stats_query = stats_query.where(SessionUsage.tenant_id == tenant_id)

    result = db.execute(stats_query).first()

    return {
        "total_tokens": int(result.total_tokens) if result else 0,
        "total_cost_usd": float(result.total_cost) if result else 0.0,
        "total_sessions": int(result.total_sessions) if result else 0,
        "active_users": int(result.active_users) if result else 0,
    }


@router.get("/cost-trend")
def get_cost_trend(
    time_range: Literal["day", "week", "month"] = Query("day"),
    tenant_id: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Get cost trend over time

    Returns:
        - labels: List of date strings
        - data: List of cost values
    """
    start_time = get_time_filter(time_range)

    # Determine date truncation based on time range
    if time_range == "day":
        date_trunc = func.date_trunc("hour", SessionUsage.created_at)
    else:
        date_trunc = func.date_trunc("day", SessionUsage.created_at)

    # Build query
    query = (
        select(
            date_trunc.label("period"),
            func.coalesce(func.sum(SessionUsage.estimated_cost_usd), 0).label("cost"),
        )
        .select_from(SessionUsage)
        .where(SessionUsage.created_at >= start_time)
        .group_by("period")
        .order_by("period")
    )

    if tenant_id:
        query = query.where(SessionUsage.tenant_id == tenant_id)

    # If model filter is specified, join with analysis logs
    if model:
        query = (
            query
            .join(SessionAnalysisLog, SessionUsage.session_id == SessionAnalysisLog.session_id)
            .where(SessionAnalysisLog.model_name == model)
        )

    results = db.execute(query).all()

    labels = []
    data = []
    for row in results:
        if time_range == "day":
            labels.append(row.period.strftime("%H:%M"))
        else:
            labels.append(row.period.strftime("%Y-%m-%d"))
        data.append(float(row.cost))

    return {
        "labels": labels,
        "data": data,
    }


@router.get("/token-trend")
def get_token_trend(
    time_range: Literal["day", "week", "month"] = Query("day"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Get token usage trend over time

    Returns:
        - labels: List of date strings
        - prompt_tokens: List of prompt token counts
        - completion_tokens: List of completion token counts
        - total_tokens: List of total token counts
    """
    start_time = get_time_filter(time_range)

    # Determine date truncation based on time range
    if time_range == "day":
        date_trunc = func.date_trunc("hour", SessionUsage.created_at)
    else:
        date_trunc = func.date_trunc("day", SessionUsage.created_at)

    # Build query
    query = (
        select(
            date_trunc.label("period"),
            func.coalesce(func.sum(SessionUsage.total_prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(SessionUsage.total_completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(SessionUsage.total_tokens), 0).label("total_tokens"),
        )
        .select_from(SessionUsage)
        .where(SessionUsage.created_at >= start_time)
        .group_by("period")
        .order_by("period")
    )

    if tenant_id:
        query = query.where(SessionUsage.tenant_id == tenant_id)

    results = db.execute(query).all()

    labels = []
    prompt_tokens = []
    completion_tokens = []
    total_tokens = []

    for row in results:
        if time_range == "day":
            labels.append(row.period.strftime("%H:%M"))
        else:
            labels.append(row.period.strftime("%Y-%m-%d"))
        prompt_tokens.append(int(row.prompt_tokens))
        completion_tokens.append(int(row.completion_tokens))
        total_tokens.append(int(row.total_tokens))

    return {
        "labels": labels,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


@router.get("/model-distribution")
def get_model_distribution(
    time_range: Literal["day", "week", "month"] = Query("day"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, int]:
    """
    Get model usage distribution

    Returns:
        Dictionary mapping model names to usage counts
    """
    start_time = get_time_filter(time_range)

    # Build query
    query = (
        select(
            SessionAnalysisLog.model_name,
            func.count(SessionAnalysisLog.id).label("count"),
        )
        .select_from(SessionAnalysisLog)
        .where(SessionAnalysisLog.analyzed_at >= start_time)
        .where(SessionAnalysisLog.model_name.isnot(None))
        .group_by(SessionAnalysisLog.model_name)
        .order_by(desc("count"))
    )

    if tenant_id:
        query = query.where(SessionAnalysisLog.tenant_id == tenant_id)

    results = db.execute(query).all()

    return {row.model_name: int(row.count) for row in results}


@router.get("/safety-distribution")
def get_safety_distribution(
    time_range: Literal["day", "week", "month"] = Query("day"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, int]:
    """
    Get safety level distribution

    Returns:
        Dictionary mapping safety levels (green, yellow, red) to counts
    """
    start_time = get_time_filter(time_range)

    # Build query
    query = (
        select(
            SessionAnalysisLog.safety_level,
            func.count(SessionAnalysisLog.id).label("count"),
        )
        .select_from(SessionAnalysisLog)
        .where(SessionAnalysisLog.analyzed_at >= start_time)
        .where(SessionAnalysisLog.safety_level.isnot(None))
        .group_by(SessionAnalysisLog.safety_level)
        .order_by(desc("count"))
    )

    if tenant_id:
        query = query.where(SessionAnalysisLog.tenant_id == tenant_id)

    results = db.execute(query).all()

    return {row.safety_level: int(row.count) for row in results}


@router.get("/top-users")
def get_top_users(
    time_range: Literal["day", "week", "month"] = Query("day"),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """
    Get top users by usage

    Returns:
        List of users with:
        - email
        - total_tokens
        - total_sessions
        - total_cost_usd
        - total_minutes
    """
    start_time = get_time_filter(time_range)

    # Build query
    query = (
        select(
            Counselor.email,
            func.coalesce(func.sum(SessionUsage.total_tokens), 0).label("total_tokens"),
            func.count(func.distinct(SessionUsage.session_id)).label("total_sessions"),
            func.coalesce(func.sum(SessionUsage.estimated_cost_usd), 0).label("total_cost_usd"),
            func.coalesce(func.sum(SessionUsage.duration_seconds), 0).label("total_seconds"),
        )
        .select_from(SessionUsage)
        .join(Counselor, SessionUsage.counselor_id == Counselor.id)
        .where(SessionUsage.created_at >= start_time)
        .group_by(Counselor.email)
        .order_by(desc("total_tokens"))
        .limit(limit)
    )

    if tenant_id:
        query = query.where(SessionUsage.tenant_id == tenant_id)

    results = db.execute(query).all()

    return [
        {
            "email": row.email,
            "total_tokens": int(row.total_tokens),
            "total_sessions": int(row.total_sessions),
            "total_cost_usd": float(row.total_cost_usd),
            "total_minutes": round(float(row.total_seconds) / 60, 2),
        }
        for row in results
    ]


@router.get("/user-daily-usage")
def get_user_daily_usage(
    counselor_id: UUID = Query(...),
    time_range: Literal["day", "week", "month"] = Query("month"),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """
    Get daily usage for a specific user

    Returns:
        List of daily statistics:
        - date
        - sessions
        - tokens
        - cost_usd
        - minutes
    """
    start_time = get_time_filter(time_range)

    # Build query
    query = (
        select(
            func.date_trunc("day", SessionUsage.created_at).label("date"),
            func.count(func.distinct(SessionUsage.session_id)).label("sessions"),
            func.coalesce(func.sum(SessionUsage.total_tokens), 0).label("tokens"),
            func.coalesce(func.sum(SessionUsage.estimated_cost_usd), 0).label("cost_usd"),
            func.coalesce(func.sum(SessionUsage.duration_seconds), 0).label("seconds"),
        )
        .select_from(SessionUsage)
        .where(
            and_(
                SessionUsage.counselor_id == counselor_id,
                SessionUsage.created_at >= start_time,
            )
        )
        .group_by("date")
        .order_by("date")
    )

    results = db.execute(query).all()

    return [
        {
            "date": row.date.strftime("%Y-%m-%d"),
            "sessions": int(row.sessions),
            "tokens": int(row.tokens),
            "cost_usd": float(row.cost_usd),
            "minutes": round(float(row.seconds) / 60, 2),
        }
        for row in results
    ]


@router.get("/overall-stats")
def get_overall_stats(
    time_range: Literal["day", "week", "month"] = Query("month"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Get overall statistics

    Returns:
        - avg_tokens_per_day
        - avg_sessions_per_day
        - peak_date
        - peak_value (tokens)
        - monthly_growth_pct
    """
    start_time = get_time_filter(time_range)

    # Get daily statistics
    query = (
        select(
            func.date_trunc("day", SessionUsage.created_at).label("date"),
            func.coalesce(func.sum(SessionUsage.total_tokens), 0).label("tokens"),
            func.count(func.distinct(SessionUsage.session_id)).label("sessions"),
        )
        .select_from(SessionUsage)
        .where(SessionUsage.created_at >= start_time)
        .group_by("date")
        .order_by("date")
    )

    if tenant_id:
        query = query.where(SessionUsage.tenant_id == tenant_id)

    results = db.execute(query).all()

    if not results:
        return {
            "avg_tokens_per_day": 0,
            "avg_sessions_per_day": 0,
            "peak_date": None,
            "peak_value": 0,
            "monthly_growth_pct": 0,
        }

    # Calculate averages
    total_tokens = sum(row.tokens for row in results)
    total_sessions = sum(row.sessions for row in results)
    num_days = len(results)

    avg_tokens_per_day = total_tokens / num_days if num_days > 0 else 0
    avg_sessions_per_day = total_sessions / num_days if num_days > 0 else 0

    # Find peak day
    peak_row = max(results, key=lambda r: r.tokens)
    peak_date = peak_row.date.strftime("%Y-%m-%d")
    peak_value = int(peak_row.tokens)

    # Calculate monthly growth (compare first week vs last week)
    monthly_growth_pct = 0
    if time_range == "month" and num_days >= 14:
        first_week = results[:7]
        last_week = results[-7:]
        first_week_avg = sum(r.tokens for r in first_week) / 7
        last_week_avg = sum(r.tokens for r in last_week) / 7
        if first_week_avg > 0:
            monthly_growth_pct = ((last_week_avg - first_week_avg) / first_week_avg) * 100

    return {
        "avg_tokens_per_day": round(avg_tokens_per_day, 2),
        "avg_sessions_per_day": round(avg_sessions_per_day, 2),
        "peak_date": peak_date,
        "peak_value": peak_value,
        "monthly_growth_pct": round(monthly_growth_pct, 2),
    }


@router.get("/export-csv")
def export_csv(
    time_range: Literal["day", "week", "month"] = Query("month"),
    data_type: Literal["users", "sessions"] = Query("users"),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    """
    Export data as CSV

    Args:
        data_type: "users" for user summary, "sessions" for session details
    """
    start_time = get_time_filter(time_range)

    # Create CSV in memory
    output = io.StringIO()

    if data_type == "users":
        # Export user summary
        query = (
            select(
                Counselor.email,
                Counselor.full_name,
                Counselor.tenant_id,
                func.coalesce(func.sum(SessionUsage.total_tokens), 0).label("total_tokens"),
                func.count(func.distinct(SessionUsage.session_id)).label("total_sessions"),
                func.coalesce(func.sum(SessionUsage.estimated_cost_usd), 0).label("total_cost_usd"),
                func.coalesce(func.sum(SessionUsage.duration_seconds), 0).label("total_seconds"),
            )
            .select_from(SessionUsage)
            .join(Counselor, SessionUsage.counselor_id == Counselor.id)
            .where(SessionUsage.created_at >= start_time)
            .group_by(Counselor.email, Counselor.full_name, Counselor.tenant_id)
            .order_by(desc("total_tokens"))
        )

        results = db.execute(query).all()

        writer = csv.DictWriter(
            output,
            fieldnames=["email", "full_name", "tenant_id", "total_tokens", "total_sessions", "total_cost_usd", "total_minutes"],
        )
        writer.writeheader()

        for row in results:
            writer.writerow({
                "email": row.email,
                "full_name": row.full_name,
                "tenant_id": row.tenant_id,
                "total_tokens": int(row.total_tokens),
                "total_sessions": int(row.total_sessions),
                "total_cost_usd": float(row.total_cost_usd),
                "total_minutes": round(float(row.total_seconds) / 60, 2),
            })

    else:  # sessions
        # Export session details
        query = (
            select(
                SessionUsage.created_at,
                Counselor.email,
                SessionUsage.tenant_id,
                SessionUsage.total_tokens,
                SessionUsage.estimated_cost_usd,
                SessionUsage.duration_seconds,
                SessionUsage.status,
            )
            .select_from(SessionUsage)
            .join(Counselor, SessionUsage.counselor_id == Counselor.id)
            .where(SessionUsage.created_at >= start_time)
            .order_by(desc(SessionUsage.created_at))
        )

        results = db.execute(query).all()

        writer = csv.DictWriter(
            output,
            fieldnames=["timestamp", "email", "tenant_id", "tokens", "cost_usd", "duration_minutes", "status"],
        )
        writer.writeheader()

        for row in results:
            writer.writerow({
                "timestamp": row.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "email": row.email,
                "tenant_id": row.tenant_id,
                "tokens": int(row.total_tokens or 0),
                "cost_usd": float(row.estimated_cost_usd or 0),
                "duration_minutes": round(float(row.duration_seconds or 0) / 60, 2),
                "status": row.status,
            })

    # Return CSV response
    csv_content = output.getvalue()
    filename = f"{data_type}_{time_range}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
