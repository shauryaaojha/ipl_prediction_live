"""Request cache manager.

Uses SQLite to track ETags, last-modified timestamps, and request
deduplication to avoid redundant fetches.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import os

from loguru import logger


class CacheManager:
    """Manages HTTP request caching with ETag and timestamp support."""

    def __init__(self, cache_path: Optional[str] = None):
        if cache_path is None:
            data_path = os.getenv("DATA_PATH", "./data")
            cache_path = str(Path(data_path) / "cache" / "request_cache.db")
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS request_cache (
                    url TEXT PRIMARY KEY,
                    etag TEXT,
                    last_modified TEXT,
                    response_hash TEXT,
                    last_fetched TIMESTAMP,
                    status_code INTEGER,
                    content_length INTEGER
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def get_etag(self, url: str) -> Optional[str]:
        """Get stored ETag for a URL."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT etag FROM request_cache WHERE url = ?", (url,)
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def get_last_modified(self, url: str) -> Optional[str]:
        """Get stored Last-Modified header for a URL."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT last_modified FROM request_cache WHERE url = ?", (url,)
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def should_fetch(self, url: str, max_age_hours: int = 24) -> bool:
        """Determine if a URL should be re-fetched based on age."""
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT last_fetched FROM request_cache WHERE url = ?", (url,)
            ).fetchone()
            if not row:
                return True
            last = datetime.fromisoformat(row[0])
            return datetime.utcnow() - last > timedelta(hours=max_age_hours)
        finally:
            conn.close()

    def update(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        response_hash: Optional[str] = None,
        status_code: int = 200,
        content_length: int = 0,
    ) -> None:
        """Update cache entry for a URL."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO request_cache
                   (url, etag, last_modified, response_hash, last_fetched, status_code, content_length)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (url, etag, last_modified, response_hash,
                 datetime.utcnow().isoformat(), status_code, content_length),
            )
            conn.commit()
        finally:
            conn.close()

    def clear(self) -> None:
        """Clear all cache entries."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("DELETE FROM request_cache")
            conn.commit()
            logger.info("Request cache cleared.")
        finally:
            conn.close()
