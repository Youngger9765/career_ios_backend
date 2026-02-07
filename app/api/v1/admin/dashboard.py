"""
Admin Dashboard API - AI Monitoring Dashboard
Provides analytics for AI usage, costs, tokens, and user activity
"""
import csv
import io
import logging
from datetime import datetime, timedelta, timezone
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
        - total_cost_usd: Sum of estimated costs (ElevenLabs + Gemini)
        - total_sessions: Count of unique sessions
        - active_users: Count of unique counselors
    """
    start_time = get_time_filter(time_range)

    # Calculate ElevenLabs cost from duration (not from estimated_cost_usd which contains total cost)
    ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND = 0.40 / 3600.0  # noqa: N806 - Constant in function

    elevenlabs_query = select(
        func.coalesce(func.sum(SessionUsage.duration_seconds * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND), 0).label("elevenlabs_cost")
    ).select_from(SessionUsage).where(SessionUsage.created_at >= start_time)

    if tenant_id:
        elevenlabs_query = elevenlabs_query.where(SessionUsage.tenant_id == tenant_id)

    elevenlabs_result = db.execute(elevenlabs_query).first()
    elevenlabs_cost = float(elevenlabs_result.elevenlabs_cost) if elevenlabs_result else 0.0

    # 2. Gemini cost from SessionAnalysisLog.estimated_cost_usd
    gemini_query = select(
        func.coalesce(func.sum(SessionAnalysisLog.estimated_cost_usd), 0).label("gemini_cost")
    ).select_from(SessionAnalysisLog).where(SessionAnalysisLog.analyzed_at >= start_time)

    if tenant_id:
        gemini_query = gemini_query.where(SessionAnalysisLog.tenant_id == tenant_id)

    gemini_result = db.execute(gemini_query).first()
    gemini_cost = float(gemini_result.gemini_cost) if gemini_result else 0.0

    # 3. Session counts and active users
    stats_query = select(
        func.count(func.distinct(SessionUsage.session_id)).label("total_sessions"),
        func.count(func.distinct(SessionUsage.counselor_id)).label("active_users"),
    ).select_from(SessionUsage).where(SessionUsage.created_at >= start_time)

    if tenant_id:
        stats_query = stats_query.where(SessionUsage.tenant_id == tenant_id)

    result = db.execute(stats_query).first()

    return {
        "total_cost_usd": round(elevenlabs_cost + gemini_cost, 4),
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


@router.get("/cost-breakdown")
def get_cost_breakdown(
    time_range: Literal["day", "week", "month"] = Query("day"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Get cost breakdown by service

    Returns:
        {
            "services": [
                {
                    "name": "ElevenLabs STT",
                    "cost": 12.34,
                    "percentage": 45.6,
                    "usage": "123.4 hours"
                },
                ...
            ],
            "total_cost": 56.78
        }
    """
    from sqlalchemy import case

    from app.core.pricing import (
        ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND,
        calculate_gemini_cost,
    )

    start_time = get_time_filter(time_range)

    # BUG FIX 1: Standardize model names using CASE WHEN to avoid duplicates
    # Group by display_name instead of raw model_name
    model_query = (
        select(
            case(
                (SessionAnalysisLog.model_name.like("%flash-lite%"), "Gemini Flash Lite"),
                (SessionAnalysisLog.model_name.like("%1.5-flash%"), "Gemini Flash 1.5"),
                else_="Other"
            ).label("display_name"),
            func.coalesce(func.sum(SessionAnalysisLog.prompt_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(SessionAnalysisLog.completion_tokens), 0).label("output_tokens"),
        )
        .select_from(SessionAnalysisLog)
        .where(SessionAnalysisLog.analyzed_at >= start_time)
        .where(SessionAnalysisLog.model_name.isnot(None))
        .group_by("display_name")
    )

    if tenant_id:
        model_query = model_query.where(SessionAnalysisLog.tenant_id == tenant_id)

    model_results = db.execute(model_query).all()

    # Map display names to pricing
    display_name_pricing = {
        "Gemini Flash Lite": {
            "input_price": 0.075,
            "output_price": 0.30,
        },
        "Gemini Flash 1.5": {
            "input_price": 0.50,
            "output_price": 3.00,
        },
    }

    # Calculate costs by service
    services = []
    total_cost = 0.0

    # Process AI models
    for row in model_results:
        display_name = row.display_name
        input_tokens = int(row.input_tokens)
        output_tokens = int(row.output_tokens)

        # Skip "Other" category
        if display_name == "Other":
            logger.warning("Skipping unknown model category: Other")
            continue

        # Get pricing info
        pricing = display_name_pricing.get(display_name)
        if not pricing:
            logger.warning(f"Unknown display name in cost breakdown: {display_name}")
            continue

        # Calculate cost
        cost = calculate_gemini_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_price_per_1m=pricing["input_price"],
            output_price_per_1m=pricing["output_price"],
        )

        services.append({
            "name": display_name,
            "cost": round(cost, 4),
            "percentage": 0,  # Will calculate later
            "usage": f"{(input_tokens + output_tokens) / 1_000_000:.2f}M tokens"
        })
        total_cost += cost

    # Get ElevenLabs STT costs (from SessionUsage duration)
    duration_query = select(
        func.coalesce(func.sum(SessionUsage.duration_seconds), 0).label("total_seconds")
    ).select_from(SessionUsage).where(SessionUsage.created_at >= start_time)

    if tenant_id:
        duration_query = duration_query.where(SessionUsage.tenant_id == tenant_id)

    duration_result = db.execute(duration_query).first()
    total_seconds = float(duration_result.total_seconds) if duration_result else 0.0

    elevenlabs_cost = total_seconds * ELEVENLABS_SCRIBE_V2_REALTIME_USD_PER_SECOND
    if elevenlabs_cost > 0:
        services.append({
            "name": "ElevenLabs STT",
            "cost": round(elevenlabs_cost, 4),
            "percentage": 0,  # Will calculate later
            "usage": f"{total_seconds / 3600:.1f} hours"
        })
        total_cost += elevenlabs_cost

    # Calculate percentages
    for service in services:
        if total_cost > 0:
            service["percentage"] = round((service["cost"] / total_cost) * 100, 1)

    # Sort by cost descending
    services.sort(key=lambda x: x["cost"], reverse=True)

    return {
        "services": services,
        "total_cost": round(total_cost, 4)
    }


@router.get("/session-trend")
def get_session_trend(
    time_range: Literal["day", "week", "month"] = Query("day"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Get daily session count trend

    Returns:
        {
            "labels": ["2/1", "2/2", ...],
            "sessions": [12, 15, 8, ...],
            "duration_hours": [2.5, 3.1, 1.8, ...]
        }
    """
    start_time = get_time_filter(time_range)

    # Determine date truncation
    if time_range == "day":
        date_trunc = func.date_trunc("hour", SessionUsage.created_at)
    else:
        date_trunc = func.date_trunc("day", SessionUsage.created_at)

    # Build query
    query = (
        select(
            date_trunc.label("period"),
            func.count(func.distinct(SessionUsage.session_id)).label("sessions"),
            func.coalesce(func.sum(SessionUsage.duration_seconds), 0).label("total_seconds"),
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
    sessions = []
    duration_hours = []

    for row in results:
        if time_range == "day":
            labels.append(row.period.strftime("%H:%M"))
        else:
            labels.append(row.period.strftime("%m/%d"))
        sessions.append(int(row.sessions))
        duration_hours.append(round(float(row.total_seconds) / 3600, 2))

    return {
        "labels": labels,
        "sessions": sessions,
        "duration_hours": duration_hours,
    }


@router.get("/model-distribution")
def get_model_distribution(
    time_range: Literal["day", "week", "month"] = Query("day"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Get model usage distribution by cost (not token count)

    DEPRECATED: Kept for backward compatibility.
    Use /daily-active-users instead.

    Returns:
        {
            "labels": ["Gemini Flash Lite", "Gemini Flash 1.5", ...],
            "costs": [12.34, 5.67, ...],
            "tokens": [1234567, 567890, ...]
        }
    """
    from app.core.pricing import MODEL_PRICING_MAP, calculate_gemini_cost

    start_time = get_time_filter(time_range)

    # Build query
    query = (
        select(
            SessionAnalysisLog.model_name,
            func.coalesce(func.sum(SessionAnalysisLog.prompt_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(SessionAnalysisLog.completion_tokens), 0).label("output_tokens"),
        )
        .select_from(SessionAnalysisLog)
        .where(SessionAnalysisLog.analyzed_at >= start_time)
        .where(SessionAnalysisLog.model_name.isnot(None))
        .group_by(SessionAnalysisLog.model_name)
        .order_by(desc("input_tokens"))
    )

    if tenant_id:
        query = query.where(SessionAnalysisLog.tenant_id == tenant_id)

    results = db.execute(query).all()

    labels = []
    costs = []
    tokens = []

    for row in results:
        model_name = row.model_name
        input_tokens = int(row.input_tokens)
        output_tokens = int(row.output_tokens)
        total_tokens = input_tokens + output_tokens

        # Get pricing info
        pricing = MODEL_PRICING_MAP.get(model_name)
        if not pricing:
            logger.warning(f"Unknown model in distribution: {model_name}")
            continue

        # Calculate cost
        cost = calculate_gemini_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_price_per_1m=pricing["input_price"],
            output_price_per_1m=pricing["output_price"],
        )

        labels.append(pricing["display_name"])
        costs.append(round(cost, 4))
        tokens.append(total_tokens)

    return {
        "labels": labels,
        "costs": costs,
        "tokens": tokens,
    }


@router.get("/daily-active-users")
def get_daily_active_users(
    time_range: Literal["day", "week", "month"] = Query("day"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Get daily active users trend

    Returns:
        {
            "labels": ["2/1", "2/2", ...],
            "data": [12, 15, 8, 20, ...]
        }
    """
    start_time = get_time_filter(time_range)
    end_time = datetime.now(timezone.utc)

    # Determine date truncation based on time range
    if time_range == "day":
        date_trunc = func.date_trunc("hour", SessionUsage.created_at)
    else:
        date_trunc = func.date_trunc("day", SessionUsage.created_at)

    # Build query - Count unique users per period
    query = (
        select(
            date_trunc.label("period"),
            func.count(func.distinct(SessionUsage.counselor_id)).label("user_count")
        )
        .select_from(SessionUsage)
        .where(SessionUsage.created_at >= start_time)
        .group_by("period")
        .order_by("period")
    )

    if tenant_id:
        query = query.where(SessionUsage.tenant_id == tenant_id)

    results = db.execute(query).all()

    # BUG FIX 4: Fill missing dates/hours with zeros
    data_dict = {row.period: int(row.user_count) for row in results}

    labels = []
    data = []

    if time_range == "day":
        # Fill hourly data for past 24 hours
        current = start_time.replace(minute=0, second=0, microsecond=0)
        while current <= end_time:
            labels.append(current.strftime("%H:%M"))
            data.append(data_dict.get(current, 0))
            current += timedelta(hours=1)
    else:
        # Fill daily data for week/month
        current = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        while current.date() <= end_time.date():
            labels.append(current.strftime("%m/%d"))
            data.append(data_dict.get(current, 0))
            current += timedelta(days=1)

    return {
        "labels": labels,
        "data": data,
    }


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
        - gemini_flash_tokens (Gemini 1.5 Flash tokens)
        - gemini_lite_tokens (Gemini Flash Lite tokens)
        - elevenlabs_hours (ElevenLabs duration in hours)
        - total_sessions
        - total_cost_usd
        - total_minutes
    """
    from sqlalchemy import case

    start_time = get_time_filter(time_range)

    # Build query with separate token counts per model
    query = (
        select(
            Counselor.email,
            # Gemini Flash tokens (includes both Flash 1.5 and Flash 3)
            func.coalesce(
                func.sum(
                    case(
                        (SessionAnalysisLog.model_name.in_(["gemini-1.5-flash-latest", "gemini-3-flash-preview"]),
                         SessionAnalysisLog.prompt_tokens + SessionAnalysisLog.completion_tokens),
                        else_=0
                    )
                ), 0
            ).label("gemini_flash_tokens"),

            # Gemini Lite tokens (from SessionAnalysisLog where model contains 'flash-lite')
            func.coalesce(
                func.sum(
                    case(
                        (SessionAnalysisLog.model_name.like("%flash-lite%"),
                         SessionAnalysisLog.prompt_tokens + SessionAnalysisLog.completion_tokens),
                        else_=0
                    )
                ), 0
            ).label("gemini_lite_tokens"),

            # ElevenLabs duration in hours (from SessionUsage)
            func.coalesce(
                func.sum(SessionUsage.duration_seconds) / 3600.0, 0
            ).label("elevenlabs_hours"),

            func.count(func.distinct(SessionUsage.session_id)).label("total_sessions"),
            # Calculate total cost: ElevenLabs (from duration) + Gemini (from estimated_cost_usd)
            (
                func.coalesce(func.sum(SessionUsage.duration_seconds * 0.40 / 3600.0), 0) +
                func.coalesce(func.sum(SessionAnalysisLog.estimated_cost_usd), 0)
            ).label("total_cost_usd"),
            func.coalesce(func.sum(SessionUsage.duration_seconds), 0).label("total_seconds"),
        )
        .select_from(SessionUsage)
        .join(Counselor, SessionUsage.counselor_id == Counselor.id)
        .outerjoin(SessionAnalysisLog, SessionUsage.session_id == SessionAnalysisLog.session_id)
        .where(SessionUsage.created_at >= start_time)
        .group_by(Counselor.email)
        .order_by(desc("total_cost_usd"))
        .limit(limit)
    )

    if tenant_id:
        query = query.where(SessionUsage.tenant_id == tenant_id)

    results = db.execute(query).all()

    return [
        {
            "email": row.email,
            "gemini_flash_tokens": int(row.gemini_flash_tokens),
            "gemini_lite_tokens": int(row.gemini_lite_tokens),
            "elevenlabs_hours": round(float(row.elevenlabs_hours), 1),
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
        - avg_cost_per_day: Average cost per day in USD
        - avg_sessions_per_day: Average sessions per day
        - peak_date: Date with highest cost
        - peak_value: Cost on peak date (USD)
        - monthly_growth_pct: Month-over-month growth percentage
    """
    start_time = get_time_filter(time_range)

    # BUG FIX 3: Use cost instead of tokens
    # Get daily statistics with cost from both sources
    query = (
        select(
            func.date_trunc("day", SessionUsage.created_at).label("date"),
            func.coalesce(func.sum(SessionUsage.estimated_cost_usd), 0).label("elevenlabs_cost"),
            func.count(func.distinct(SessionUsage.session_id)).label("sessions"),
        )
        .select_from(SessionUsage)
        .where(SessionUsage.created_at >= start_time)
        .group_by("date")
        .order_by("date")
    )

    if tenant_id:
        query = query.where(SessionUsage.tenant_id == tenant_id)

    usage_results = db.execute(query).all()

    # Get Gemini costs by day
    gemini_query = (
        select(
            func.date_trunc("day", SessionAnalysisLog.analyzed_at).label("date"),
            func.coalesce(func.sum(SessionAnalysisLog.estimated_cost_usd), 0).label("gemini_cost"),
        )
        .select_from(SessionAnalysisLog)
        .where(SessionAnalysisLog.analyzed_at >= start_time)
        .group_by("date")
        .order_by("date")
    )

    if tenant_id:
        gemini_query = gemini_query.where(SessionAnalysisLog.tenant_id == tenant_id)

    gemini_results = db.execute(gemini_query).all()

    # Merge results by date
    gemini_costs_by_date = {row.date: float(row.gemini_cost) for row in gemini_results}

    daily_data = []
    for row in usage_results:
        date = row.date
        elevenlabs_cost = float(row.elevenlabs_cost)
        gemini_cost = gemini_costs_by_date.get(date, 0.0)
        total_cost = elevenlabs_cost + gemini_cost

        daily_data.append({
            "date": date,
            "cost": total_cost,
            "sessions": int(row.sessions),
        })

    if not daily_data:
        return {
            "avg_cost_per_day": 0.0,
            "avg_sessions_per_day": 0,
            "peak_date": None,
            "peak_value": 0.0,
            "monthly_growth_pct": 0.0,
        }

    # Calculate averages
    total_cost = sum(day["cost"] for day in daily_data)
    total_sessions = sum(day["sessions"] for day in daily_data)
    num_days = len(daily_data)

    avg_cost_per_day = total_cost / num_days if num_days > 0 else 0.0
    avg_sessions_per_day = total_sessions / num_days if num_days > 0 else 0

    # Find peak day
    peak_day = max(daily_data, key=lambda d: d["cost"])
    peak_date = peak_day["date"].strftime("%Y-%m-%d")
    peak_value = peak_day["cost"]

    # Calculate monthly growth (compare first week vs last week)
    monthly_growth_pct = 0.0
    if time_range == "month" and num_days >= 14:
        first_week = daily_data[:7]
        last_week = daily_data[-7:]
        first_week_avg = sum(d["cost"] for d in first_week) / 7
        last_week_avg = sum(d["cost"] for d in last_week) / 7
        if first_week_avg > 0:
            monthly_growth_pct = ((last_week_avg - first_week_avg) / first_week_avg) * 100

    return {
        "avg_cost_per_day": round(avg_cost_per_day, 4),
        "avg_sessions_per_day": round(avg_sessions_per_day, 2),
        "peak_date": peak_date,
        "peak_value": round(peak_value, 4),
        "monthly_growth_pct": round(monthly_growth_pct, 2),
    }


@router.get("/cost-per-user")
def get_cost_per_user(
    time_range: Literal["day", "week", "month"] = Query("month"),
    tenant_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[Dict]:
    """
    Get cost per user with anomaly detection

    Returns users sorted by cost, with:
    - total_cost_usd: Total cost for this user
    - sessions: Number of sessions
    - cost_per_session: Average cost per session
    - status: "normal", "high_cost", "test_account"
    - suggested_action: Recommended next step
    """

    start_time = get_time_filter(time_range)

    # Calculate total costs from both sources
    query = (
        select(
            Counselor.email,
            Counselor.full_name,
            # Total cost = ElevenLabs + Gemini
            (
                func.coalesce(func.sum(SessionUsage.estimated_cost_usd), 0)
            ).label("total_cost"),
            func.count(func.distinct(SessionUsage.session_id)).label("sessions"),
            func.coalesce(func.sum(SessionUsage.duration_seconds), 0).label("total_seconds"),
        )
        .select_from(SessionUsage)
        .join(Counselor, SessionUsage.counselor_id == Counselor.id)
        .where(SessionUsage.created_at >= start_time)
        .group_by(Counselor.email, Counselor.full_name)
        .order_by(desc("total_cost"))
        .limit(limit)
    )

    if tenant_id:
        query = query.where(SessionUsage.tenant_id == tenant_id)

    results = db.execute(query).all()

    # Add Gemini costs separately (from SessionAnalysisLog)
    gemini_query = (
        select(
            Counselor.email,
            func.coalesce(func.sum(SessionAnalysisLog.estimated_cost_usd), 0).label("gemini_cost")
        )
        .select_from(SessionAnalysisLog)
        .join(Counselor, SessionAnalysisLog.counselor_id == Counselor.id)
        .where(SessionAnalysisLog.analyzed_at >= start_time)
        .group_by(Counselor.email)
    )

    if tenant_id:
        gemini_query = gemini_query.where(SessionAnalysisLog.tenant_id == tenant_id)

    gemini_results = db.execute(gemini_query).all()
    gemini_costs = {row.email: float(row.gemini_cost) for row in gemini_results}

    # Calculate platform average for comparison
    total_cost = sum(float(row.total_cost) for row in results)
    total_sessions = sum(int(row.sessions) for row in results)
    platform_avg_cost_per_session = total_cost / total_sessions if total_sessions > 0 else 0

    # Classify users and suggest actions
    user_list = []
    for row in results:
        email = row.email
        elevenlabs_cost = float(row.total_cost)
        gemini_cost = gemini_costs.get(email, 0.0)
        total_cost = elevenlabs_cost + gemini_cost
        sessions = int(row.sessions)
        cost_per_session = total_cost / sessions if sessions > 0 else 0

        # Anomaly detection
        status = "normal"
        suggested_action = "-"

        # Test account detection (many sessions, low cost per session)
        if sessions > 100 and cost_per_session < platform_avg_cost_per_session * 0.5:
            status = "test_account"
            suggested_action = "Review and consider throttling"
        # High cost user (2x platform average)
        elif cost_per_session > platform_avg_cost_per_session * 2:
            status = "high_cost"
            suggested_action = "Contact for premium upgrade"

        user_list.append({
            "email": email,
            "full_name": row.full_name,
            "total_cost_usd": round(total_cost, 2),
            "sessions": sessions,
            "cost_per_session": round(cost_per_session, 2),
            "total_minutes": round(float(row.total_seconds) / 60, 1),
            "status": status,
            "suggested_action": suggested_action,
        })

    return user_list


@router.get("/user-segments")
def get_user_segments(
    time_range: Literal["day", "week", "month"] = Query("month"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Get user segmentation: Power Users, Active, At-Risk, Churned

    Returns:
    - power_users: Top 10% by session count
    - active_users: Used in last 7 days
    - at_risk_users: No activity in 7+ days (but active in last 30)
    - churned_users: No activity in 30+ days
    """
    now = datetime.now(timezone.utc)

    # Get all users with activity
    base_query = (
        select(
            Counselor.id,
            Counselor.email,
            func.count(func.distinct(SessionUsage.session_id)).label("sessions"),
            func.max(SessionUsage.created_at).label("last_activity"),
            # Calculate total cost: ElevenLabs (from duration) + Gemini (from estimated_cost_usd)
            (
                func.coalesce(func.sum(SessionUsage.duration_seconds * 0.40 / 3600.0), 0) +
                func.coalesce(func.sum(SessionAnalysisLog.estimated_cost_usd), 0)
            ).label("total_cost"),
        )
        .select_from(Counselor)
        .outerjoin(SessionUsage, Counselor.id == SessionUsage.counselor_id)
        .outerjoin(SessionAnalysisLog, SessionUsage.session_id == SessionAnalysisLog.session_id)
        .where(Counselor.created_at < now - timedelta(days=7))  # Only users older than 7 days
        .group_by(Counselor.id, Counselor.email)
    )

    if tenant_id:
        base_query = base_query.where(Counselor.tenant_id == tenant_id)

    all_users = db.execute(base_query).all()

    # Segment users
    power_users = []
    active_users = []
    at_risk_users = []
    churned_users = []

    # Calculate 90th percentile for power users
    session_counts = [int(u.sessions) for u in all_users if u.sessions > 0]
    p90_threshold = sorted(session_counts)[int(len(session_counts) * 0.9)] if session_counts else 0

    for user in all_users:
        sessions = int(user.sessions)
        last_activity = user.last_activity
        total_cost = float(user.total_cost)

        # No activity at all
        if last_activity is None:
            churned_users.append({
                "email": user.email,
                "sessions": 0,
                "last_activity": None,
                "total_cost_usd": 0,
            })
            continue

        days_inactive = (now - last_activity).days

        # Power users (top 10%)
        if sessions >= p90_threshold and sessions > 0:
            power_users.append({
                "email": user.email,
                "sessions": sessions,
                "last_activity": last_activity.strftime("%Y-%m-%d %H:%M"),
                "total_cost_usd": round(total_cost, 2),
            })
        # At-risk users (7-30 days inactive)
        elif 7 <= days_inactive < 30:
            at_risk_users.append({
                "email": user.email,
                "sessions": sessions,
                "last_activity": last_activity.strftime("%Y-%m-%d %H:%M"),
                "days_inactive": days_inactive,
            })
        # Churned users (30+ days inactive)
        elif days_inactive >= 30:
            churned_users.append({
                "email": user.email,
                "sessions": sessions,
                "last_activity": last_activity.strftime("%Y-%m-%d %H:%M"),
                "days_inactive": days_inactive,
            })
        # Active users (< 7 days inactive)
        else:
            active_users.append({
                "email": user.email,
                "sessions": sessions,
                "last_activity": last_activity.strftime("%Y-%m-%d %H:%M"),
                "total_cost_usd": round(total_cost, 2),
            })

    # Calculate averages
    avg_sessions_power = sum(u["sessions"] for u in power_users) / len(power_users) if power_users else 0
    avg_cost_power = sum(u["total_cost_usd"] for u in power_users) / len(power_users) if power_users else 0
    avg_sessions_active = sum(u["sessions"] for u in active_users) / len(active_users) if active_users else 0
    avg_cost_active = sum(u["total_cost_usd"] for u in active_users) / len(active_users) if active_users else 0

    return {
        "power_users": {
            "count": len(power_users),
            "avg_sessions": round(avg_sessions_power, 1),
            "avg_cost_usd": round(avg_cost_power, 2),
            "suggested_action": "Upsell to premium tier",
            "users": power_users[:10],  # Top 10 for display
        },
        "active_users": {
            "count": len(active_users),
            "avg_sessions": round(avg_sessions_active, 1),
            "avg_cost_usd": round(avg_cost_active, 2),
            "suggested_action": "Maintain engagement",
            "users": active_users[:10],
        },
        "at_risk_users": {
            "count": len(at_risk_users),
            "suggested_action": "Send re-engagement email",
            "users": at_risk_users[:10],
        },
        "churned_users": {
            "count": len(churned_users),
            "suggested_action": "Archive or remove",
            "users": churned_users[:10],
        },
    }


@router.get("/cost-prediction")
def get_cost_prediction(
    time_range: Literal["month"] = Query("month"),
    tenant_id: Optional[str] = Query(None),
    current_user: Counselor = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict:
    """
    Predict next month's cost based on current trend

    Returns:
    - current_month_cost: Cost so far this month
    - days_elapsed: Days into current month
    - days_remaining: Days left in month
    - predicted_month_cost: Linear projection
    - daily_average: Average cost per day
    """
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Calculate days in month
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month = now.replace(month=now.month + 1, day=1)

    days_in_month = (next_month - month_start).days
    days_elapsed = (now - month_start).days + 1
    days_remaining = days_in_month - days_elapsed

    # Get current month cost (ElevenLabs)
    elevenlabs_query = select(
        func.coalesce(func.sum(SessionUsage.estimated_cost_usd), 0).label("cost")
    ).select_from(SessionUsage).where(SessionUsage.created_at >= month_start)

    if tenant_id:
        elevenlabs_query = elevenlabs_query.where(SessionUsage.tenant_id == tenant_id)

    elevenlabs_result = db.execute(elevenlabs_query).first()
    elevenlabs_cost = float(elevenlabs_result.cost) if elevenlabs_result else 0.0

    # Get current month cost (Gemini)
    gemini_query = select(
        func.coalesce(func.sum(SessionAnalysisLog.estimated_cost_usd), 0).label("cost")
    ).select_from(SessionAnalysisLog).where(SessionAnalysisLog.analyzed_at >= month_start)

    if tenant_id:
        gemini_query = gemini_query.where(SessionAnalysisLog.tenant_id == tenant_id)

    gemini_result = db.execute(gemini_query).first()
    gemini_cost = float(gemini_result.cost) if gemini_result else 0.0

    current_month_cost = elevenlabs_cost + gemini_cost

    # Simple linear projection
    daily_average = current_month_cost / days_elapsed if days_elapsed > 0 else 0
    predicted_month_cost = daily_average * days_in_month

    # Calculate growth vs last month
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)

    last_month_query = select(
        func.coalesce(func.sum(SessionUsage.estimated_cost_usd), 0).label("cost")
    ).select_from(SessionUsage).where(
        and_(
            SessionUsage.created_at >= last_month_start,
            SessionUsage.created_at < month_start
        )
    )

    if tenant_id:
        last_month_query = last_month_query.where(SessionUsage.tenant_id == tenant_id)

    last_month_result = db.execute(last_month_query).first()
    last_month_cost = float(last_month_result.cost) if last_month_result else 0.0

    # Add Gemini cost for last month
    gemini_last_query = select(
        func.coalesce(func.sum(SessionAnalysisLog.estimated_cost_usd), 0).label("cost")
    ).select_from(SessionAnalysisLog).where(
        and_(
            SessionAnalysisLog.analyzed_at >= last_month_start,
            SessionAnalysisLog.analyzed_at < month_start
        )
    )

    if tenant_id:
        gemini_last_query = gemini_last_query.where(SessionAnalysisLog.tenant_id == tenant_id)

    gemini_last_result = db.execute(gemini_last_query).first()
    last_month_cost += float(gemini_last_result.cost) if gemini_last_result else 0.0

    growth_pct = 0.0
    if last_month_cost > 0:
        growth_pct = ((predicted_month_cost - last_month_cost) / last_month_cost) * 100

    return {
        "current_month_cost": round(current_month_cost, 2),
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "daily_average": round(daily_average, 2),
        "predicted_month_cost": round(predicted_month_cost, 2),
        "last_month_cost": round(last_month_cost, 2),
        "growth_pct": round(growth_pct, 1),
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
        # Export user summary with separate token columns
        from sqlalchemy import case

        query = (
            select(
                Counselor.email,
                Counselor.full_name,
                Counselor.tenant_id,
                # Gemini Flash tokens (includes both Flash 1.5 and Flash 3)
                func.coalesce(
                    func.sum(
                        case(
                            (SessionAnalysisLog.model_name.in_(["gemini-1.5-flash-latest", "gemini-3-flash-preview"]),
                             SessionAnalysisLog.prompt_tokens + SessionAnalysisLog.completion_tokens),
                            else_=0
                        )
                    ), 0
                ).label("gemini_flash_tokens"),
                # Gemini Lite tokens
                func.coalesce(
                    func.sum(
                        case(
                            (SessionAnalysisLog.model_name.like("%flash-lite%"),
                             SessionAnalysisLog.prompt_tokens + SessionAnalysisLog.completion_tokens),
                            else_=0
                        )
                    ), 0
                ).label("gemini_lite_tokens"),
                # ElevenLabs hours
                func.coalesce(
                    func.sum(SessionUsage.duration_seconds) / 3600.0, 0
                ).label("elevenlabs_hours"),
                func.count(func.distinct(SessionUsage.session_id)).label("total_sessions"),
                # Calculate total cost: ElevenLabs (from duration) + Gemini (from estimated_cost_usd)
                (
                    func.coalesce(func.sum(SessionUsage.duration_seconds * 0.40 / 3600.0), 0) +
                    func.coalesce(func.sum(SessionAnalysisLog.estimated_cost_usd), 0)
                ).label("total_cost_usd"),
                func.coalesce(func.sum(SessionUsage.duration_seconds), 0).label("total_seconds"),
            )
            .select_from(SessionUsage)
            .join(Counselor, SessionUsage.counselor_id == Counselor.id)
            .outerjoin(SessionAnalysisLog, SessionUsage.session_id == SessionAnalysisLog.session_id)
            .where(SessionUsage.created_at >= start_time)
            .group_by(Counselor.email, Counselor.full_name, Counselor.tenant_id)
            .order_by(desc("total_cost_usd"))
        )

        results = db.execute(query).all()

        writer = csv.DictWriter(
            output,
            fieldnames=["email", "full_name", "tenant_id", "gemini_flash_tokens", "gemini_lite_tokens", "elevenlabs_hours", "total_sessions", "total_cost_usd", "total_minutes"],
        )
        writer.writeheader()

        for row in results:
            writer.writerow({
                "email": row.email,
                "full_name": row.full_name,
                "tenant_id": row.tenant_id,
                "gemini_flash_tokens": int(row.gemini_flash_tokens),
                "gemini_lite_tokens": int(row.gemini_lite_tokens),
                "elevenlabs_hours": f"{row.elevenlabs_hours:.1f}",
                "total_sessions": int(row.total_sessions),
                "total_cost_usd": f"{row.total_cost_usd:.2f}",
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
