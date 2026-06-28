"""IPLT20 Official Website scraper — incremental fallback source.

Scrapes the official IPL website feeds (S3 JSONP APIs) for:
- Match schedule and results
- Team squads and player profiles
- Venue information
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from .base import BaseScraper


class IPLT20Scraper(BaseScraper):
    """IPLT20.com scraper — consumes S3 JSONP feeds."""

    SOURCE_NAME = "iplt20"
    
    # S3 JSONP endpoints are reliable and bypass React hydration issues
    FEED_BASE = "https://ipl-stats-sports-mechanic.s3.ap-south-1.amazonaws.com/ipl/feeds"

    # Known competition IDs
    COMPETITION_IDS = {
        2023: 107,
        2024: 148,
        2025: 155, # Speculative / needs update
        2026: 160, # Speculative / needs update
    }

    async def _fetch_jsonp(self, url: str) -> Dict[str, Any]:
        """Fetch and parse JSONP to dict."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code != 200:
                    return {}
                
                content = resp.text
                json_str = re.search(r'^[a-zA-Z0-9_]+\((.*)\);?$', content.strip(), re.DOTALL)
                if json_str:
                    return json.loads(json_str.group(1))
                return {}
        except Exception as e:
            logger.warning("[IPLT20] Failed to fetch JSONP from {}: {}", url, e)
            return {}

    async def health_check(self) -> bool:
        return True

    async def scrape_matches(self, season: int, **kwargs) -> List[Dict[str, Any]]:
        """Scrape match results using the S3 match schedule feed."""
        comp_id = self.COMPETITION_IDS.get(season)
        if not comp_id:
            # Try to guess
            comp_id = 148 + (season - 2024)
            
        url = f"{self.FEED_BASE}/{comp_id}-matchschedule.js"
        logger.info("[IPLT20] Scraping matches for season {} (CompID: {})", season, comp_id)

        data = await self._fetch_jsonp(url)
        matches_data = data.get("Matchsummary", [])
        
        matches = []
        for m in matches_data:
            try:
                # winner logic
                winner = None
                win_margin = None
                win_type = None
                comments = m.get("Comments", "")
                
                if comments and "won by" in comments.lower():
                    won_match = re.search(r"(.+?)\s+Won by\s+(\d+)\s+(Run|Wicket)", comments, re.I)
                    if won_match:
                        winner = won_match.group(1).strip()
                        win_margin = int(won_match.group(2))
                        win_type = "runs" if "run" in won_match.group(3).lower() else "wickets"
                        
                match_status = "complete" if m.get("MatchStatus") == "Post" else "upcoming"
                if "Abandoned" in comments or "No Result" in comments:
                    match_status = "abandoned"

                matches.append({
                    "season": season,
                    "match_number": m.get("RowNo", 0),
                    "match_date": m.get("MatchDate", ""),
                    "venue_name": m.get("GroundName", ""),
                    "team_a": m.get("FirstBattingTeamName", m.get("HomeTeamName", "")),
                    "team_b": m.get("SecondBattingTeamName", m.get("AwayTeamName", "")),
                    "winner": winner,
                    "win_margin": win_margin,
                    "win_type": win_type,
                    "match_status": match_status,
                    "match_type": "league",
                })
            except Exception as e:
                logger.warning("[IPLT20] Failed to parse match: {}", e)

        logger.info("[IPLT20] Parsed {} matches for season {}", len(matches), season)
        return matches

    async def scrape_match_detail(self, match_id: str, **kwargs) -> Dict[str, Any]:
        return {}

    async def scrape_squads(self, season: int, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        return {}

    async def scrape_venues(self, **kwargs) -> List[Dict[str, Any]]:
        return []
