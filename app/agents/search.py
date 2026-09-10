"""Search and fact-check agent - queries multiple sources."""
from typing import Any, Dict
from app.agents.base import BaseAgent, AgentResult
from app.services.serpapi import SerpApiService
from app.services.newsapi import NewsAPIService
from app.services.duckduckgo import DuckDuckGoService
from app.services.wikipedia import WikipediaService
from app.config import get_settings
import asyncio

settings = get_settings()


class SearchAgent(BaseAgent):
    """Searches for evidence across multiple free sources."""

    def __init__(self):
        super().__init__(
            name="SearchAgent",
            description="Searches SerpApi fact-check results, NewsAPI, DuckDuckGo, and Wikipedia"
        )
        self.factcheck = SerpApiService()
        self.newsapi = NewsAPIService()
        self.ddg = DuckDuckGoService()
        self.wiki = WikipediaService()

    async def _process(self, context: Dict[str, Any]) -> AgentResult:
        claims = context.get("claims", [])
        extracted_text = context.get("extracted_text", "")

        if not claims and not extracted_text:
            return AgentResult(success=True, data={"evidence": [], "sources": []})

        search_query = claims[0] if claims else extracted_text[:200]

        tasks = [
            self._search_factcheck(search_query),
            self._search_news(search_query),
            self._search_web(search_query),
            self._search_wikipedia(search_query)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_evidence = []
        all_sources = []
        factcheck_hits = 0
        news_hits = 0
        web_hits = 0
        wiki_hits = 0

        if isinstance(results[0], dict):
            factcheck_hits = results[0].get("claim_count", 0)
            all_sources.extend(results[0].get("sources", []))

        if isinstance(results[1], dict):
            news_hits = results[1].get("article_count", 0)
            all_sources.extend(results[1].get("sources", []))

        if isinstance(results[2], dict):
            web_hits = results[2].get("result_count", 0)
            all_evidence.extend(results[2].get("snippets", []))

        if isinstance(results[3], dict):
            wiki_hits = 1 if results[3].get("found") else 0
            if wiki_hits:
                all_evidence.append(results[3].get("summary", ""))

        source_diversity = sum([factcheck_hits > 0, news_hits > 0, web_hits > 0, wiki_hits > 0])

        return AgentResult(
            success=True,
            data={
                "evidence": all_evidence,
                "sources": all_sources[:20],
                "metrics": {
                    "factcheck_hits": factcheck_hits,
                    "news_hits": news_hits,
                    "web_hits": web_hits,
                    "wiki_hits": wiki_hits,
                    "source_diversity": source_diversity,
                    "total_sources": len(all_sources)
                },
                "search_query": search_query
            }
        )

    async def _search_factcheck(self, query: str) -> Dict:
        try:
            return await self.factcheck.search_claims(query)
        except Exception as e:
            return {"claim_count": 0, "sources": [], "error": str(e)}

    async def _search_news(self, query: str) -> Dict:
        try:
            return await self.newsapi.search_news(query)
        except Exception as e:
            return {"article_count": 0, "sources": [], "error": str(e)}

    async def _search_web(self, query: str) -> Dict:
        try:
            return await self.ddg.search(query)
        except Exception as e:
            return {"result_count": 0, "snippets": [], "error": str(e)}

    async def _search_wikipedia(self, query: str) -> Dict:
        try:
            return await self.wiki.search(query)
        except Exception as e:
            return {"found": False, "error": str(e)}
