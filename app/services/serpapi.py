"""SerpApi integration - used in place of Google's own Fact Check Tools API.

SerpApi (https://serpapi.com) proxies Google's Fact Check Tool results
through the same `claims` / `claimReview` JSON shape Google's own API
returns, so this is a drop-in replacement with the same response
contract as the previous GoogleFactCheckService - just billed through
SerpApi's plans instead of a direct (and now cost-gated) Google Cloud key.

Falls back to SerpApi's general Google Search engine if the fact-check
engine returns nothing, so a claim with no dedicated fact-check article
still surfaces relevant web evidence instead of an empty result.
"""
import httpx
from app.config import get_settings

settings = get_settings()
BASE_URL = "https://serpapi.com/search.json"

FACT_CHECK_DOMAINS = ("snopes.com", "politifact.com", "factcheck.org", "fullfact.org", "leadstories.com")


class SerpApiService:
    """Service to query fact-check style results via SerpApi."""

    def __init__(self):
        self.api_key = settings.SERPAPI_KEY

    async def search_claims(self, query: str) -> dict:
        if settings.ENABLE_MOCK_MODE or not self.api_key:
            return self._mock_response(query)

        async with httpx.AsyncClient(timeout=30.0) as client:
            fact_check_result = await self._search_fact_check_engine(client, query)
            if fact_check_result["claim_count"] > 0:
                return fact_check_result

            # No dedicated fact-check article found - fall back to a
            # regular search scoped to known fact-checking publishers.
            return await self._search_fallback(client, query)

    async def _search_fact_check_engine(self, client: httpx.AsyncClient, query: str) -> dict:
        params = {
            "engine": "google_fact_check",
            "query": query[:500],
            "api_key": self.api_key,
        }
        try:
            response = await client.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return {"claim_count": 0, "sources": []}

        return self._format_factcheck_response(data)

    async def _search_fallback(self, client: httpx.AsyncClient, query: str) -> dict:
        domain_filter = " OR ".join(f"site:{d}" for d in FACT_CHECK_DOMAINS)
        params = {
            "engine": "google",
            "q": f"{query[:300]} ({domain_filter})",
            "api_key": self.api_key,
            "num": 10,
        }
        try:
            response = await client.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError:
            return {"claim_count": 0, "sources": []}

        return self._format_organic_response(data)

    def _format_factcheck_response(self, data: dict) -> dict:
        claims = data.get("claims", [])
        sources = []

        for claim in claims:
            for review in claim.get("claim_review", claim.get("claimReview", [])):
                sources.append({
                    "title": review.get("title", "Unknown"),
                    "url": review.get("url") or review.get("link"),
                    "publisher": review.get("publisher", {}).get("name", "Unknown")
                        if isinstance(review.get("publisher"), dict) else review.get("publisher", "Unknown"),
                    "publish_date": review.get("review_date") or review.get("reviewDate"),
                    "claim_reviewed": claim.get("text", ""),
                    "textual_rating": review.get("textual_rating") or review.get("textualRating", "Unknown"),
                })

        return {"claim_count": len(claims), "sources": sources}

    def _format_organic_response(self, data: dict) -> dict:
        results = data.get("organic_results", [])
        sources = [
            {
                "title": r.get("title", "Unknown"),
                "url": r.get("link"),
                "publisher": r.get("source", "Unknown"),
                "publish_date": r.get("date"),
                "claim_reviewed": "",
                "textual_rating": "Unrated",
            }
            for r in results
        ]
        return {"claim_count": len(sources), "sources": sources}

    def _mock_response(self, query: str) -> dict:
        return {
            "claim_count": 2,
            "sources": [
                {
                    "title": f"Fact Check: Related to '{query[:30]}...'",
                    "url": "https://example.com/factcheck/1",
                    "publisher": "Mock Fact Checker",
                    "publish_date": "2026-01-15",
                    "claim_reviewed": query[:100],
                    "textual_rating": "Mostly True",
                }
            ],
        }
