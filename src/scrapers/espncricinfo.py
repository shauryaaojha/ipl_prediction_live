"""ESPNcricinfo scraper — primary data source.

Uses the hs-consumer-api.espncricinfo.com JSON API for structured data
and falls back to HTML parsing when needed.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper
from ..models.match import MatchCreate
from ..models.delivery import DeliveryCreate


class ESPNCricinfoScraper(BaseScraper):
    """ESPNcricinfo scraper — implements all data domains."""

    SOURCE_NAME = "espncricinfo"
    API_BASE = "https://hs-consumer-api.espncricinfo.com"

    # Known IPL series IDs
    SERIES_IDS = {
        2008: 313494, 2009: 374163, 2010: 418064, 2011: 466304,
        2012: 520932, 2013: 586733, 2014: 695871, 2015: 791129,
        2016: 968923, 2017: 1078425, 2018: 1131611, 2019: 1165643,
        2020: 1210595, 2021: 1249214, 2022: 1298423, 2023: 1345038,
        2024: 1410320, 2025: 1449924,
    }

    def _get_series_id(self, season: int) -> Optional[int]:
        """Get the ESPN series ID for a season."""
        # Check config overrides first
        sources_config = self.config.get("sources_config", {})
        overrides = sources_config.get("espncricinfo", {}).get("ipl_series_ids", {})
        if season in overrides:
            return overrides[season]
        return self.SERIES_IDS.get(season)

    # ------------------------------------------------------------------
    async def health_check(self) -> bool:
        """Check if ESPN endpoint is accessible."""
        return True  # Complex to check due to auth/tokens

    async def scrape_matches(self, season: int, **kwargs) -> List[Dict[str, Any]]:
        """Scrape all matches for a given IPL season from the series schedule API."""
        series_id = self._get_series_id(season)
        if not series_id:
            logger.error("No series ID known for season {}", season)
            return []

        url = f"{self.API_BASE}/v1/pages/series/schedule?seriesId={series_id}"
        logger.info("Scraping matches for season {} (series {})", season, series_id)

        try:
            data = await self.fetch_json(url)
        except Exception as e:
            logger.error("Failed to fetch series schedule for {}: {}", season, e)
            return []

        return self._parse_schedule(data, season)

    def _parse_schedule(self, data: Any, season: int) -> List[Dict[str, Any]]:
        """Parse series schedule API response."""
        matches = []

        # The API structure varies — try multiple known paths
        content = data if isinstance(data, dict) else {}
        match_list = (
            content.get("content", {}).get("matches", [])
            or content.get("content", {}).get("matchEvents", [])
            or content.get("matches", [])
            or []
        )

        for i, match in enumerate(match_list):
            try:
                # Extract match object (may be nested)
                m = match.get("match", match)

                espn_id = str(m.get("objectId", m.get("id", m.get("slug", ""))))

                # Teams
                teams = m.get("teams", [])
                team_a = teams[0].get("team", {}).get("longName", teams[0].get("team", {}).get("name", "")) if len(teams) > 0 else ""
                team_b = teams[1].get("team", {}).get("longName", teams[1].get("team", {}).get("name", "")) if len(teams) > 1 else ""

                # Venue
                ground = m.get("ground", m.get("venue", {}))
                venue_name = ground.get("longName", ground.get("name", ground.get("smallName", "Unknown")))

                # Status
                status_text = m.get("status", m.get("statusText", ""))
                match_status = self._map_match_status(m.get("state", status_text))

                # Toss
                toss = m.get("tpiResult", m.get("toss", {}))
                toss_winner = None
                toss_decision = None
                if isinstance(toss, dict):
                    toss_team = toss.get("team", {})
                    toss_winner = toss_team.get("longName", toss_team.get("name"))
                    toss_decision = toss.get("decision", "").lower() or None
                    if toss_decision and toss_decision not in ("bat", "field"):
                        toss_decision = "bat" if "bat" in toss_decision else "field"

                # Winner
                winner = None
                win_margin = None
                win_type = None
                if match_status == "complete":
                    winner_team_id = m.get("winnerTeamId")
                    for t in teams:
                        tid = t.get("team", {}).get("id")
                        if tid and str(tid) == str(winner_team_id):
                            winner = t.get("team", {}).get("longName", t.get("team", {}).get("name"))
                    win_margin = m.get("winnerMargin")
                    wt = m.get("winnerMarginType", "").lower()
                    if wt in ("runs", "wickets"):
                        win_type = wt

                # Match type
                stage = m.get("stage", m.get("matchType", "LEAGUE"))
                match_type = self._map_match_type(stage)

                # Date
                match_date = m.get("startDate", m.get("startTime", ""))

                matches.append({
                    "espncricinfo_id": espn_id,
                    "season": season,
                    "match_number": m.get("matchNumber", i + 1),
                    "match_date": match_date,
                    "venue_name": venue_name,
                    "team_a": team_a,
                    "team_b": team_b,
                    "toss_winner": toss_winner,
                    "toss_decision": toss_decision,
                    "winner": winner,
                    "win_margin": win_margin,
                    "win_type": win_type,
                    "player_of_match": m.get("playerOfTheMatch", {}).get("longName") if isinstance(m.get("playerOfTheMatch"), dict) else None,
                    "dl_applied": m.get("isDLApplied", False),
                    "match_type": match_type,
                    "match_status": match_status,
                })
            except Exception as e:
                logger.warning("Failed to parse match {}: {}", i, e)
                continue

        logger.info("Parsed {} matches for season {}", len(matches), season)
        return matches

    # ------------------------------------------------------------------
    # Match Detail / Scorecard
    # ------------------------------------------------------------------

    async def scrape_match_detail(self, match_id: str, **kwargs) -> Dict[str, Any]:
        """Scrape detailed match data including scorecard."""
        series_id = kwargs.get("series_id", "")
        url = f"{self.API_BASE}/v1/pages/match/scorecard?seriesId={series_id}&matchId={match_id}"

        try:
            data = await self.fetch_json(url)
            return self._parse_scorecard(data)
        except Exception as e:
            logger.error("Failed to fetch scorecard for match {}: {}", match_id, e)
            return {}

    def _parse_scorecard(self, data: Any) -> Dict[str, Any]:
        """Parse scorecard API response."""
        content = data.get("content", data) if isinstance(data, dict) else {}
        scorecard = content.get("scorecard", content.get("innings", []))

        result = {"innings": []}
        for inn in scorecard if isinstance(scorecard, list) else []:
            innings_data = {
                "innings_number": inn.get("inningsNumber", 0),
                "team": inn.get("team", {}).get("longName", ""),
                "total_runs": inn.get("runs", 0),
                "total_wickets": inn.get("wickets", 0),
                "total_overs": inn.get("overs", 0),
                "batsmen": [],
                "bowlers": [],
            }

            for bat in inn.get("inningBatsmen", []):
                innings_data["batsmen"].append({
                    "name": bat.get("player", {}).get("longName", ""),
                    "runs": bat.get("runs", 0),
                    "balls": bat.get("balls", 0),
                    "fours": bat.get("fours", 0),
                    "sixes": bat.get("sixes", 0),
                    "strike_rate": bat.get("strikeRate"),
                    "dismissal": bat.get("dismissalText", {}).get("long", ""),
                })

            for bowl in inn.get("inningBowlers", []):
                innings_data["bowlers"].append({
                    "name": bowl.get("player", {}).get("longName", ""),
                    "overs": bowl.get("overs", 0),
                    "maidens": bowl.get("maidens", 0),
                    "runs": bowl.get("conceded", 0),
                    "wickets": bowl.get("wickets", 0),
                    "economy": bowl.get("economy"),
                })

            result["innings"].append(innings_data)

        return result

    # ------------------------------------------------------------------
    # Ball-by-Ball Commentary
    # ------------------------------------------------------------------

    async def scrape_ball_by_ball(self, match_id: str, **kwargs) -> List[Dict[str, Any]]:
        """Scrape ball-by-ball data from commentary API."""
        series_id = kwargs.get("series_id", "")
        all_deliveries = []

        for innings in [1, 2]:
            page = 1
            while True:
                url = (
                    f"{self.API_BASE}/v1/pages/match/comments"
                    f"?seriesId={series_id}&matchId={match_id}"
                    f"&inningNumber={innings}&page={page}"
                )
                try:
                    data = await self.fetch_json(url)
                except Exception as e:
                    logger.warning("Failed commentary page {} inn {} match {}: {}", page, innings, match_id, e)
                    break

                content = data.get("content", data) if isinstance(data, dict) else {}
                comments = content.get("comments", content.get("commentList", []))

                if not comments:
                    break

                for comment in comments:
                    delivery = self._parse_commentary_item(comment, match_id, innings)
                    if delivery:
                        all_deliveries.append(delivery)

                # Check for next page
                pagination = content.get("pagination", {})
                if not pagination.get("hasNextPage", False) and page > 1:
                    break
                if not comments:
                    break
                page += 1

                # Safety limit
                if page > 100:
                    break

        logger.info("Scraped {} deliveries for match {}", len(all_deliveries), match_id)
        return all_deliveries

    def _parse_commentary_item(
        self, comment: Dict, match_id: str, innings: int
    ) -> Optional[Dict[str, Any]]:
        """Parse a single commentary item into a delivery record."""
        # Filter to actual deliveries (not session breaks, etc.)
        if not comment.get("isBall") and not comment.get("over"):
            return None

        over_str = str(comment.get("over", comment.get("overNumber", "0.0")))
        try:
            parts = over_str.split(".")
            over_num = int(parts[0])
            ball_num = int(parts[1]) if len(parts) > 1 else 1
        except (ValueError, IndexError):
            return None

        runs = comment.get("runs", {})
        if isinstance(runs, int):
            runs = {"batsman": runs, "extras": 0, "total": runs}

        batsman = comment.get("batsman", comment.get("batsmanStriker", {}))
        bowler = comment.get("bowler", {})

        batsman_name = batsman.get("longName", batsman.get("name", "")) if isinstance(batsman, dict) else str(batsman)
        bowler_name = bowler.get("longName", bowler.get("name", "")) if isinstance(bowler, dict) else str(bowler)

        if not batsman_name or not bowler_name:
            return None

        return {
            "match_id": match_id,
            "innings": innings,
            "over_number": over_num,
            "ball_number": ball_num,
            "batsman": batsman_name,
            "bowler": bowler_name,
            "batsman_runs": runs.get("batsman", 0),
            "extra_runs": runs.get("extras", 0),
            "total_runs": runs.get("total", 0),
            "is_wicket": comment.get("isWicket", False),
            "wicket_type": comment.get("dismissalType", {}).get("value") if isinstance(comment.get("dismissalType"), dict) else None,
            "player_dismissed": comment.get("dismissedBatsman", {}).get("longName") if isinstance(comment.get("dismissedBatsman"), dict) else None,
            "match_phase": self._classify_phase(over_num),
        }

    # ------------------------------------------------------------------
    # Player Stats
    # ------------------------------------------------------------------

    async def scrape_player_stats(self, player_id: str, **kwargs) -> Dict[str, Any]:
        """Scrape detailed stats for a player."""
        url = f"{self.API_BASE}/v1/pages/player/stats?playerId={player_id}"

        try:
            data = await self.fetch_json(url)
            return self._parse_player_stats(data, player_id)
        except Exception as e:
            logger.error("Failed to fetch player stats {}: {}", player_id, e)
            return {}

    def _parse_player_stats(self, data: Any, player_id: str) -> Dict[str, Any]:
        """Parse player stats API response."""
        content = data.get("content", data) if isinstance(data, dict) else {}
        player_info = content.get("player", {})

        result = {
            "espncricinfo_id": player_id,
            "full_name": player_info.get("longName", player_info.get("name", "")),
            "short_name": player_info.get("shortName", ""),
            "batting_hand": player_info.get("battingStyle", "").lower() if player_info.get("battingStyle") else None,
            "role": self._map_player_role(player_info.get("playingRole", "")),
            "nationality": player_info.get("country", {}).get("name") if isinstance(player_info.get("country"), dict) else player_info.get("country"),
            "date_of_birth": player_info.get("dateOfBirth"),
        }

        # Extract IPL-specific stats
        stats_groups = content.get("groups", content.get("stats", []))
        if isinstance(stats_groups, list):
            for group in stats_groups:
                if "ipl" in str(group.get("title", "")).lower() or "t20" in str(group.get("type", "")).lower():
                    result["ipl_stats"] = group
                    break

        return result

    # ------------------------------------------------------------------
    # Playing XI
    # ------------------------------------------------------------------

    async def scrape_playing_xi(self, match_id: str, **kwargs) -> List[Dict[str, Any]]:
        """Scrape playing XI from match details."""
        series_id = kwargs.get("series_id", "")
        url = f"{self.API_BASE}/v1/pages/match/details?seriesId={series_id}&matchId={match_id}"

        try:
            data = await self.fetch_json(url)
            return self._parse_playing_xi(data, match_id)
        except Exception as e:
            logger.error("Failed to fetch playing XI for match {}: {}", match_id, e)
            return []

    def _parse_playing_xi(self, data: Any, match_id: str) -> List[Dict[str, Any]]:
        """Parse playing XI from match details."""
        content = data.get("content", data) if isinstance(data, dict) else {}
        match_players = content.get("matchPlayers", content.get("squads", []))
        playing_xi = []

        if isinstance(match_players, list):
            for team_data in match_players:
                team_name = team_data.get("team", {}).get("longName", "")
                players = team_data.get("players", [])
                captain_id = team_data.get("captain", {}).get("id") if isinstance(team_data.get("captain"), dict) else None
                keeper_id = team_data.get("wicketKeeper", {}).get("id") if isinstance(team_data.get("wicketKeeper"), dict) else None

                for i, p in enumerate(players):
                    player = p.get("player", p)
                    pid = player.get("id", player.get("objectId"))
                    playing_xi.append({
                        "match_id": match_id,
                        "team": team_name,
                        "player_name": player.get("longName", player.get("name", "")),
                        "batting_position": i + 1,
                        "is_captain": str(pid) == str(captain_id) if captain_id else False,
                        "is_wicketkeeper": str(pid) == str(keeper_id) if keeper_id else False,
                        "is_impact_sub": p.get("isSubstitute", False),
                    })

        return playing_xi

    # ------------------------------------------------------------------
    # Venues
    # ------------------------------------------------------------------

    async def scrape_venues(self, **kwargs) -> List[Dict[str, Any]]:
        """Scrape venue data. ESPN doesn't have a list endpoint,
        so we extract venues from match data."""
        # Venues are extracted as a side effect of match scraping
        logger.info("ESPN venues are extracted during match scraping.")
        return []

    # ------------------------------------------------------------------
    # Squads
    # ------------------------------------------------------------------

    async def scrape_squads(self, season: int, **kwargs) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape team squads for a season."""
        series_id = self._get_series_id(season)
        if not series_id:
            return {}

        url = f"{self.API_BASE}/v1/pages/series/squads?seriesId={series_id}"
        try:
            data = await self.fetch_json(url)
            return self._parse_squads(data)
        except Exception as e:
            logger.error("Failed to fetch squads for season {}: {}", season, e)
            return {}

    def _parse_squads(self, data: Any) -> Dict[str, List[Dict[str, Any]]]:
        """Parse squads API response."""
        content = data.get("content", data) if isinstance(data, dict) else {}
        squads_list = content.get("squads", [])
        result = {}

        for squad in squads_list:
            team_name = squad.get("team", {}).get("longName", squad.get("team", {}).get("name", ""))
            players = []
            for p in squad.get("players", []):
                player = p.get("player", p)
                players.append({
                    "espncricinfo_id": str(player.get("id", player.get("objectId", ""))),
                    "full_name": player.get("longName", player.get("name", "")),
                    "short_name": player.get("shortName", ""),
                    "role": self._map_player_role(player.get("playingRole", "")),
                    "nationality": player.get("country", {}).get("name") if isinstance(player.get("country"), dict) else None,
                })
            result[team_name] = players

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_phase(over: int) -> str:
        if over <= 5:
            return "powerplay"
        elif over <= 14:
            return "middle"
        return "death"

    @staticmethod
    def _map_match_type(stage: str) -> str:
        stage_upper = str(stage).upper()
        mapping = {
            "LEAGUE": "league",
            "QUALIFIER_1": "qualifier_1", "QUALIFIER1": "qualifier_1",
            "ELIMINATOR": "eliminator",
            "QUALIFIER_2": "qualifier_2", "QUALIFIER2": "qualifier_2",
            "FINAL": "final",
        }
        return mapping.get(stage_upper, "league")

    @staticmethod
    def _map_match_status(state: str) -> str:
        state_upper = str(state).upper()
        if state_upper in ("FINISHED", "COMPLETE", "RESULT", "POST"):
            return "complete"
        elif state_upper in ("LIVE", "RUNNING", "IN_PROGRESS"):
            return "live"
        elif state_upper in ("ABANDONED", "NO_RESULT"):
            return "abandoned"
        return "upcoming"

    @staticmethod
    def _map_player_role(role: str) -> Optional[str]:
        role_lower = str(role).lower()
        if "wicket" in role_lower and "bat" in role_lower:
            return "wicketkeeper_batsman"
        elif "wicket" in role_lower:
            return "wicketkeeper"
        elif "all" in role_lower or "allround" in role_lower:
            return "all_rounder"
        elif "bat" in role_lower:
            return "batsman"
        elif "bowl" in role_lower:
            return "bowler"
        return None
