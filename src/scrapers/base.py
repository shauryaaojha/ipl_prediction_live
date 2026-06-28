"""Abstract BaseScraper class.

All scraper modules inherit from this base and implement the scrape / parse
interface. Provides common functionality: HTTP fetching, browser fallback,
validation, rate-limiting, and error handling.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from loguru import logger
from pydantic import BaseModel

from ..utils.http_client import HttpClient


class BaseScraper(ABC):
    """Abstract base class for all scraper modules."""

    SOURCE_NAME: str = "base"

    def __init__(self, config: Dict[str, Any], http_client: HttpClient):
        self.config = config
        self.client = http_client
        self.rate_limit_delay = config.get("request_delay", 1.5)
        self.max_retries = config.get("max_retries", 3)

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    async def fetch_json(self, url: str, **kwargs) -> Any:
        """Fetch a URL and parse the response as JSON."""
        logger.debug("[{}] Fetching JSON: {}", self.SOURCE_NAME, url)
        return await self.client.get_json(url, **kwargs)

    async def fetch_html(self, url: str, **kwargs) -> str:
        """Fetch a URL and return HTML text."""
        logger.debug("[{}] Fetching HTML: {}", self.SOURCE_NAME, url)
        return await self.client.get_text(url, **kwargs)

    async def fetch_with_browser(self, url: str) -> str:
        """Use Playwright for JavaScript-rendered pages.

        Falls back to this when API endpoints return 403 or pages require JS.
        """
        logger.info("[{}] Fetching with browser: {}", self.SOURCE_NAME, url)
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )
            raise

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=self.client._build_headers()["User-Agent"]
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=60000)
            content = await page.content()
            await browser.close()
            return content

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        data: List[Dict[str, Any]],
        model_class: Type[BaseModel],
    ) -> List[BaseModel]:
        """Validate parsed data against Pydantic models.

        Items that fail validation are logged and skipped.
        """
        validated = []
        for item in data:
            try:
                validated.append(model_class(**item))
            except Exception as e:
                logger.warning(
                    "[{}] Validation failed: {} | Data: {}",
                    self.SOURCE_NAME, e, str(item)[:200],
                )
        logger.info(
            "[{}] Validated {}/{} records against {}",
            self.SOURCE_NAME, len(validated), len(data), model_class.__name__,
        )
        return validated

    # ------------------------------------------------------------------
    # Core Scraper Methods
    # ------------------------------------------------------------------
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the source is accessible and functioning."""
        ...

    @abstractmethod
    async def scrape_matches(self, season: int, **kwargs) -> List[Dict[str, Any]]:
        """Scrape match results for a given IPL season."""
        ...

    @abstractmethod
    async def scrape_match_detail(self, match_id: str, **kwargs) -> Dict[str, Any]:
        """Scrape detailed data for a single match."""
        ...

    async def scrape_ball_by_ball(self, match_id: str, **kwargs) -> List[Dict[str, Any]]:
        """Scrape ball-by-ball commentary for a match. Optional."""
        logger.warning("[{}] Ball-by-ball scraping not implemented.", self.SOURCE_NAME)
        return []

    async def scrape_player_stats(self, player_id: str, **kwargs) -> Dict[str, Any]:
        """Scrape detailed stats for a player. Optional."""
        logger.warning("[{}] Player stats scraping not implemented.", self.SOURCE_NAME)
        return {}

    async def scrape_playing_xi(self, match_id: str, **kwargs) -> List[Dict[str, Any]]:
        """Scrape playing XI for a match. Optional."""
        logger.warning("[{}] Playing XI scraping not implemented.", self.SOURCE_NAME)
        return []

    async def scrape_venues(self, **kwargs) -> List[Dict[str, Any]]:
        """Scrape venue metadata. Optional."""
        logger.warning("[{}] Venue scraping not implemented.", self.SOURCE_NAME)
        return []

    async def scrape_squads(self, season: int, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape team squads. Optional."""
        logger.warning("[{}] Squad scraping not implemented.", self.SOURCE_NAME)
        return {}
