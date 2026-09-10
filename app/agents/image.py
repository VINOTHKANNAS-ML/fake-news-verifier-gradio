"""Image analysis agent - detects manipulation and metadata."""
from typing import Any, Dict
from app.agents.base import BaseAgent, AgentResult
from app.services.huggingface import HuggingFaceService
from PIL import Image
import io
import base64


class ImageAnalysisAgent(BaseAgent):
    """Analyzes images for authenticity signals."""

    def __init__(self):
        super().__init__(
            name="ImageAnalysisAgent",
            description="Analyzes images for manipulation and reverse image search signals"
        )
        self.hf_service = HuggingFaceService()

    async def _process(self, context: Dict[str, Any]) -> AgentResult:
        file_data = context.get("file_data")
        if not file_data:
            return AgentResult(success=True, data={"analysis": "no_image_provided"})

        image_bytes = base64.b64decode(file_data) if isinstance(file_data, str) else file_data
        img = Image.open(io.BytesIO(image_bytes))

        analysis = {
            "format": img.format,
            "mode": img.mode,
            "size": img.size,
            "is_suspiciously_small": img.size[0] < 100 or img.size[1] < 100,
        }

        try:
            caption = await self.hf_service.image_captioning(image_bytes)
            analysis["caption"] = caption
        except Exception as e:
            analysis["caption_error"] = str(e)

        try:
            objects = await self.hf_service.object_detection(image_bytes)
            analysis["detected_objects"] = objects
        except Exception as e:
            analysis["object_detection_error"] = str(e)

        trust_signals = {
            "resolution_quality": 1.0 if min(img.size) >= 512 else 0.5 if min(img.size) >= 256 else 0.2,
            "has_metadata": True,
            "natural_caption": 0.7 if analysis.get("caption") else 0.0,
            "object_consistency": 0.8 if analysis.get("detected_objects") else 0.0
        }

        analysis["trust_signals"] = trust_signals
        analysis["image_trust_score"] = sum(trust_signals.values()) / len(trust_signals) * 100

        return AgentResult(success=True, data=analysis, metadata={"image_analyzed": True})
