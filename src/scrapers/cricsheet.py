"""Cricsheet Scraper — For guaranteed historical data."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from loguru import logger

from .base import BaseScraper


class CricsheetScraper(BaseScraper):
    """Downloads and parses historical IPL data from Cricsheet.org."""

    SOURCE_NAME = "cricsheet"
    DATA_URL = "https://cricsheet.org/downloads/ipl_json.zip"

    async def _ensure_data(self) -> Path:
        """Download and extract Cricsheet IPL zip if not present."""
        cache_dir = Path(self.config.get("storage", {}).get("data_path", "data")) / "cache" / "cricsheet"
        cache_dir.mkdir(parents=True, exist_ok=True)
        zip_path = cache_dir / "ipl_json.zip"
        
        if not zip_path.exists():
            logger.info("[Cricsheet] Downloading historical data from {}", self.DATA_URL)
            # Use a separate httpx client for large downloads to avoid timeout issues
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(self.DATA_URL, follow_redirects=True)
                resp.raise_for_status()
                with open(zip_path, "wb") as f:
                    f.write(resp.content)
            
            logger.info("[Cricsheet] Extracting data...")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(cache_dir)
                
            # Record dataset import
            try:
                import hashlib
                from ..storage.postgres_repo import DatasetImportRepository
                with open(zip_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                DatasetImportRepository().record_import("cricsheet", "latest", file_hash)
                logger.info("[Cricsheet] Recorded import with checksum {}", file_hash)
            except Exception as e:
                logger.warning("Failed to record import: {}", e)
                
        return cache_dir

    async def health_check(self) -> bool:
        return True

    async def scrape_matches(self, season: int, **kwargs) -> List[Dict[str, Any]]:
        """Scrape match results for a given season from Cricsheet.
        Returns a list of dicts with 'match', 'players', and 'deliveries'.
        """
        from ..parsers.cricsheet_parser import CricsheetParser
        cache_dir = await self._ensure_data()
        results = []
        parser = CricsheetParser(season)
        
        # Iterate over JSON files in cache_dir
        for file_path in cache_dir.glob("*.json"):
            if not file_path.stem.isdigit():
                continue
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    info = data.get("info", {})
                    
                    match_create, players, deliveries = parser.parse(data, match_id_str=file_path.stem)
                    if match_create:
                        results.append({
                            "match": match_create.model_dump(),
                            "players": players,
                            "deliveries": deliveries
                        })
            except Exception as e:
                logger.warning("[Cricsheet] Failed to parse {}: {}", file_path.name, e)
                
        logger.info("[Cricsheet] Found {} matches for season {}", len(results), season)
        # Sort matches by date to ensure proper order
        results.sort(key=lambda x: x["match"]["match_date"])
        
        # Assign match numbers sequentially if missing or zero
        for i, res in enumerate(results):
            if not res["match"].get("match_number"):
                res["match"]["match_number"] = i + 1

        return results

    async def scrape_match_detail(self, match_id: str, **kwargs) -> Dict[str, Any]:
        """Not strictly needed since historical-scrape only uses scrape_matches directly."""
        return {}
