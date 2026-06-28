"""SQLite-based JSON Warehouse.

Stores raw HTML snapshots, raw API JSON responses, and unstructured data.
Replaces MongoDB with a lighter-weight, zero-dependency solution.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from .connection import get_warehouse_connection


class JsonWarehouse:
    """Repository for raw / unstructured data stored in SQLite."""

    # -----------------------------------------------------------------------
    # Raw Match Pages
    # -----------------------------------------------------------------------

    def store_match_page(
        self,
        match_id: str,
        source: str,
        url: str,
        html_content: str,
        etag: Optional[str] = None,
    ) -> None:
        """Store a raw HTML page for a match."""
        conn = get_warehouse_connection()
        try:
            conn.execute(
                """INSERT INTO raw_match_pages (match_id, source, url, html_content, etag, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (match_id, source, url, html_content, etag, datetime.utcnow().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_match_page(self, match_id: str, source: str = "espncricinfo") -> Optional[Dict]:
        """Get the latest raw HTML for a match from a specific source."""
        conn = get_warehouse_connection()
        try:
            row = conn.execute(
                """SELECT * FROM raw_match_pages
                   WHERE match_id = ? AND source = ?
                   ORDER BY scraped_at DESC LIMIT 1""",
                (match_id, source),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Raw Ball-by-Ball
    # -----------------------------------------------------------------------

    def store_ball_by_ball(
        self,
        match_id: str,
        source: str,
        json_payload: Any,
        page: int = 1,
    ) -> None:
        """Store raw ball-by-ball API response."""
        conn = get_warehouse_connection()
        try:
            conn.execute(
                """INSERT INTO raw_ball_by_ball (match_id, source, json_payload, page, scraped_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    match_id,
                    source,
                    json.dumps(json_payload) if not isinstance(json_payload, str) else json_payload,
                    page,
                    datetime.utcnow().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_ball_by_ball(self, match_id: str) -> List[Dict]:
        """Get all raw ball-by-ball pages for a match."""
        conn = get_warehouse_connection()
        try:
            rows = conn.execute(
                """SELECT * FROM raw_ball_by_ball
                   WHERE match_id = ?
                   ORDER BY page""",
                (match_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Raw Player Profiles
    # -----------------------------------------------------------------------

    def store_player_profile(
        self,
        player_id: str,
        source: str,
        profile_html: Optional[str] = None,
        stats_json: Optional[Any] = None,
    ) -> None:
        """Store a raw player profile page or stats JSON."""
        conn = get_warehouse_connection()
        try:
            stats_str = json.dumps(stats_json) if stats_json and not isinstance(stats_json, str) else stats_json
            conn.execute(
                """INSERT INTO raw_player_profiles (player_id, source, profile_html, stats_json, scraped_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (player_id, source, profile_html, stats_str, datetime.utcnow().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    # -----------------------------------------------------------------------
    # Raw News Articles
    # -----------------------------------------------------------------------

    def store_news_article(
        self,
        url: str,
        title: str,
        content_text: str,
        published_date: Optional[str] = None,
        nlp_entities: Optional[Dict] = None,
    ) -> None:
        """Store a scraped news article."""
        conn = get_warehouse_connection()
        try:
            entities_str = json.dumps(nlp_entities) if nlp_entities else None
            conn.execute(
                """INSERT OR IGNORE INTO raw_news_articles
                   (url, title, content_text, published_date, scraped_at, nlp_entities)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (url, title, content_text, published_date, datetime.utcnow().isoformat(), entities_str),
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_articles(self, limit: int = 50) -> List[Dict]:
        """Get recent news articles."""
        conn = get_warehouse_connection()
        try:
            rows = conn.execute(
                """SELECT * FROM raw_news_articles
                   ORDER BY scraped_at DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
