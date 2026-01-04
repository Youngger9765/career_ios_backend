"""
Transcript API - ElevenLabs Token Generation

提供 iOS app 取得 ElevenLabs Speech-to-Text WebSocket token 的 endpoint。

其他分析功能請使用 iOS API:
- POST /api/v1/sessions/{session_id}/quick-feedback
- POST /api/v1/sessions/{session_id}/deep-analyze
- POST /api/v1/sessions/{session_id}/report
"""
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/transcript", tags=["Transcript"])


@router.post("/elevenlabs-token")
async def generate_elevenlabs_token():
    """Generate a single-use token for ElevenLabs Speech-to-Text WebSocket.

    This endpoint calls ElevenLabs API to generate a temporary token that
    can be used by the iOS app to connect to their WebSocket service.
    This approach keeps the API key secure on the server side.

    Returns:
        Dict with 'token' key containing the single-use token

    Raises:
        HTTPException: If token generation fails
    """
    try:
        # Get API key from environment
        api_key = os.getenv("ELEVEN_LABS_API_KEY")
        if not api_key:
            logger.error("ELEVEN_LABS_API_KEY not found in environment")
            raise HTTPException(
                status_code=500, detail="ElevenLabs API key not configured"
            )

        # Call ElevenLabs API to generate single-use token
        url = "https://api.elevenlabs.io/v1/single-use-token/realtime_scribe"
        headers = {"xi-api-key": api_key}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, timeout=30.0)

            if response.status_code != 200:
                logger.error(
                    f"ElevenLabs API error: {response.status_code} - {response.text}"
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to generate token: {response.text}",
                )

            token_data = response.json()
            logger.info("Successfully generated ElevenLabs token")

            return {"token": token_data.get("token")}

    except httpx.TimeoutException:
        logger.error("Timeout calling ElevenLabs API")
        raise HTTPException(
            status_code=504, detail="Timeout generating token from ElevenLabs"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Token generation failed: {e}")
