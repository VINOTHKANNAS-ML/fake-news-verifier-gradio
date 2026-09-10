"""Mock data generators for demo mode."""
from typing import Dict, Any, List
import random


def generate_mock_verification(input_type: str, content: str) -> Dict[str, Any]:
    """Generate mock verification result for demo purposes."""
    trust_score = random.uniform(20, 95)

    if trust_score >= 75:
        verdict = "true"
    elif trust_score >= 50:
        verdict = "misleading"
    elif trust_score >= 25:
        verdict = "unverified"
    else:
        verdict = "false"

    return {
        "trust_score": round(trust_score, 2),
        "verdict": verdict,
        "confidence": round(random.uniform(0.5, 0.95), 3),
        "explanation": [
            {
                "factor": "Source Evidence",
                "weight": 0.40,
                "score": round(random.uniform(10, 40), 2),
                "description": "Mock source evidence analysis"
            },
            {
                "factor": "Content Consistency",
                "weight": 0.25,
                "score": round(random.uniform(5, 25), 2),
                "description": "Mock content consistency analysis"
            },
            {
                "factor": "Media Authenticity",
                "weight": 0.20,
                "score": round(random.uniform(5, 20), 2),
                "description": "Mock media authenticity analysis"
            },
            {
                "factor": "Fact-Check Alignment",
                "weight": 0.15,
                "score": round(random.uniform(2, 15), 2),
                "description": "Mock fact-check alignment analysis"
            }
        ],
        "sources": [
            {
                "title": "Mock Fact Check Source 1",
                "url": "https://example.com/1",
                "publisher": "Mock Publisher",
                "textual_rating": "Mostly True"
            },
            {
                "title": "Mock News Source 1",
                "url": "https://example.com/2",
                "publisher": "Mock News",
                "textual_rating": "News Article"
            }
        ],
        "recommendations": [
            "Verify claims from official sources before sharing.",
            "Cross-check with multiple outlets."
        ],
        "extracted_text": content or "Mock extracted text from upload.",
        "processing_time_ms": random.randint(500, 3000),
        "agent_logs": []
    }
