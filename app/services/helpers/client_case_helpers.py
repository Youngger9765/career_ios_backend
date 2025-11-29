"""
Client-Case Helper Functions
Extracted from ClientCaseService to reduce complexity
"""
from datetime import datetime
from typing import Any, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models.case import Case, CaseStatus
from app.models.client import Client


def generate_client_code(db: DBSession, tenant_id: str) -> str:
    """Generate unique client code in format C0001, C0002, etc."""
    result = db.execute(
        select(Client.code)
        .where(Client.tenant_id == tenant_id)
        .where(Client.code.like("C%"))
        .order_by(Client.code.desc())
    )
    codes = result.scalars().all()

    max_num = 0
    for code in codes:
        if code.startswith("C") and code[1:].isdigit():
            num = int(code[1:])
            if num > max_num:
                max_num = num

    next_num = max_num + 1
    return f"C{next_num:04d}"


def generate_case_number(db: DBSession, tenant_id: str) -> str:
    """Generate unique case number in format CASE0001, CASE0002, etc."""
    result = db.execute(
        select(Case.case_number)
        .where(Case.tenant_id == tenant_id)
        .where(Case.case_number.like("CASE%"))
        .order_by(Case.case_number.desc())
    )
    numbers = result.scalars().all()

    max_num = 0
    for num_str in numbers:
        if num_str.startswith("CASE") and num_str[4:].isdigit():
            num = int(num_str[4:])
            if num > max_num:
                max_num = num

    next_num = max_num + 1
    return f"CASE{next_num:04d}"


def map_case_status_to_label(status: CaseStatus) -> str:
    """Map case status to Chinese label"""
    status_map = {
        CaseStatus.NOT_STARTED: "未開始",
        CaseStatus.IN_PROGRESS: "進行中",
        CaseStatus.COMPLETED: "已完成",
    }
    return status_map.get(status, "未知")


def format_session_date(dt: Optional[datetime]) -> Optional[str]:
    """Format session date for display: 2026/01/22 19:30"""
    if not dt:
        return None
    return dt.strftime("%Y/%m/%d %H:%M")


def normalize_case_status(status: Any) -> Tuple[int, CaseStatus]:
    """Normalize case status to (int_value, enum)"""
    if isinstance(status, int):
        return status, CaseStatus(status)
    elif isinstance(status, CaseStatus):
        return status.value, status
    else:
        # Legacy string data
        status_map = {
            "ACTIVE": CaseStatus.NOT_STARTED,
            "IN_PROGRESS": CaseStatus.IN_PROGRESS,
            "COMPLETED": CaseStatus.COMPLETED,
            "SUSPENDED": CaseStatus.IN_PROGRESS,
            "REFERRED": CaseStatus.COMPLETED,
            "NOT_STARTED": CaseStatus.NOT_STARTED,
        }
        status_enum = status_map.get(str(status).upper(), CaseStatus.NOT_STARTED)
        return status_enum.value, status_enum
