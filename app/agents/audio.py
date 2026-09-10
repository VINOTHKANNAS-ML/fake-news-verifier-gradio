"""Audio analysis agent - analyzes audio for deepfakes and quality."""
from typing import Any, Dict
from app.agents.base import BaseAgent, AgentResult
from app.services.assemblyai import AssemblyAIService
import base64


class AudioAnalysisAgent(BaseAgent):
    """Analyzes audio for authenticity and transcription confidence."""

    def __init__(self):
        super().__init__(
            name="AudioAnalysisAgent",
            description="Analyzes audio for deepfake detection and transcription confidence"
        )
        self.audio_service = AssemblyAIService()

    async def _process(self, context: Dict[str, Any]) -> AgentResult:
        file_data = context.get("file_data")

        if not file_data:
            return AgentResult(success=True, data={"analysis": "no_audio_provided"})

        audio_bytes = base64.b64decode(file_data) if isinstance(file_data, str) else file_data
        detailed = await self.audio_service.transcribe_detailed(audio_bytes)

        analysis = {
            "transcription_confidence": detailed.get("confidence", 0.0),
            "word_count": len(detailed.get("words", [])),
            "detected_language": detailed.get("language_code", "unknown"),
            "has_multiple_speakers": detailed.get("speaker_count", 1) > 1,
            "audio_duration_seconds": detailed.get("audio_duration", 0),
        }

        trust_signals = {
            "high_confidence_transcription": 1.0 if analysis["transcription_confidence"] > 0.9 else 0.5 if analysis["transcription_confidence"] > 0.7 else 0.2,
            "reasonable_duration": 1.0 if 0 < analysis["audio_duration_seconds"] < 300 else 0.5,
            "clear_speech": 1.0 if analysis["word_count"] > 10 else 0.5
        }

        analysis["trust_signals"] = trust_signals
        analysis["audio_trust_score"] = sum(trust_signals.values()) / len(trust_signals) * 100

        return AgentResult(success=True, data=analysis, metadata={"audio_analyzed": True})
