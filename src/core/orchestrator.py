"""Orchestrator Engine — central coordinator for all scraping operations.

Manages the execution pipeline: initializes scrapers, coordinates data
collection with fallback logic, handles scheduling, and persists results.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from ..scrapers.espncricinfo import ESPNCricinfoScraper
from ..scrapers.cricbuzz import CricbuzzScraper
from ..scrapers.iplt20 import IPLT20Scraper
from ..scrapers.cricsheet import CricsheetScraper
from ..scrapers.weather_api import WeatherScraper
from ..scrapers.news_scraper import NewsScraper
from ..parsers.match_parser import normalize_match_data, merge_match_sources
from ..parsers.delivery_parser import normalize_deliveries
from ..parsers.player_parser import normalize_player, normalize_player_stats
from ..storage.postgres_repo import (
    MatchRepository,
    PlayerRepository,
    TeamRepository,
    VenueRepository,
    DeliveryRepository,
    PlayerStatsRepository,
    ScrapeLogRepository,
)
from ..storage.json_warehouse import JsonWarehouse
from ..utils.http_client import HttpClient
from .state_manager import StateManager
from .notification import send_notification
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type


class ScraperOrchestrator:
    """Central coordinator for all scraping operations."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.http_client = HttpClient(
            max_retries=config.get("max_retries", 3),
            request_delay=config.get("request_delay", 1.5),
            request_delay_max=config.get("request_delay_max", 3.5),
            timeout=config.get("download_timeout", 30),
            http2=config.get("http2_enabled", True),
        )

        # Initialize scrapers
        self.espn = ESPNCricinfoScraper(config, self.http_client)
        self.cricbuzz = CricbuzzScraper(config, self.http_client)
        self.iplt20 = IPLT20Scraper(config, self.http_client)
        self.cricsheet = CricsheetScraper(config, self.http_client)
        self.weather = WeatherScraper(config, self.http_client)
        self.news = NewsScraper(config, self.http_client)

        # Initialize repositories
        self.match_repo = MatchRepository()
        self.player_repo = PlayerRepository()
        self.team_repo = TeamRepository()
        self.venue_repo = VenueRepository()
        self.delivery_repo = DeliveryRepository()
        self.stats_repo = PlayerStatsRepository()
        self.log_repo = ScrapeLogRepository()
        self.warehouse = JsonWarehouse()

        # State management
        self.state = StateManager()

    async def close(self):
        """Clean up resources."""
        await self.http_client.close()

    # ------------------------------------------------------------------
    # Full Historical Scrape
    # ------------------------------------------------------------------

    async def run_full_historical_scrape(
        self,
        start_season: int = 2008,
        end_season: int = 2025,
    ) -> None:
        """One-time scrape of all historical data."""
        logger.info("Starting full historical scrape: {} to {}", start_season, end_season)
        send_notification("IPL Scraper", f"Starting historical scrape ({start_season}-{end_season})")

        total_matches = 0
        total_deliveries = 0

        for season in range(start_season, end_season + 1):
            # Check if already done
            last_scraped = self.state.get_last_season_scraped()
            # if last_scraped and season <= last_scraped:
            #     logger.info("Season {} already scraped, skipping.", season)
            #     continue

            log_id = self.log_repo.start_log(f"historical_{season}", "espncricinfo")

            try:
                # Step 1: Scrape matches using Cricsheet (guaranteed historical data)
                results = await self.cricsheet.scrape_matches(season)
                logger.info("Season {}: {} matches found via Cricsheet", season, len(results))

                # Step 2: Persist matches, players, and deliveries
                for result in results:
                    match_data = result["match"]
                    players_data = result["players"]
                    deliveries_data = result["deliveries"]

                    # 2a. Upsert players
                    for p in players_data:
                        self.player_repo.upsert(
                            full_name=p["full_name"],
                            sources=p.get("sources")
                        )

                    # 2b. Upsert match
                    normalized_match = normalize_match_data(match_data)
                    match_obj = self.match_repo.upsert(normalized_match)
                    total_matches += 1

                    # 2c. Insert deliveries
                    if deliveries_data:
                        # Map match_id to all deliveries and resolve player names to IDs
                        for d in deliveries_data:
                            d["match_id"] = match_obj.match_id
                            d["batsman_id"] = None
                            d["bowler_id"] = None
                            d["non_striker_id"] = None
                            d["player_dismissed_id"] = None
                            d["fielder_id"] = None
                            d["batting_team_id"] = None
                            d["bowling_team_id"] = None
                            
                            # Resolve batter
                            if batter := d.get("batter_name"):
                                p_obj = self.player_repo.get_by_name(batter)
                                if p_obj: d["batsman_id"] = p_obj.player_id
                                
                            # Resolve bowler
                            if bowler := d.get("bowler_name"):
                                p_obj = self.player_repo.get_by_name(bowler)
                                if p_obj: d["bowler_id"] = p_obj.player_id
                                
                            # Resolve non_striker
                            if ns := d.get("non_striker_name"):
                                p_obj = self.player_repo.get_by_name(ns)
                                if p_obj: d["non_striker_id"] = p_obj.player_id
                                
                            # Resolve player_dismissed
                            if pd := d.get("player_dismissed_name"):
                                p_obj = self.player_repo.get_by_name(pd)
                                if p_obj: d["player_dismissed_id"] = p_obj.player_id
                                
                            # Resolve fielder
                            if fd := d.get("fielder_name"):
                                p_obj = self.player_repo.get_by_name(fd)
                                if p_obj: d["fielder_id"] = p_obj.player_id
                                
                            # Resolve teams
                            if bt := d.get("batting_team"):
                                t_obj = self.team_repo.get_by_code(bt)
                                if t_obj: d["batting_team_id"] = t_obj.team_id
                                
                            if bowlt := d.get("bowling_team"):
                                t_obj = self.team_repo.get_by_code(bowlt)
                                if t_obj: d["bowling_team_id"] = t_obj.team_id

                            # Remove name keys as they aren't in DB schema
                            d.pop("batter_name", None)
                            d.pop("bowler_name", None)
                            d.pop("non_striker_name", None)
                            d.pop("player_dismissed_name", None)
                            d.pop("fielder_name", None)
                            d.pop("batting_team", None)
                            d.pop("bowling_team", None)

                        self.delivery_repo.bulk_insert(deliveries_data)
                        total_deliveries += len(deliveries_data)

                self.state.set_last_season_scraped(season)
                self.log_repo.finish_log(
                    log_id,
                    status="success",
                    records_fetched=len(results),
                    records_inserted=len(results),
                )

            except Exception as e:
                logger.error("Failed to scrape season {}: {}", season, e)
                self.log_repo.finish_log(log_id, status="failed", error_message=str(e))
                continue

        logger.info(
            "Historical scrape complete: {} matches, {} deliveries",
            total_matches, total_deliveries,
        )
        send_notification(
            "IPL Scraper — Complete",
            f"Historical scrape done: {total_matches} matches, {total_deliveries} deliveries",
        )

    # ------------------------------------------------------------------
    # Incremental Scrape
    # ------------------------------------------------------------------

    async def run_incremental_scrape(self) -> None:
        """Incremental scrape for the current/latest season."""
        logger.info("Starting incremental scrape...")
        log_id = self.log_repo.start_log("incremental", "mixed")

        try:
            # Scrape latest season
            latest_season = 2024  # Updated for demonstration (since 2026 data is empty)
            matches = await self._scrape_matches_with_fallback(latest_season)

            inserted = 0
            updated = 0
            for match_data in matches:
                normalized = normalize_match_data(match_data)
                existing = None
                if normalized.get("espncricinfo_id"):
                    existing = self.match_repo.get_by_espn_id(normalized["espncricinfo_id"])

                if existing:
                    if existing.match_status != "complete" and normalized.get("match_status") == "complete":
                        self.match_repo.upsert(normalized)
                        updated += 1
                else:
                    self.match_repo.upsert(normalized)
                    inserted += 1

            self.log_repo.finish_log(
                log_id,
                status="success",
                records_fetched=len(matches),
                records_inserted=inserted,
                records_updated=updated,
            )

        except Exception as e:
            logger.error("Incremental scrape failed: {}", e)
            self.log_repo.finish_log(log_id, status="failed", error_message=str(e))

    # ------------------------------------------------------------------
    # Match Scraping with Fallback
    # ------------------------------------------------------------------

    @retry(
        wait=wait_exponential(multiplier=2, min=4, max=30),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(RuntimeError),
        before_sleep=lambda retry_state: logger.warning(
            "Retrying _scrape_matches_with_fallback (attempt {}) due to: {}",
            retry_state.attempt_number,
            retry_state.outcome.exception(),
        )
    )
    async def _scrape_matches_with_fallback(self, season: int) -> List[Dict[str, Any]]:
        """Scrape matches from primary source, falling back to secondary sources."""
        # Use user-requested fallback sequence: IPLT20 -> Cricbuzz -> ESPN
        primary = "iplt20"
        fallbacks = ["cricbuzz", "espncricinfo"]

        scraper_map = {
            "espncricinfo": self.espn,
            "cricbuzz": self.cricbuzz,
            "iplt20": self.iplt20,
            "cricsheet": self.cricsheet,
        }

        matches = []
        for source_name in [primary] + fallbacks:
            scraper = scraper_map.get(source_name)
            if not scraper:
                continue
            try:
                matches = await scraper.scrape_matches(season)
                if matches:
                    logger.info("Source ({}) returned {} matches", source_name, len(matches))
                    break
                else:
                    logger.info("Source ({}) returned 0 matches, trying next fallback...", source_name)
            except Exception as e:
                logger.warning("Source ({}) failed: {}, trying next fallback...", source_name, e)

        if not matches:
            logger.error("All sources failed to fetch matches for season {}.", season)
            raise RuntimeError(f"All sources failed to fetch matches for season {season}")
            
        return matches

    # ------------------------------------------------------------------
    # Scrape Specific Match
    # ------------------------------------------------------------------

    async def scrape_single_match(
        self,
        match_id: str,
        source: str = "espncricinfo",
    ) -> Dict[str, Any]:
        """Scrape a specific match by ID."""
        scraper_map = {
            "espncricinfo": self.espn,
            "cricbuzz": self.cricbuzz,
            "iplt20": self.iplt20,
        }
        scraper = scraper_map.get(source)
        if not scraper:
            raise ValueError(f"Unknown source: {source}")

        detail = await scraper.scrape_match_detail(match_id)
        return detail

    # ------------------------------------------------------------------
    # Player Stats
    # ------------------------------------------------------------------

    async def scrape_player(self, player_id: str, source: str = "espncricinfo") -> Dict[str, Any]:
        """Scrape stats for a single player."""
        if source == "espncricinfo":
            return await self.espn.scrape_player_stats(player_id)
        elif source == "iplt20":
            # IPLT20 stats are aggregated, not per-player API
            logger.warning("IPLT20 doesn't support individual player stat scraping via API.")
            return {}
        return {}

    # ------------------------------------------------------------------
    # Injury Check
    # ------------------------------------------------------------------

    async def check_injuries(self) -> List[Dict[str, Any]]:
        """Run injury news scraping across all sources."""
        logger.info("Checking for injury updates...")
        results = await self.news.scrape_all_news()
        logger.info("Found {} injury-related articles", len(results))
        return results

    # ------------------------------------------------------------------
    # Scheduling
    # ------------------------------------------------------------------

    def schedule_jobs(self) -> None:
        """Configure APScheduler jobs."""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger

            scheduler = AsyncIOScheduler()

            sched_config = self.config.get("scheduling", {})

            # Incremental scrape
            if sched_config.get("incremental_scrape"):
                scheduler.add_job(
                    self.run_incremental_scrape,
                    CronTrigger.from_crontab(sched_config["incremental_scrape"]),
                    id="incremental_scrape",
                    name="Incremental Data Scrape",
                    replace_existing=True,
                )

            # Injury check
            if sched_config.get("injury_check"):
                scheduler.add_job(
                    self.check_injuries,
                    CronTrigger.from_crontab(sched_config["injury_check"]),
                    id="injury_check",
                    name="Player Availability Check",
                    replace_existing=True,
                )

            scheduler.start()
            logger.info("APScheduler started with configured jobs.")
            return scheduler

        except ImportError:
            logger.warning("APScheduler not installed. Scheduling unavailable.")
            return None
