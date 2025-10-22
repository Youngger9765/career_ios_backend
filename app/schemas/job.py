from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from app.models.job import JobStatus, JobType
from app.schemas.base import BaseResponse, BaseSchema


class JobBase(BaseSchema):
    job_type: JobType
    status: JobStatus = JobStatus.PENDING


class JobCreate(JobBase):
    session_id: UUID
    input_data: Optional[Dict[str, Any]] = None
    job_metadata: Optional[Dict[str, Any]] = None


class JobResponse(BaseResponse, JobBase):
    session_id: UUID
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    output_data: Optional[Dict[str, Any]] = None
    job_metadata: Optional[Dict[str, Any]] = None
