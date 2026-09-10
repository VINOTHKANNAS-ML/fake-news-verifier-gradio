"""Wikipedia API integration (no API key required)."""
import wikipedia
from app.config import get_settings

settings = get_settings()


class WikipediaService:
    """Service to search Wikipedia for verification."""

    def __init__(self):
        wikipedia.set_lang("en")

    async def search(self, query: str) -> dict:
        if settings.ENABLE_MOCK_MODE:
            return self._mock_response(query)

        try:
            search_results = wikipedia.search(query, results=3)
            if not search_results:
                return {"found": False, "summary": ""}

            page = wikipedia.page(search_results[0], auto_suggest=False)
            summary = wikipedia.summary(search_results[0], sentences=3, auto_suggest=False)

            return {
                "found": True,
                "title": page.title,
                "summary": summary,
                "url": page.url,
                "sources": [{
                    "title": page.title,
                    "url": page.url,
                    "publisher": "Wikipedia",
                    "textual_rating": "Encyclopedia"
                }]
            }
        except wikipedia.exceptions.DisambiguationError as e:
            return {"found": True, "disambiguation": True, "options": e.options[:5]}
        except wikipedia.exceptions.PageError:
            return {"found": False, "summary": ""}
        except Exception as e:
            return {"found": False, "error": str(e)}

    def _mock_response(self, query: str) -> dict:
        return {
            "found": True,
            "title": f"Mock Wikipedia: {query[:30]}",
            "summary": f"Mock Wikipedia summary for {query[:50]}...",
            "url": "https://en.wikipedia.org/wiki/Mock",
            "sources": [{
                "title": "Mock Wikipedia",
                "url": "https://en.wikipedia.org/wiki/Mock",
                "publisher": "Wikipedia",
                "textual_rating": "Encyclopedia"
            }]
        }
