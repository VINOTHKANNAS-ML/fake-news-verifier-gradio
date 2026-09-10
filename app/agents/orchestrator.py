"""Multi-agent orchestrator - coordinates all agents."""
from typing import Any, Dict, List
from datetime import datetime
import asyncio

from app.agents.ingestion import IngestionAgent
from app.agents.image import ImageAnalysisAgent
from app.agents.audio import AudioAnalysisAgent
from app.agents.search import SearchAgent
from app.agents.trust import TrustScoringAgent
from app.agents.explanation import ExplanationAgent
from app.agents.base import AgentResult


class VerificationOrchestrator:
    """Orchestrates the multi-agent verification pipeline."""

    def __init__(self):
        self.ingestion_agent = IngestionAgent()
        self.image_agent = ImageAnalysisAgent()
        self.audio_agent = AudioAnalysisAgent()
        self.search_agent = SearchAgent()
        self.trust_agent = TrustScoringAgent()
        self.explanation_agent = ExplanationAgent()
        self.agent_logs: List[Dict[str, Any]] = []

    async def verify(self, input_type: str, content: str = None, file_data: Any = None) -> Dict[str, Any]:
        start_time = datetime.utcnow()
        self.agent_logs = []

        ingestion_context = {
            "input_type": input_type,
            "content": content,
            "file_data": file_data
        }
        ingestion_result = await self._run_agent(self.ingestion_agent, ingestion_context)

        extracted_text = ingestion_result.data.get("extracted_text", "")
        claims = ingestion_result.data.get("claims", [])

        media_tasks = []
        media_context = {"file_data": file_data, "extracted_text": extracted_text}

        if input_type == "image":
            media_tasks.append(self._run_agent(self.image_agent, media_context))
        elif input_type == "audio":
            media_tasks.append(self._run_agent(self.audio_agent, media_context))

        media_results = await asyncio.gather(*media_tasks, return_exceptions=True) if media_tasks else []

        image_result = {}
        audio_result = {}
        for result in media_results:
            if isinstance(result, AgentResult):
                if result.metadata.get("agent_name") == "ImageAnalysisAgent":
                    image_result = {"success": result.success, "data": result.data, "metadata": result.metadata}
                elif result.metadata.get("agent_name") == "AudioAnalysisAgent":
                    audio_result = {"success": result.success, "data": result.data, "metadata": result.metadata}

        search_context = {"claims": claims, "extracted_text": extracted_text}
        search_result = await self._run_agent(self.search_agent, search_context)

        trust_context = {
            "ingestion_result": {"data": ingestion_result.data, "metadata": ingestion_result.metadata},
            "image_result": image_result,
            "audio_result": audio_result,
            "search_result": {"data": search_result.data, "metadata": search_result.metadata}
        }
        trust_result = await self._run_agent(self.trust_agent, trust_context)

        explanation_context = {
            "trust_result": {"data": trust_result.data, "metadata": trust_result.metadata},
            "search_result": {"data": search_result.data, "metadata": search_result.metadata},
            "ingestion_result": {"data": ingestion_result.data, "metadata": ingestion_result.metadata}
        }
        explanation_result = await self._run_agent(self.explanation_agent, explanation_context)

        end_time = datetime.utcnow()
        total_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return {
            "trust_score": trust_result.data.get("trust_score"),
            "verdict": trust_result.data.get("verdict"),
            "confidence": trust_result.data.get("confidence"),
            "explanation": explanation_result.data.get("factors", []),
            "detailed_explanation": explanation_result.data.get("detailed_explanation"),
            "ai_summary": explanation_result.data.get("ai_summary"),
            "sources": search_result.data.get("sources", []),
            "recommendations": explanation_result.data.get("recommendations", []),
            "extracted_text": extracted_text,
            "processing_time_ms": total_time_ms,
            "agent_logs": self.agent_logs
        }

    async def _run_agent(self, agent, context: Dict) -> AgentResult:
        result = await agent.execute(context)
        self.agent_logs.append({
            "agent_name": agent.name,
            "status": "completed" if result.success else "failed",
            "input_data": context,
            "output_data": result.data if result.success else None,
            "error_message": result.error if not result.success else None,
            "processing_time_ms": result.processing_time_ms
        })
        return result
