"""
Client-Case Query Builder
Complex SQLAlchemy query building logic extracted from ClientCaseService
"""
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import func, select

from app.models.case import Case
from app.models.client import Client
from app.models.session import Session as SessionModel
from app.services.helpers.client_case_helpers import (
    format_session_date,
    map_case_status_to_label,
    normalize_case_status,
)


def build_client_case_list_query(tenant_id: str):
    """
    Build complex query for client-case list with session statistics.

    Returns:
        Tuple of (main_query, count_query)
    """
    # Subquery: first case per client
    case_subquery = (
        select(
            Case.client_id,
            func.min(Case.created_at).label("first_case_created_at"),
        )
        .where(
            Case.tenant_id == tenant_id,
            Case.deleted_at.is_(None),
        )
        .group_by(Case.client_id)
        .subquery()
    )

    # Subquery: session stats per case
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

    # Main query: join clients with first case and session stats
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

    # Count query
    count_query = select(func.count()).select_from(
        select(Client.id)
        .join(case_subquery, Client.id == case_subquery.c.client_id)
        .where(
            Client.tenant_id == tenant_id,
            Client.deleted_at.is_(None),
        )
        .subquery()
    )

    return query, count_query


def format_client_case_list_item(
    client, case, total_sessions, last_session_date
) -> Dict[str, Any]:
    """Format a single client-case list item with session stats."""
    status_value, status_enum = normalize_case_status(case.status)

    return {
        "client_id": client.id,
        "case_id": case.id,
        "counselor_id": client.counselor_id,
        "client_name": client.name,
        "client_code": client.code,
        "client_email": client.email,
        "identity_option": client.identity_option,
        "current_status": client.current_status,
        "case_number": case.case_number,
        "case_status": status_value,
        "case_status_label": map_case_status_to_label(status_enum),
        "last_session_date": last_session_date,
        "last_session_date_display": format_session_date(last_session_date),
        "total_sessions": total_sessions or 0,
        "case_created_at": case.created_at,
        "case_updated_at": case.updated_at,
    }


def sort_items_by_last_session_date(
    items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Sort items by last_session_date (newest first)."""
    min_datetime = datetime.min.replace(tzinfo=timezone.utc)

    def sort_key(item):
        dt = item["last_session_date"]
        if dt is None:
            return min_datetime
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    items.sort(key=sort_key, reverse=True)
    return items
