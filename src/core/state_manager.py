"""Scrape state manager.

Tracks scraping progress and checkpoints so that interrupted runs can
resume from where they left off.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import os

from loguru import logger


class StateManager:
    """Tracks scrape checkpoints for incremental/resumable runs."""

    def __init__(self, state_path: Optional[str] = None):
        if state_path is None:
            data_path = os.getenv("DATA_PATH", "./data")
            state_path = str(Path(data_path) / "cache" / "scrape_state.db")
        Path(state_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = state_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scrape_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def get(self, key: str) -> Optional[str]:
        """Get a state value."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT value FROM scrape_state WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def set(self, key: str, value: str) -> None:
        """Set a state value."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO scrape_state (key, value, updated_at)
                   VALUES (?, ?, ?)""",
                (key, value, datetime.utcnow().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_json(self, key: str) -> Optional[Any]:
        """Get a JSON state value."""
        val = self.get(key)
        return json.loads(val) if val else None

    def set_json(self, key: str, value: Any) -> None:
        """Set a JSON state value."""
        self.set(key, json.dumps(value))

    def get_last_season_scraped(self) -> Optional[int]:
        """Get the last season that was fully scraped."""
        val = self.get("last_season_scraped")
        return int(val) if val else None

    def set_last_season_scraped(self, season: int) -> None:
        """Mark a season as fully scraped."""
        self.set("last_season_scraped", str(season))

    def is_match_scraped(self, match_id: str) -> bool:
        """Check if a match has been scraped."""
        val = self.get(f"match_{match_id}")
        return val == "done"

    def mark_match_scraped(self, match_id: str) -> None:
        """Mark a match as scraped."""
        self.set(f"match_{match_id}", "done")

    def get_checkpoint(self, job_name: str) -> Optional[Dict[str, Any]]:
        """Get a job checkpoint (for resuming interrupted jobs)."""
        return self.get_json(f"checkpoint_{job_name}")

    def save_checkpoint(self, job_name: str, data: Dict[str, Any]) -> None:
        """Save a job checkpoint."""
        self.set_json(f"checkpoint_{job_name}", data)

    def clear_checkpoint(self, job_name: str) -> None:
        """Clear a job checkpoint (job completed successfully)."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM scrape_state WHERE key = ?", (f"checkpoint_{job_name}",))
            conn.commit()
        finally:
            conn.close()
