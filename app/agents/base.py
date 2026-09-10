"""Base agent class for the multi-agent system."""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentResult:
    """Standard result format for all agents."""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: int = 0


class BaseAgent(ABC):
    """Abstract base class for all verification agents."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.status = "idle"
        self.last_result: Optional[AgentResult] = None

    async def execute(self, context: Dict[str, Any]) -> AgentResult:
        """Execute agent with timing and error handling."""
        self.status = "running"
        start_time = datetime.utcnow()

        try:
            result = await self._process(context)
            self.status = "completed"
        except Exception as e:
            self.status = "failed"
            result = AgentResult(
                success=False,
                error=str(e),
                metadata={"agent": self.name, "exception_type": type(e).__name__}
            )

        end_time = datetime.utcnow()
        processing_time = int((end_time - start_time).total_seconds() * 1000)
        result.processing_time_ms = processing_time
        result.metadata.update({
            "agent_name": self.name,
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat()
        })

        self.last_result = result
        return result

    @abstractmethod
    async def _process(self, context: Dict[str, Any]) -> AgentResult:
        pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "last_result": self.last_result
        }
