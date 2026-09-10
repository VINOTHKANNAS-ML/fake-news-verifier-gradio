"""Groq integration - fast LLM inference used to turn the raw trust-score
factors into a short, natural-language narrative summary of the
verification (an "AI Analysis" paragraph shown alongside the templated
factor breakdown).

Groq's API is OpenAI-chat-completions-compatible, so this is a plain
httpx POST - no SDK dependency needed. Get a free key (prefixed `gsk_`)
from https://console.groq.com/keys
"""
from typing import Any, Dict, List, Optional
import httpx
from app.config import get_settings

settings = get_settings()
BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are a fact-checking assistant. You are given a piece of content, "
    "a computed trust score, a verdict, and evidence factors from an "
    "automated pipeline. Write a concise, neutral, 2-4 sentence summary "
    "explaining WHY the content received this assessment, in plain "
    "language a general reader can understand. Do not invent facts beyond "
    "what's provided. Do not use markdown formatting. Do not repeat the "
    "numeric score verbatim more than once."
)


class GroqService:
    """Generates a short AI narrative summary of a verification result."""

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model = settings.GROQ_MODEL

    async def generate_summary(
        self,
        extracted_text: str,
        verdict: str,
        trust_score: float,
        factors: List[Dict[str, Any]],
    ) -> Optional[str]:
        if settings.ENABLE_MOCK_MODE or not self.api_key:
            return self._mock_summary(verdict, trust_score)

        factor_lines = "\n".join(
            f"- {f['factor']}: {f['score']}/{f['max']} - {f['description']}"
            for f in factors
        )
        user_prompt = (
            f"Content (truncated): \"{extracted_text[:800]}\"\n\n"
            f"Verdict: {verdict}\n"
            f"Trust score: {trust_score}/100\n\n"
            f"Factors:\n{factor_lines}\n\n"
            "Write the summary now."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 220,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(BASE_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, IndexError):
            # Never let a flaky LLM call break the verification pipeline -
            # the templated explanation still stands on its own without it.
            return None

    def _mock_summary(self, verdict: str, trust_score: float) -> str:
        return (
            f"[Mock AI summary] Based on the available evidence, this content was "
            f"assessed as '{verdict}' with a trust score of {trust_score:.0f}/100. "
            "This is a simulated response because ENABLE_MOCK_MODE is set to true; "
            "set a real GROQ_API_KEY and disable mock mode for a live AI-generated summary."
        )
