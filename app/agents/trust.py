"""Trust scoring agent - calculates final trust score."""
from typing import Any, Dict, List
from app.agents.base import BaseAgent, AgentResult


class TrustScoringAgent(BaseAgent):
    """Calculates comprehensive trust score based on all agent outputs."""

    def __init__(self):
        super().__init__(
            name="TrustScoringAgent",
            description="Calculates trust score using source credibility and evidence strength"
        )

    async def _process(self, context: Dict[str, Any]) -> AgentResult:
        ingestion_result = context.get("ingestion_result", {})
        image_result = context.get("image_result", {})
        audio_result = context.get("audio_result", {})
        search_result = context.get("search_result", {})

        scores = []
        factors = []

        # 1. Source Evidence Score (0-40 points)
        search_data = search_result.get("data", {})
        metrics = search_data.get("metrics", {})
        source_diversity = metrics.get("source_diversity", 0)
        total_sources = metrics.get("total_sources", 0)
        factcheck_hits = metrics.get("factcheck_hits", 0)

        source_score = min(40, (source_diversity * 10) + min(total_sources * 2, 20))
        if factcheck_hits > 0:
            source_score += 10
        source_score = min(40, source_score)

        scores.append(source_score)
        factors.append({
            "factor": "Source Evidence",
            "weight": 0.40,
            "score": source_score,
            "max": 40,
            "description": f"Found {total_sources} sources across {source_diversity} categories. Fact-check hits: {factcheck_hits}"
        })

        # 2. Content Consistency Score (0-25 points)
        claims = ingestion_result.get("data", {}).get("claims", [])
        extracted_text = ingestion_result.get("data", {}).get("extracted_text", "")

        content_score = 15
        if len(claims) >= 1:
            content_score += 5
        if len(extracted_text) > 100:
            content_score += 5
        content_score = min(25, content_score)

        scores.append(content_score)
        factors.append({
            "factor": "Content Consistency",
            "weight": 0.25,
            "score": content_score,
            "max": 25,
            "description": f"Extracted {len(claims)} verifiable claims from {len(extracted_text)} characters"
        })

        # 3. Media Authenticity Score (0-20 points)
        media_score = 10
        image_data = image_result.get("data", {})
        if "image_trust_score" in image_data:
            media_score += (image_data["image_trust_score"] / 100) * 5

        audio_data = audio_result.get("data", {})
        if "audio_trust_score" in audio_data:
            media_score += (audio_data["audio_trust_score"] / 100) * 5

        media_score = min(20, media_score)
        scores.append(media_score)
        factors.append({
            "factor": "Media Authenticity",
            "weight": 0.20,
            "score": media_score,
            "max": 20,
            "description": "Analysis of image/audio for manipulation signals"
        })

        # 4. Fact-Check Alignment Score (0-15 points)
        factcheck_score = 0
        sources = search_data.get("sources", [])

        for source in sources:
            rating = source.get("textual_rating", "").lower()
            if any(word in rating for word in ["true", "correct", "accurate"]):
                factcheck_score += 5
            elif any(word in rating for word in ["false", "fake", "incorrect"]):
                factcheck_score -= 5

        factcheck_score = max(0, min(15, factcheck_score + 7))
        scores.append(factcheck_score)
        factors.append({
            "factor": "Fact-Check Alignment",
            "weight": 0.15,
            "score": factcheck_score,
            "max": 15,
            "description": "Alignment with known fact-check ratings"
        })

        total_score = sum(scores)

        if total_score >= 75:
            verdict = "true"
            confidence = min(1.0, 0.7 + (total_score - 75) / 100)
        elif total_score >= 50:
            verdict = "misleading"
            confidence = 0.6
        elif total_score >= 25:
            verdict = "unverified"
            confidence = 0.5
        else:
            verdict = "false"
            confidence = min(1.0, 0.7 + (25 - total_score) / 50)

        if source_diversity >= 3:
            confidence = min(1.0, confidence + 0.1)

        return AgentResult(
            success=True,
            data={
                "trust_score": round(total_score, 2),
                "verdict": verdict,
                "confidence": round(confidence, 3),
                "factors": factors,
                "max_possible_score": 100
            },
            metadata={"scoring_model": "multi_factor_v1"}
        )
