"""URL article extraction service - fetches a web page and extracts the
main article text, title, author, and publish date so a news article URL
can be dropped straight into the verification pipeline like plain text.

Implemented with requests + BeautifulSoup (no heavy NLP deps) so it stays
fast and reliable across arbitrary news sites without requiring NLTK
corpora downloads.
"""
from typing import Any, Dict, Optional
import re
import httpx
from bs4 import BeautifulSoup
from app.config import get_settings

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 FakeNewsVerifierBot/1.0"
)

# Tags that never contain article body copy - stripped before extraction.
NOISE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "iframe"]


class URLExtractionError(Exception):
    """Raised when a URL cannot be fetched or no article content is found."""


class URLExtractorService:
    """Fetches a URL and pulls out readable article content."""

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self.settings = get_settings()

    async def extract(self, url: str) -> Dict[str, Any]:
        if not re.match(r"^https?://", url.strip(), re.IGNORECASE):
            raise URLExtractionError("URL must start with http:// or https://")

        if self.settings.ENABLE_MOCK_MODE:
            return self._mock_response(url.strip())

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPError as e:
            raise URLExtractionError(f"Could not fetch URL: {e}") from e

        content_type = response.headers.get("content-type", "")
        if "html" not in content_type and content_type:
            raise URLExtractionError(f"URL does not point to an HTML page ({content_type})")

        soup = BeautifulSoup(response.text, "html.parser")

        for tag_name in NOISE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        title = self._extract_title(soup)
        author = self._extract_author(soup)
        publish_date = self._extract_publish_date(soup)
        top_image = self._extract_top_image(soup, str(response.url))
        body_text = self._extract_body_text(soup)

        if not body_text or len(body_text) < 80:
            raise URLExtractionError(
                "Could not find enough readable article text on this page"
            )

        return {
            "title": title,
            "text": body_text,
            "author": author,
            "publish_date": publish_date,
            "top_image": top_image,
            "source_url": str(response.url),
            "domain": self._domain(str(response.url)),
        }

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        return None

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            return meta_author["content"].strip()
        article_author = soup.find(attrs={"class": re.compile(r"author", re.I)})
        if article_author:
            text = article_author.get_text(strip=True)
            if 0 < len(text) < 100:
                return text
        return None

    def _extract_publish_date(self, soup: BeautifulSoup) -> Optional[str]:
        for prop in ("article:published_time", "og:published_time", "datePublished"):
            meta = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if meta and meta.get("content"):
                return meta["content"].strip()
        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            return time_tag["datetime"].strip()
        return None

    def _extract_top_image(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            return og_image["content"].strip()
        return None

    def _extract_body_text(self, soup: BeautifulSoup) -> str:
        """Pick the container with the most paragraph text - a cheap but
        effective readability heuristic that works across most news sites
        without per-domain scraping rules."""
        candidates = soup.find_all(["article", "main", "div", "section"])
        best_text = ""
        best_len = 0

        for candidate in candidates:
            paragraphs = candidate.find_all("p", recursive=True)
            text = " ".join(
                p.get_text(" ", strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 30
            )
            if len(text) > best_len:
                best_len = len(text)
                best_text = text

        if not best_text:
            # Fallback: every <p> on the page
            paragraphs = soup.find_all("p")
            best_text = " ".join(
                p.get_text(" ", strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20
            )

        best_text = re.sub(r"\s+", " ", best_text).strip()
        # Cap length to keep downstream agents/APIs fast and within limits.
        return best_text[:8000]

    def _domain(self, url: str) -> str:
        match = re.match(r"^https?://([^/]+)", url)
        return match.group(1) if match else url

    def _mock_response(self, url: str) -> Dict[str, Any]:
        """Realistic canned response used when ENABLE_MOCK_MODE=true, so
        the URL tab works fully offline for demos - consistent with how
        the other external-API services behave in mock mode."""
        domain = self._domain(url)
        return {
            "title": "Mock Headline: Local Officials Announce New Infrastructure Plan",
            "text": (
                "This is a mock article body generated because ENABLE_MOCK_MODE is set to true. "
                "In a real run, this text would be the actual extracted content from the "
                f"article at {url}. The mock article discusses a fictional infrastructure "
                "announcement, including quotes from officials and details about funding "
                "timelines, to give the verification pipeline realistic-looking text to score."
            ),
            "author": "Mock Newsroom Staff",
            "publish_date": "2026-01-15T09:00:00Z",
            "top_image": None,
            "source_url": url,
            "domain": domain,
        }
