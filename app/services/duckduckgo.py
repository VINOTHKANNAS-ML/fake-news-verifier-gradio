"""DuckDuckGo search integration (no API key required)."""
from duckduckgo_search import DDGS
from app.config import get_settings

settings = get_settings()


class DuckDuckGoService:
    """Service to search DuckDuckGo (free, no API key)."""

    async def search(self, query: str, max_results: int = 10) -> dict:
        if settings.ENABLE_MOCK_MODE:
            return self._mock_response(query)

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
        except Exception as e:
            return {"result_count": 0, "snippets": [], "error": str(e)}

        snippets = [r["body"] for r in results if r.get("body")]
        sources = [{
            "title": r.get("title", "Unknown"),
            "url": r.get("href"),
            "publisher": "DuckDuckGo Result",
            "textual_rating": "Web Search"
        } for r in results]

        return {
            "result_count": len(results),
            "snippets": snippets,
            "sources": sources
        }

    def _mock_response(self, query: str) -> dict:
        return {
            "result_count": 5,
            "snippets": [f"Mock web search result for: {query[:50]}..."],
            "sources": [
                {
                    "title": f"Search result for {query[:30]}",
                    "url": "https://example.com/search/1",
                    "publisher": "Mock Search",
                    "textual_rating": "Web Search"
                }
            ]
        }
