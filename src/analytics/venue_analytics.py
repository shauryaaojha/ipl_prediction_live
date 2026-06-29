"""Venue Analytics Module.

Provides query functions for venue-level statistics: scoring profiles,
chase success rates, and season-over-season trends.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import text

from ..storage.connection import get_engine


def get_venue_profile(venue_id: UUID) -> Optional[Dict[str, Any]]:
    """Get comprehensive venue profile from the materialized view."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT venue_name, city, total_matches,
                   avg_first_innings_score, avg_second_innings_score,
                   avg_boundaries_first, avg_wickets_first,
                   chase_success_pct, bat_first_win_pct, field_first_win_pct
            FROM mv_venue_stats
            WHERE venue_id = :vid
        """), {"vid": venue_id}).fetchone()

    if not row:
        return None

    return {
        "venue_id": str(venue_id),
        "venue_name": row[0],
        "city": row[1],
        "total_matches": row[2],
        "avg_first_innings_score": float(row[3]) if row[3] else 0,
        "avg_second_innings_score": float(row[4]) if row[4] else 0,
        "avg_boundaries_per_innings": float(row[5]) if row[5] else 0,
        "avg_wickets_per_innings": float(row[6]) if row[6] else 0,
        "chase_success_pct": float(row[7]) if row[7] else 0,
        "bat_first_win_pct": float(row[8]) if row[8] else 0,
        "field_first_win_pct": float(row[9]) if row[9] else 0,
    }


def get_all_venues() -> List[Dict[str, Any]]:
    """Get all venue profiles sorted by number of matches."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT venue_id, venue_name, city, total_matches,
                   avg_first_innings_score, avg_second_innings_score,
                   chase_success_pct
            FROM mv_venue_stats
            ORDER BY total_matches DESC
        """)).fetchall()

    return [
        {
            "venue_id": str(r[0]), "venue": r[1], "city": r[2],
            "matches": r[3],
            "avg_1st": float(r[4]) if r[4] else 0,
            "avg_2nd": float(r[5]) if r[5] else 0,
            "chase_pct": float(r[6]) if r[6] else 0,
        }
        for r in rows
    ]


def get_venue_trend(venue_id: UUID) -> List[Dict[str, Any]]:
    """Get season-over-season scoring trends for a venue."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            WITH season_innings AS (
                SELECT
                    m.season,
                    d.innings,
                    m.match_id,
                    SUM(d.total_runs) AS total_runs,
                    SUM(CASE WHEN d.batsman_runs IN (4, 6) THEN 1 ELSE 0 END) AS boundaries,
                    SUM(CASE WHEN d.is_wicket = TRUE THEN 1 ELSE 0 END) AS wickets
                FROM deliveries d
                JOIN matches m ON d.match_id = m.match_id
                WHERE m.venue_id = :vid
                GROUP BY m.season, d.innings, m.match_id
            )
            SELECT
                season,
                COUNT(DISTINCT match_id) AS matches,
                ROUND(AVG(CASE WHEN innings = 1 THEN total_runs END), 1) AS avg_1st_score,
                ROUND(AVG(CASE WHEN innings = 2 THEN total_runs END), 1) AS avg_2nd_score,
                ROUND(AVG(boundaries), 1) AS avg_boundaries,
                ROUND(AVG(wickets), 1) AS avg_wickets
            FROM season_innings
            GROUP BY season
            ORDER BY season
        """), {"vid": venue_id}).fetchall()

    return [
        {
            "season": r[0], "matches": r[1],
            "avg_1st_score": float(r[2]) if r[2] else 0,
            "avg_2nd_score": float(r[3]) if r[3] else 0,
            "avg_boundaries": float(r[4]) if r[4] else 0,
            "avg_wickets": float(r[5]) if r[5] else 0,
        }
        for r in rows
    ]


def get_venue_phase_breakdown(venue_id: UUID) -> List[Dict[str, Any]]:
    """Get powerplay/middle/death overs breakdown for a venue."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                fd.match_phase,
                COUNT(DISTINCT fd.match_id) AS matches,
                SUM(fd.total_runs) AS total_runs,
                SUM(CASE WHEN fd.is_legal THEN 1 ELSE 0 END) AS balls,
                SUM(CASE WHEN fd.is_four THEN 1 ELSE 0 END) AS fours,
                SUM(CASE WHEN fd.is_six THEN 1 ELSE 0 END) AS sixes,
                SUM(CASE WHEN fd.is_wicket THEN 1 ELSE 0 END) AS wickets,
                SUM(CASE WHEN fd.is_dot THEN 1 ELSE 0 END) AS dots
            FROM fact_deliveries fd
            WHERE fd.venue_id = :vid
            GROUP BY fd.match_phase
            ORDER BY
                CASE fd.match_phase
                    WHEN 'powerplay' THEN 1
                    WHEN 'middle' THEN 2
                    WHEN 'death' THEN 3
                    ELSE 4
                END
        """), {"vid": venue_id}).fetchall()

    return [
        {
            "phase": r[0], "matches": r[1],
            "total_runs": r[2], "balls": r[3],
            "fours": r[4], "sixes": r[5],
            "wickets": r[6], "dots": r[7],
            "run_rate": round(r[2] * 6.0 / r[3], 2) if r[3] else 0,
            "boundary_pct": round((r[4] + r[5]) * 100.0 / r[3], 1) if r[3] else 0,
        }
        for r in rows
    ]
