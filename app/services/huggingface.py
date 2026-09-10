"""HuggingFace Inference API for image analysis."""
import httpx
from app.config import get_settings

settings = get_settings()
API_URL = "https://api-inference.huggingface.co/models"


class HuggingFaceService:
    """Service for HuggingFace Inference API."""

    def __init__(self):
        self.api_key = settings.HUGGINGFACE_API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def image_captioning(self, image_bytes: bytes) -> str:
        if settings.ENABLE_MOCK_MODE or not self.api_key:
            return "Mock image caption: A person speaking at a podium with text overlay."

        model = "Salesforce/blip-image-captioning-base"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_URL}/{model}",
                headers=self.headers,
                data=image_bytes
            )
            response.raise_for_status()
            result = response.json()

        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "")
        return ""

    async def object_detection(self, image_bytes: bytes) -> list:
        if settings.ENABLE_MOCK_MODE or not self.api_key:
            return [{"label": "person", "score": 0.95}, {"label": "text", "score": 0.88}]

        model = "facebook/detr-resnet-50"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_URL}/{model}",
                headers=self.headers,
                data=image_bytes
            )
            response.raise_for_status()
            result = response.json()

        if isinstance(result, list):
            return [{"label": r.get("label"), "score": r.get("score")} for r in result[:10]]
        return []
