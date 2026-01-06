"""Speech-to-Text Service using OpenAI Whisper API"""

import os

from openai import AsyncOpenAI

from app.core.config import settings


class STTService:
    """OpenAI Whisper Speech-to-Text Service"""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "whisper-1"

    async def transcribe_audio(
        self,
        audio_file_path: str,
        language: str = "zh",
        response_format: str = "text",
    ) -> str:
        """
        Transcribe audio file to text using OpenAI Whisper

        Args:
            audio_file_path: Path to audio file (mp3, mp4, mpeg, mpga, m4a, wav, webm)
            language: Language code (default: zh for Chinese)
            response_format: Response format (text, json, srt, verbose_json, vtt)

        Returns:
            Transcribed text
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        with open(audio_file_path, "rb") as audio_file:
            response = await self.client.audio.transcriptions.create(  # type: ignore[call-overload]
                model=self.model,
                file=audio_file,
                language=language,
                response_format=response_format,
            )

        if response_format == "text":
            return response
        else:
            return response.text

    async def transcribe_with_timestamps(
        self, audio_file_path: str, language: str = "zh"
    ) -> dict:
        """
        Transcribe audio with word-level timestamps

        Returns:
            {
                "text": "full transcript",
                "segments": [{"start": 0.0, "end": 1.5, "text": "..."}],
                "language": "zh"
            }
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        with open(audio_file_path, "rb") as audio_file:
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

        return {
            "text": response.text,
            "segments": [
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                }
                for segment in (response.segments or [])
            ],
            "language": response.language,
            "duration": response.duration,
        }


# Service instance
stt_service = STTService()
