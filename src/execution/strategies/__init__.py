"""
Crawling Strategies.

Different approaches for fetching web content:
- HttpStrategy: Simple HTTP requests (fastest)
- BrowserStrategy: Playwright/browser automation (for JS-heavy sites)
- ApiStrategy: Direct API calls if discoverable
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class FetchResult:
    """Result of fetching a page."""
    url: str
    success: bool
    html: Optional[str] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    links: Optional[List[str]] = None


class BaseStrategy(ABC):
    """Base class for crawling strategies."""

    @abstractmethod
    async def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch a single page."""

    @abstractmethod
    async def extract(self, html: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract data using selectors."""


class HttpStrategy(BaseStrategy):
    """
    HTTP-based crawling strategy.

    Best for:
    - Static content sites
    - Simple HTML pages
    - Sites without heavy JavaScript
    """

    def __init__(self):
        import httpx
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch page using HTTP GET."""
        try:
            response = await self.client.get(url, **kwargs)
            return FetchResult(
                url=url,
                success=response.status_code == 200,
                html=response.text,
                status_code=response.status_code,
                links=self._extract_links(response.text)
            )
        except Exception as e:
            return FetchResult(
                url=url,
                success=False,
                error=str(e)
            )

    async def extract(self, html: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract data using CSS selectors."""
        from lxml import html as lxml_html
        from lxml.cssselect import CSSSelector

        doc = lxml_html.fromstring(html)
        result = {}

        for field, selector in selectors.items():
            try:
                sel = CSSSelector(selector)
                elements = sel(doc)
                if elements:
                    result[field] = elements[0].text_content().strip()
            except Exception:
                result[field] = None

        return result

    def _extract_links(self, html: str) -> List[str]:
        """Extract all links from HTML."""
        from lxml import html as lxml_html
        from urllib.parse import urljoin

        doc = lxml_html.fromstring(html)
        links = []
        for a in doc.cssselect("a[href]"):
            href = a.get("href")
            if href:
                links.append(href)
        return links


class BrowserStrategy(BaseStrategy):
    """
    Browser-based crawling strategy.

    Best for:
    - JavaScript-heavy sites
    - Sites with anti-bot measures
    - Sites requiring interaction
    """

    def __init__(self):
        # Lazy import to avoid requiring playwright
        self.browser = None

    async def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch page using browser automation."""
        try:
            from playwright.async_api import async_playwright

            if self.browser is None:
                playwright = await async_playwright().start()
                self.browser = await playwright.chromium.launch()

            page = await self.browser.new_page()
            await page.goto(url, wait_until="networkidle")

            html = await page.content()
            links = await page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.href)")

            await page.close()

            return FetchResult(
                url=url,
                success=True,
                html=html,
                status_code=200,
                links=links or []
            )
        except Exception as e:
            return FetchResult(
                url=url,
                success=False,
                error=str(e)
            )

    async def extract(self, html: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Extract data using CSS selectors."""
        # Can reuse HTTP strategy extraction
        return HttpStrategy().extract(html, selectors)

    async def close(self) -> None:
        """Close browser."""
        if self.browser:
            await self.browser.close()


class ApiStrategy(BaseStrategy):
    """
    API-based crawling strategy.

    Best for:
    - Sites with discoverable APIs
    - Sites with structured data endpoints
    - High-volume data extraction
    """

    async def fetch(self, url: str, **kwargs) -> FetchResult:
        """Fetch data via API."""
        # TODO: Implement API discovery and calling
        return FetchResult(
            url=url,
            success=False,
            error="API strategy not yet implemented"
        )

    async def extract(self, html: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """Parse API response (typically JSON, not HTML)."""
        import json
        try:
            data = json.loads(html)
            return data
        except Exception:
            return {}
