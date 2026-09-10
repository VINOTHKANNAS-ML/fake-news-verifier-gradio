"""Explanation agent - generates human-readable XAI reports."""
from typing import Any, Dict, List
from app.agents.base import BaseAgent, AgentResult
from app.services.groq_service import GroqService


class ExplanationAgent(BaseAgent):
    """Generates explainable trust assessment reports."""

    def __init__(self):
        super().__init__(
            name="ExplanationAgent",
            description="Generates human-readable explanations for trust scores"
        )
        self.groq = GroqService()

    async def _process(self, context: Dict[str, Any]) -> AgentResult:
        trust_result = context.get("trust_result", {})
        search_result = context.get("search_result", {})
        ingestion_result = context.get("ingestion_result", {})

        trust_data = trust_result.get("data", {})
        factors = trust_data.get("factors", [])
        verdict = trust_data.get("verdict", "unverified")
        trust_score = trust_data.get("trust_score", 0)
        extracted_text = ingestion_result.get("data", {}).get("extracted_text", "")

        verdict_explanations = {
            "true": f"This content appears credible with a trust score of {trust_score}/100.",
            "false": f"This content shows strong indicators of being false (score: {trust_score}/100).",
            "misleading": f"This content may be misleading (score: {trust_score}/100).",
            "unverified": f"Insufficient evidence to verify this claim (score: {trust_score}/100)."
        }

        factor_texts = []
        for factor in factors:
            name = factor["factor"]
            score = factor["score"]
            max_score = factor["max"]
            desc = factor["description"]
            percentage = (score / max_score) * 100 if max_score > 0 else 0

            if percentage >= 70:
                assessment = "strong"
            elif percentage >= 40:
                assessment = "moderate"
            else:
                assessment = "weak"

            factor_texts.append(f"**{name}** ({assessment}): {desc} [Score: {score}/{max_score}]")

        search_data = search_result.get("data", {})
        sources = search_data.get("sources", [])
        source_text = ""
        if sources:
            top_sources = sources[:5]
            source_text = "\n\n**Key Sources:**\n" + "\n".join(
                f"- {s.get('title', 'Unknown')}: {s.get('textual_rating', 'No rating')}"
                for s in top_sources
            )

        recommendations = self._generate_recommendations(verdict, trust_score, factors)
        rec_text = f"\n\n**Recommendations:**\n" + "\n".join(f"- {r}" for r in recommendations)

        full_explanation = verdict_explanations.get(verdict, "") + "\n\n**Factor Breakdown:**\n" + "\n".join(f"- {ft}" for ft in factor_texts) + source_text + rec_text

        ai_summary = await self.groq.generate_summary(
            extracted_text=extracted_text,
            verdict=verdict,
            trust_score=trust_score,
            factors=factors,
        )

        return AgentResult(
            success=True,
            data={
                "summary": verdict_explanations.get(verdict, ""),
                "detailed_explanation": full_explanation,
                "ai_summary": ai_summary,
                "factors": factors,
                "recommendations": recommendations,
                "verdict": verdict,
                "trust_score": trust_score
            },
            metadata={"explanation_length": len(full_explanation), "ai_summary_generated": ai_summary is not None}
        )

    def _generate_recommendations(self, verdict: str, score: float, factors: List[Dict]) -> List[str]:
        recommendations = []

        if verdict == "false":
            recommendations.append("Do not share this content. It contains false information.")
            recommendations.append("Report this content to platform moderators if possible.")
        elif verdict == "misleading":
            recommendations.append("Verify claims from official sources before sharing.")
            recommendations.append("Be aware that headlines may not reflect full context.")
        elif verdict == "unverified":
            recommendations.append("Wait for more sources to verify this claim.")
            recommendations.append("Check reputable news outlets for confirmation.")
        else:
            recommendations.append("This content appears credible, but always verify critical information.")

        source_factor = next((f for f in factors if f["factor"] == "Source Evidence"), None)
        if source_factor and source_factor["score"] < 20:
            recommendations.append("Limited source diversity detected. Cross-check with multiple outlets.")

        return recommendations
