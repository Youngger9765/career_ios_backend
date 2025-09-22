from fastapi import APIRouter, HTTPException
from typing import List
from app.schemas.job import JobResponse, JobCreate
from app.utils.mock_data import mock_generator
from app.models.job import JobStatus

router = APIRouter()


@router.get("/", response_model=List[JobResponse])
async def list_jobs(session_id: str = None, status: JobStatus = None):
    """List jobs with optional filters"""
    jobs = [mock_generator.generate_job(session_id) for _ in range(5)]
    
    if status:
        for job in jobs:
            job["status"] = status
    
    return [JobResponse(**job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get job status and details"""
    job = mock_generator.generate_job()
    job["id"] = job_id
    return JobResponse(**job)


@router.post("/", response_model=JobResponse, status_code=201)
async def create_job(job: JobCreate):
    """Create new processing job"""
    job_data = mock_generator.generate_job()
    job_data.update(job.dict())
    return JobResponse(**job_data)


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a pending or processing job"""
    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Job cancelled successfully"
    }


@router.post("/{job_id}/retry")
async def retry_job(job_id: str):
    """Retry a failed job"""
    job = mock_generator.generate_job()
    job["id"] = job_id
    job["status"] = JobStatus.PENDING
    job["retry_count"] = job.get("retry_count", 0) + 1
    return JobResponse(**job)