"""NewsAPI integration for news verification."""
import httpx
from datetime import datetime, timedelta
from app.config import get_settings

settings = get_settings()
BASE_URL = "https://newsapi.org/v2"


class NewsAPIService:
    """Service to search news articles."""

    def __init__(self):
        self.api_key = settings.NEWSAPI_KEY

    async def search_news(self, query: str, days_back: int = 30) -> dict:
        if settings.ENABLE_MOCK_MODE or not self.api_key:
            return self._mock_response(query)

        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

        params = {
            "q": query[:500],
            "from": from_date,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": 10,
            "apiKey": self.api_key
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BASE_URL}/everything", params=params)
            response.raise_for_status()
            data = response.json()

        return self._format_response(data)

    def _format_response(self, data: dict) -> dict:
        articles = data.get("articles", [])
        sources = []

        for article in articles:
            sources.append({
                "title": article.get("title", "Unknown"),
                "url": article.get("url"),
                "publisher": article.get("source", {}).get("name", "Unknown"),
                "publish_date": article.get("publishedAt"),
                "claim_reviewed": article.get("description", ""),
                "textual_rating": "News Article"
            })

        return {"article_count": len(articles), "sources": sources}

    def _mock_response(self, query: str) -> dict:
        return {
            "article_count": 3,
            "sources": [
                {
                    "title": f"News about: {query[:30]}...",
                    "url": "https://example.com/news/1",
                    "publisher": "Mock News Source",
                    "publish_date": "2024-01-10T12:00:00Z",
                    "claim_reviewed": query[:100],
                    "textual_rating": "News Article"
                }
            ]
        }
