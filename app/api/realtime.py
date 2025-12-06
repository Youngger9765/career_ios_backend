"""
Realtime STT Counseling API
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.schemas.realtime import RealtimeAnalyzeRequest, RealtimeAnalyzeResponse
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/api/v1/realtime", tags=["Realtime Counseling"])

# Initialize Gemini service
gemini_service = GeminiService()


@router.post("/analyze", response_model=RealtimeAnalyzeResponse)
async def analyze_transcript(request: RealtimeAnalyzeRequest):
    """Analyze realtime counseling transcript with AI supervision.

    Returns summary, alerts, and suggestions for the counselor based on
    the conversation in the past 60 seconds.

    This is a demo feature with no authentication required.
    """
    try:
        # Convert speakers to dict format for service
        speakers_dict = [
            {"speaker": s.speaker, "text": s.text} for s in request.speakers
        ]

        # Call Gemini service for analysis
        analysis = await gemini_service.analyze_realtime_transcript(
            transcript=request.transcript,
            speakers=speakers_dict,
        )

        # Build response
        return RealtimeAnalyzeResponse(
            summary=analysis.get("summary", ""),
            alerts=analysis.get("alerts", []),
            suggestions=analysis.get("suggestions", []),
            time_range=request.time_range,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
