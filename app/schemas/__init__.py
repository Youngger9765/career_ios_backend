"""Pydantic schemas for request/response models"""

from .auth import CounselorInfo, LoginRequest, TokenResponse
from .case import CaseCreate, CaseResponse, CaseUpdate
from .client import ClientCreate, ClientListResponse, ClientResponse, ClientUpdate
from .job import JobCreate, JobResponse
from .reminder import ReminderCreate, ReminderResponse, ReminderUpdate
from .report import ReportListResponse, ReportResponse
from .session import AudioUpload, SessionCreate, SessionResponse

__all__ = [
    # Auth
    "LoginRequest",
    "TokenResponse",
    "CounselorInfo",
    # Client
    "ClientCreate",
    "ClientResponse",
    "ClientUpdate",
    "ClientListResponse",
    # Case
    "CaseCreate",
    "CaseResponse",
    "CaseUpdate",
    # Session
    "SessionCreate",
    "SessionResponse",
    "AudioUpload",
    # Job
    "JobResponse",
    "JobCreate",
    # Report
    "ReportResponse",
    "ReportListResponse",
    # Reminder
    "ReminderCreate",
    "ReminderResponse",
    "ReminderUpdate",
]
