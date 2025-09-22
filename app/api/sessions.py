from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Optional
from app.schemas.session import SessionResponse, SessionCreate, AudioUpload
from app.utils.mock_data import mock_generator
import uuid
import asyncio
from app.core.config import settings

router = APIRouter()


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(case_id: Optional[str] = None):
    """List sessions, optionally filtered by case"""
    sessions = [mock_generator.generate_session(case_id) for _ in range(5)]
    return [SessionResponse(**session) for session in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get specific session details"""
    session = mock_generator.generate_session()
    session["id"] = session_id
    return SessionResponse(**session)


@router.post("/", response_model=SessionResponse, status_code=201)
async def create_session(session: SessionCreate):
    """Create new session"""
    session_data = mock_generator.generate_session()
    session_data.update(session.dict())
    return SessionResponse(**session_data)


@router.post("/{session_id}/upload-audio")
async def upload_audio(
    session_id: str,
    file: UploadFile = File(...),
    duration_seconds: Optional[int] = Form(None)
):
    """Upload audio file for session"""
    # Simulate file upload delay
    if settings.MOCK_MODE:
        await asyncio.sleep(settings.MOCK_DELAY)
    
    # Mock response
    return {
        "session_id": session_id,
        "file_name": file.filename,
        "file_size": 1024 * 1024 * 45,  # Mock 45MB
        "duration_seconds": duration_seconds or 2730,  # Mock 45:30
        "audio_path": f"gs://mock-bucket/audio_{uuid.uuid4()}.m4a",
        "job_id": str(uuid.uuid4()),
        "message": "Audio uploaded successfully, processing started"
    }


@router.get("/{session_id}/transcript")
async def get_transcript(session_id: str):
    """Get session transcript"""
    # Simulate processing delay
    if settings.MOCK_MODE:
        await asyncio.sleep(settings.MOCK_DELAY)
    
    return {
        "session_id": session_id,
        "transcript": mock_generator.generate_transcript(),
        "word_count": 5420,
        "duration": "45:30",
        "language": "zh-TW",
        "confidence": 0.95
    }