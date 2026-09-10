"""AssemblyAI integration for speech-to-text."""
import httpx
import time
from app.config import get_settings

settings = get_settings()
BASE_URL = "https://api.assemblyai.com/v2"


class AssemblyAIService:
    """Service for AssemblyAI speech-to-text."""

    def __init__(self):
        self.api_key = settings.ASSEMBLYAI_API_KEY
        self.headers = {"authorization": self.api_key} if self.api_key else {}

    async def transcribe(self, audio_bytes: bytes) -> str:
        result = await self.transcribe_detailed(audio_bytes)
        return result.get("text", "")

    async def transcribe_detailed(self, audio_bytes: bytes) -> dict:
        if settings.ENABLE_MOCK_MODE or not self.api_key:
            return self._mock_response()

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Upload audio
            upload_response = await client.post(
                f"{BASE_URL}/upload",
                headers=self.headers,
                content=audio_bytes
            )
            upload_response.raise_for_status()
            upload_url = upload_response.json()["upload_url"]

            # Submit transcription
            transcript_response = await client.post(
                f"{BASE_URL}/transcript",
                headers={**self.headers, "content-type": "application/json"},
                json={"audio_url": upload_url}
            )
            transcript_response.raise_for_status()
            transcript_id = transcript_response.json()["id"]

            # Poll for completion
            while True:
                polling_response = await client.get(
                    f"{BASE_URL}/transcript/{transcript_id}",
                    headers=self.headers
                )
                polling_response.raise_for_status()
                polling_result = polling_response.json()

                if polling_result["status"] == "completed":
                    return {
                        "text": polling_result.get("text", ""),
                        "confidence": polling_result.get("confidence", 0.0),
                        "words": polling_result.get("words", []),
                        "language_code": polling_result.get("language_code", "en"),
                        "audio_duration": polling_result.get("audio_duration", 0)
                    }
                elif polling_result["status"] == "error":
                    raise Exception(f"Transcription failed: {polling_result.get('error')}")

                time.sleep(3)

    def _mock_response(self) -> dict:
        return {
            "text": "This is a mock transcription of the uploaded audio file.",
            "confidence": 0.92,
            "words": [{"text": "mock", "confidence": 0.92}],
            "language_code": "en",
            "audio_duration": 15.5
        }
