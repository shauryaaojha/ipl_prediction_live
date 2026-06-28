"""Cricbuzz scraper — fallback data source.

Scrapes match results, playing XI, and injury/news data from Cricbuzz
using HTML parsing with BeautifulSoup.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper


class CricbuzzScraper(BaseScraper):
    """Cricbuzz HTML scraper — fallback for when ESPN data is incomplete."""

    SOURCE_NAME = "cricbuzz"
    BASE_URL = "https://www.cricbuzz.com"

    # Known IPL series slugs on Cricbuzz
    SERIES_SLUGS = {
        2023: "6732/indian-premier-league-2023",
        2024: "7607/indian-premier-league-2024",
        2025: "9237/indian-premier-league-2025",
    }

    async def health_check(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Match Results
    # ------------------------------------------------------------------

    async def scrape_matches(self, season: int, **kwargs) -> List[Dict[str, Any]]:
        """Scrape match results from Cricbuzz series page."""
        slug = self.SERIES_SLUGS.get(season)
        if not slug:
            logger.warning("[Cricbuzz] No series slug for season {}", season)
            return []

        url = f"{self.BASE_URL}/cricket-series/{slug}/matches"
        logger.info("[Cricbuzz] Scraping matches for season {}", season)

        try:
            html = await self.fetch_html(url)
        except Exception as e:
            logger.error("[Cricbuzz] Failed to fetch matches for {}: {}", season, e)
            return []

        return self._parse_matches_page(html, season)

    def _parse_matches_page(self, html: str, season: int) -> List[Dict[str, Any]]:
        """Parse Cricbuzz matches page HTML."""
        soup = BeautifulSoup(html, "lxml")
        matches = []

        # Cricbuzz uses div-based match cards
        match_cards = soup.select("div.cb-col-100.cb-col.cb-schdl") or soup.select("div.cb-mtch-lst")

        for i, card in enumerate(match_cards):
            try:
                # Extract match title / teams
                header = card.select_one("h3, .cb-lv-scr-mtch-hdr, .cb-billing-plans-text")
                if not header:
                    continue

                title_text = header.get_text(strip=True)

                # Try to extract team names from title like "CSK vs MI"
                team_match = re.search(r"(.+?)\s+(?:vs?|VS)\s+(.+?)(?:,|\s*$)", title_text)
                team_a = team_match.group(1).strip() if team_match else ""
                team_b = team_match.group(2).strip() if team_match else ""

                if not team_a or not team_b:
                    continue

                # Extract result text
                result_el = card.select_one(".cb-text-complete, .cb-mtch-crd-stt")
                result_text = result_el.get_text(strip=True) if result_el else ""

                # Determine winner from result text
                winner = None
                win_margin = None
                win_type = None
                match_status = "upcoming"

                if result_text:
                    match_status = "complete"
                    won_match = re.search(r"(.+?)\s+won\s+by\s+(\d+)\s+(run|wicket)", result_text, re.I)
                    if won_match:
                        winner = won_match.group(1).strip()
                        win_margin = int(won_match.group(2))
                        win_type = "runs" if "run" in won_match.group(3).lower() else "wickets"
                    elif "no result" in result_text.lower():
                        match_status = "abandoned"

                # Extract venue
                venue_el = card.select_one(".text-gray, .cb-mtch-crd-lct")
                venue_text = venue_el.get_text(strip=True) if venue_el else "Unknown"

                matches.append({
                    "season": season,
                    "match_number": i + 1,
                    "match_date": "",  # Cricbuzz date parsing is complex
                    "venue_name": venue_text,
                    "team_a": team_a,
                    "team_b": team_b,
                    "winner": winner,
                    "win_margin": win_margin,
                    "win_type": win_type,
                    "match_status": match_status,
                    "match_type": "league",
                })
            except Exception as e:
                logger.warning("[Cricbuzz] Failed to parse match card {}: {}", i, e)

        logger.info("[Cricbuzz] Parsed {} matches for season {}", len(matches), season)
        return matches

    # ------------------------------------------------------------------
    # Match Detail
    # ------------------------------------------------------------------

    async def scrape_match_detail(self, match_id: str, **kwargs) -> Dict[str, Any]:
        """Scrape scorecard for a specific match."""
        url = f"{self.BASE_URL}/api/html/cricket-scorecard/{match_id}"
        try:
            html = await self.fetch_html(url)
            return self._parse_scorecard(html)
        except Exception as e:
            logger.error("[Cricbuzz] Failed scorecard for match {}: {}", match_id, e)
            return {}

    def _parse_scorecard(self, html: str) -> Dict[str, Any]:
        """Parse Cricbuzz scorecard HTML."""
        soup = BeautifulSoup(html, "lxml")
        result = {"innings": []}

        innings_headers = soup.select("div.cb-scrd-hdr-rw")
        for inn_header in innings_headers:
            innings_data = {
                "team": inn_header.get_text(strip=True),
                "batsmen": [],
                "bowlers": [],
            }

            # Parse batting table
            parent = inn_header.find_parent()
            if parent:
                bat_rows = parent.select("div.cb-col.cb-col-100.cb-scrd-itms")
                for row in bat_rows:
                    cols = row.select("div.cb-col")
                    if len(cols) >= 7:
                        name_el = cols[0].select_one("a")
                        if name_el:
                            innings_data["batsmen"].append({
                                "name": name_el.get_text(strip=True),
                                "runs": self._safe_int(cols[2].get_text(strip=True)),
                                "balls": self._safe_int(cols[3].get_text(strip=True)),
                                "fours": self._safe_int(cols[4].get_text(strip=True)),
                                "sixes": self._safe_int(cols[5].get_text(strip=True)),
                                "strike_rate": self._safe_float(cols[6].get_text(strip=True)),
                            })

            result["innings"].append(innings_data)

        return result

    # ------------------------------------------------------------------
    # Playing XI
    # ------------------------------------------------------------------

    async def scrape_playing_xi(self, match_id: str, **kwargs) -> List[Dict[str, Any]]:
        """Scrape playing XI from Cricbuzz match page."""
        url = f"{self.BASE_URL}/cricket-scorecard/{match_id}"
        try:
            html = await self.fetch_html(url)
            return self._parse_playing_xi(html, match_id)
        except Exception as e:
            logger.error("[Cricbuzz] Failed playing XI for match {}: {}", match_id, e)
            return []

    def _parse_playing_xi(self, html: str, match_id: str) -> List[Dict[str, Any]]:
        """Parse playing XI from match page."""
        soup = BeautifulSoup(html, "lxml")
        playing_xi = []

        squad_sections = soup.select("div.cb-minfo-tm") or soup.select("div.cb-play11-lft-col, div.cb-play11-rt-col")
        for section in squad_sections:
            team_el = section.select_one("div.cb-team-info, span.cb-team1, span.cb-team2")
            team_name = team_el.get_text(strip=True) if team_el else "Unknown"

            player_els = section.select("a.cb-player-name-left, div.cb-player-name-left a")
            for i, pel in enumerate(player_els):
                player_name = pel.get_text(strip=True)
                is_captain = "(c)" in player_name.lower() or bool(pel.find_next_sibling(string=re.compile(r"\(c\)", re.I)))
                is_keeper = "(wk)" in player_name.lower() or bool(pel.find_next_sibling(string=re.compile(r"\(wk\)", re.I)))
                player_name = re.sub(r"\s*\((?:c|wk|c & wk)\)\s*", "", player_name, flags=re.I).strip()

                playing_xi.append({
                    "match_id": match_id,
                    "team": team_name,
                    "player_name": player_name,
                    "batting_position": i + 1,
                    "is_captain": is_captain,
                    "is_wicketkeeper": is_keeper,
                    "is_impact_sub": False,
                })

        return playing_xi

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_int(text: str) -> int:
        try:
            return int(re.sub(r"[^\d-]", "", text))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _safe_float(text: str) -> Optional[float]:
        try:
            return float(text)
        except (ValueError, TypeError):
            return None
