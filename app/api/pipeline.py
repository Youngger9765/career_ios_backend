from fastapi import APIRouter, HTTPException
import asyncio
from app.utils.mock_data import mock_generator
from app.core.config import settings
import uuid

router = APIRouter()


@router.post("/process")
async def start_pipeline(session_id: str, audio_file_path: str = None):
    """Start complete pipeline processing for a session"""
    pipeline_id = str(uuid.uuid4())
    
    return {
        "pipeline_id": pipeline_id,
        "session_id": session_id,
        "status": "started",
        "estimated_completion_time": "5-10 minutes",
        "steps": [
            "音訊上傳",
            "語音轉文字",
            "文字脫敏",
            "AI 分析",
            "報告生成"
        ],
        "tracking_url": f"/api/v1/pipeline/{pipeline_id}/status"
    }


@router.get("/{pipeline_id}/status")
async def get_pipeline_status(pipeline_id: str):
    """Get current pipeline processing status"""
    # Simulate processing delay
    if settings.MOCK_MODE:
        await asyncio.sleep(settings.MOCK_DELAY)
    
    return mock_generator.generate_pipeline_status()


@router.get("/demo")
async def get_demo_pipeline():
    """Get demo pipeline data for visualization"""
    return {
        "title": "諮商會談處理流程",
        "description": "從錄音上傳到報告生成的完整流程",
        "pipeline": mock_generator.generate_pipeline_status()
    }


@router.post("/{pipeline_id}/cancel")
async def cancel_pipeline(pipeline_id: str):
    """Cancel an ongoing pipeline process"""
    return {
        "pipeline_id": pipeline_id,
        "status": "cancelled",
        "cancelled_at": "2024-01-01T00:00:00Z"
    }