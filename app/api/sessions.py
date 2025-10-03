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
    """
    Upload audio file for session (Mode 1)

    Flow:
    1. Save audio file to storage
    2. Update session with audio_path and source_type='audio'
    3. Create async job for STT processing
    4. Return job_id for status tracking
    """

    if settings.MOCK_MODE:
        # Mock response
        await asyncio.sleep(settings.MOCK_DELAY)
        return {
            "session_id": session_id,
            "file_name": file.filename,
            "file_size": 1024 * 1024 * 45,
            "duration_seconds": duration_seconds or 2730,
            "audio_path": f"gs://mock-bucket/audio_{uuid.uuid4()}.m4a",
            "job_id": str(uuid.uuid4()),
            "message": "Audio uploaded successfully, processing started"
        }

    # TODO: Real implementation
    # from app.services.storage import storage_service
    # from app.services.stt_service import stt_service
    # from app.models.job import Job
    # from app.database import get_db

    # 1. Upload to storage
    # audio_path = await storage_service.upload_audio(file, session_id)

    # 2. Update session
    # async with get_db() as db:
    #     session = await db.get(Session, session_id)
    #     session.audio_path = audio_path
    #     session.source_type = 'audio'
    #     await db.commit()

    # 3. Create STT job
    #     job = Job(
    #         session_id=session_id,
    #         type='stt',
    #         status='queued'
    #     )
    #     db.add(job)
    #     await db.commit()

    # 4. Trigger async STT processing
    # asyncio.create_task(process_stt_job(job.id))

    # return {"job_id": job.id, "message": "Processing started"}

    raise HTTPException(status_code=501, detail="Real implementation pending - use MOCK_MODE=true")


@router.post("/{session_id}/upload-transcript")
async def upload_transcript(
    session_id: str,
    transcript: str = Form(...),
    sanitize: bool = Form(False)
):
    """
    Upload transcript directly (Mode 2)

    Flow:
    1. Update session with transcript_text and source_type='text'
    2. Optional: sanitize transcript
    3. Return session info
    """

    if settings.MOCK_MODE:
        await asyncio.sleep(settings.MOCK_DELAY)
        return {
            "session_id": session_id,
            "transcript_length": len(transcript),
            "source_type": "text",
            "sanitized": sanitize,
            "message": "Transcript uploaded successfully"
        }

    # TODO: Real implementation
    # from app.services.sanitizer_service import sanitizer_service
    # from app.database import get_db

    # async with get_db() as db:
    #     session = await db.get(Session, session_id)
    #     session.transcript_text = transcript
    #     session.source_type = 'text'
    #
    #     if sanitize:
    #         sanitized_text, metadata = sanitizer_service.sanitize_session_transcript(transcript)
    #         session.transcript_sanitized = sanitized_text
    #
    #     await db.commit()
    #     return {"session_id": session_id, "message": "Transcript saved"}

    raise HTTPException(status_code=501, detail="Real implementation pending - use MOCK_MODE=true")


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