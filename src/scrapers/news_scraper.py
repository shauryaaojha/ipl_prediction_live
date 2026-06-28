"""News scraper for injury and availability updates.

Monitors cricket news sites for IPL injury updates and squad changes.
Uses regex-based NLP to extract player names, injury types, and dates.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper
from ..storage.json_warehouse import JsonWarehouse


# Injury-related keywords for filtering
INJURY_KEYWORDS = [
    "injury", "injured", "ruled out", "replaced by", "replacement",
    "withdrawn", "unavailable", "sidelined", "hamstring", "shoulder",
    "knee", "back", "groin", "calf", "ankle", "concussion", "fracture",
    "surgery", "rehabilitation", "fitness", "recovery", "pull out",
    "miss", "absent", "doubtful", "strain", "tear", "sprain",
    "impact player", "squad change", "released", "traded",
]


class NewsScraper(BaseScraper):
    """Scrapes news sites for IPL injury and availability updates."""

    SOURCE_NAME = "news"

    def __init__(self, config, http_client):
        super().__init__(config, http_client)
        self.warehouse = JsonWarehouse()

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # ESPN News
    # ------------------------------------------------------------------

    async def scrape_espn_news(self) -> List[Dict[str, Any]]:
        """Scrape IPL-related news from ESPNcricinfo."""
        url = "https://www.espncricinfo.com/indian-premier-league-2025/news"
        logger.info("[News] Scraping ESPN news")

        try:
            html = await self.fetch_html(url)
        except Exception as e:
            logger.error("[News] Failed to fetch ESPN news: {}", e)
            return []

        return self._parse_espn_news(html)

    def _parse_espn_news(self, html: str) -> List[Dict[str, Any]]:
        """Parse ESPN news listing page."""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        story_cards = soup.select("a.story-card, div.story-list-item, article")
        for card in story_cards:
            title_el = card.select_one("h3, h2, .story-title, .headline")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)

            # Filter: only keep injury-related articles
            if not any(kw in title.lower() for kw in INJURY_KEYWORDS):
                continue

            link = card.get("href") or (card.select_one("a") or {}).get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.espncricinfo.com{link}"

            articles.append({
                "title": title,
                "url": link,
                "source": "espncricinfo",
            })

        return articles

    # ------------------------------------------------------------------
    # Cricbuzz News
    # ------------------------------------------------------------------

    async def scrape_cricbuzz_news(self) -> List[Dict[str, Any]]:
        """Scrape IPL-related news from Cricbuzz."""
        url = "https://www.cricbuzz.com/cricket-news/ipl"
        logger.info("[News] Scraping Cricbuzz news")

        try:
            html = await self.fetch_html(url)
        except Exception as e:
            logger.error("[News] Failed to fetch Cricbuzz news: {}", e)
            return []

        return self._parse_cricbuzz_news(html)

    def _parse_cricbuzz_news(self, html: str) -> List[Dict[str, Any]]:
        """Parse Cricbuzz news listing page."""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        news_items = soup.select("a.cb-nws-hdln-ancr, div.cb-lst-itm")
        for item in news_items:
            title_el = item.select_one("h3, h2") or item
            title = title_el.get_text(strip=True)

            if not any(kw in title.lower() for kw in INJURY_KEYWORDS):
                continue

            link = item.get("href", "")
            if link and not link.startswith("http"):
                link = f"https://www.cricbuzz.com{link}"

            articles.append({
                "title": title,
                "url": link,
                "source": "cricbuzz",
            })

        return articles

    # ------------------------------------------------------------------
    # IPLT20 News
    # ------------------------------------------------------------------

    async def scrape_iplt20_news(self) -> List[Dict[str, Any]]:
        """Scrape IPL-related news from IPLT20.com."""
        url = "https://www.iplt20.com/news"
        logger.info("[News] Scraping IPLT20 news")

        try:
            html = await self.fetch_html(url)
        except Exception as e:
            try:
                html = await self.fetch_with_browser(url)
            except Exception:
                return []

        return self._parse_iplt20_news(html)

    def _parse_iplt20_news(self, html: str) -> List[Dict[str, Any]]:
        """Parse IPLT20 news page."""
        soup = BeautifulSoup(html, "lxml")
        articles = []

        news_cards = soup.select("div.news-card, article, div.news-item")
        for card in news_cards:
            title_el = card.select_one("h3, h4, a.title")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if not any(kw in title.lower() for kw in INJURY_KEYWORDS):
                continue

            link = card.select_one("a")
            url = link.get("href", "") if link else ""
            if url and not url.startswith("http"):
                url = f"https://www.iplt20.com{url}"

            articles.append({
                "title": title,
                "url": url,
                "source": "iplt20",
            })

        return articles

    # ------------------------------------------------------------------
    # Article Deep-Scrape
    # ------------------------------------------------------------------

    async def scrape_article_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape the full text of a news article."""
        try:
            html = await self.fetch_html(url)
        except Exception:
            return None

        soup = BeautifulSoup(html, "lxml")

        # Extract article body
        article_body = (
            soup.select_one("article, div.story-content, div.article-body, div.cb-nws-dtl") or soup.body
        )
        text = article_body.get_text(separator="\n", strip=True) if article_body else ""

        # Extract title
        title = soup.select_one("h1, h2.article-title")
        title_text = title.get_text(strip=True) if title else ""

        # Run NLP extraction
        entities = extract_injury_entities(text)

        # Store in warehouse
        self.warehouse.store_news_article(
            url=url,
            title=title_text,
            content_text=text[:5000],  # Limit stored text
            nlp_entities=entities,
        )

        return {
            "url": url,
            "title": title_text,
            "content": text[:2000],
            "entities": entities,
        }

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    async def scrape_all_news(self) -> List[Dict[str, Any]]:
        """Scrape news from all sources and extract injury entities."""
        all_articles = []

        espn = await self.scrape_espn_news()
        all_articles.extend(espn)

        cricbuzz = await self.scrape_cricbuzz_news()
        all_articles.extend(cricbuzz)

        iplt20 = await self.scrape_iplt20_news()
        all_articles.extend(iplt20)

        logger.info("[News] Found {} injury-related articles across all sources", len(all_articles))

        # Deep scrape each article
        results = []
        for article in all_articles[:20]:  # Limit to avoid overloading
            detail = await self.scrape_article_content(article["url"])
            if detail:
                results.append(detail)

        return results

    # Unused abstract methods
    async def scrape_matches(self, season, **kwargs):
        return []

    async def scrape_match_detail(self, match_id, **kwargs):
        return {}


# ===========================================================================
# NLP Entity Extraction (regex-based)
# ===========================================================================

# IPL team names for extraction
_IPL_TEAMS = [
    "Chennai Super Kings", "CSK",
    "Mumbai Indians", "MI",
    "Royal Challengers Bengaluru", "Royal Challengers Bangalore", "RCB",
    "Kolkata Knight Riders", "KKR",
    "Sunrisers Hyderabad", "SRH",
    "Delhi Capitals", "DC",
    "Rajasthan Royals", "RR",
    "Punjab Kings", "PBKS",
    "Gujarat Titans", "GT",
    "Lucknow Super Giants", "LSG",
]

_INJURY_TYPES = [
    "hamstring", "shoulder", "knee", "back", "groin", "calf", "ankle",
    "concussion", "fracture", "finger", "thumb", "elbow", "hip",
    "quadriceps", "abdominal", "side strain", "stress fracture",
    "tendon", "ligament", "ACL", "MCL", "muscle", "sprain", "strain",
]


def extract_injury_entities(text: str) -> Dict[str, Any]:
    """Extract injury-related entities from article text using regex.

    Returns dict with:
    - players: list of player names mentioned
    - injury_types: list of injury types found
    - teams: list of teams mentioned
    - dates: list of date strings found
    - status: inferred availability status
    - confidence: extraction confidence (0-1)
    """
    text_lower = text.lower()
    entities: Dict[str, Any] = {
        "players": [],
        "injury_types": [],
        "teams": [],
        "dates": [],
        "status": None,
        "confidence": 0.0,
    }

    # Extract teams
    for team in _IPL_TEAMS:
        if team.lower() in text_lower or team in text:
            if team not in entities["teams"]:
                entities["teams"].append(team)

    # Extract injury types
    for injury in _INJURY_TYPES:
        if injury.lower() in text_lower:
            entities["injury_types"].append(injury)

    # Extract dates (various formats)
    date_patterns = [
        r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        r"\d{4}-\d{2}-\d{2}",
        r"\d{1,2}/\d{1,2}/\d{4}",
    ]
    for pattern in date_patterns:
        found = re.findall(pattern, text, re.I)
        entities["dates"].extend(found)

    # Infer status
    if re.search(r"ruled\s+out|sidelined|miss(?:es|ing)|withdrawn", text_lower):
        entities["status"] = "injured"
    elif re.search(r"return|recover|fit|available|back\s+in", text_lower):
        entities["status"] = "available"
    elif re.search(r"suspend|ban", text_lower):
        entities["status"] = "suspended"
    elif re.search(r"replace|traded|released", text_lower):
        entities["status"] = "unavailable"

    # Calculate confidence
    signals = sum([
        len(entities["injury_types"]) > 0,
        len(entities["teams"]) > 0,
        entities["status"] is not None,
        len(entities["dates"]) > 0,
    ])
    entities["confidence"] = min(signals / 4.0, 1.0)

    return entities
