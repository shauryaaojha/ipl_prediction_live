"""Batting Analytics Module.

Provides query functions for batting statistics using the raw deliveries
table and materialized views. Designed to power FastAPI endpoints and
dashboard components.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import text

from ..storage.connection import get_engine


def get_career_stats(player_id: UUID) -> Optional[Dict[str, Any]]:
    """Get full career batting stats for a player from the materialized view."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT full_name, matches, innings, total_runs, balls_faced,
                   highest_score, fours, sixes, dot_balls, dismissals,
                   strike_rate, batting_average, boundary_percentage
            FROM mv_batting_career_stats
            WHERE batsman_id = :pid
        """), {"pid": player_id}).fetchone()

    if not row:
        return None

    return {
        "player_id": str(player_id),
        "full_name": row[0],
        "matches": row[1],
        "innings": row[2],
        "total_runs": row[3],
        "balls_faced": row[4],
        "highest_score": row[5],
        "fours": row[6],
        "sixes": row[7],
        "dot_balls": row[8],
        "dismissals": row[9],
        "not_outs": row[2] - row[9] if row[2] and row[9] else 0,
        "strike_rate": float(row[10]) if row[10] else 0,
        "batting_average": float(row[11]) if row[11] else None,
        "boundary_percentage": float(row[12]) if row[12] else 0,
    }


def get_season_stats(player_id: UUID, season: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get season-wise batting stats for a player."""
    engine = get_engine()
    query = """
        SELECT season, matches, innings, total_runs, balls_faced,
               fours, sixes, dismissals, strike_rate, batting_average
        FROM mv_batting_season_stats
        WHERE batsman_id = :pid
    """
    params: Dict[str, Any] = {"pid": player_id}
    if season:
        query += " AND season = :season"
        params["season"] = season
    query += " ORDER BY season"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    return [
        {
            "season": r[0], "matches": r[1], "innings": r[2],
            "runs": r[3], "balls_faced": r[4], "fours": r[5], "sixes": r[6],
            "dismissals": r[7],
            "strike_rate": float(r[8]) if r[8] else 0,
            "average": float(r[9]) if r[9] else None,
        }
        for r in rows
    ]


def get_vs_bowler(batsman_id: UUID, bowler_id: UUID) -> Dict[str, Any]:
    """Get head-to-head batting stats against a specific bowler.

    Computed live from the deliveries table (not materialized).
    """
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                COUNT(DISTINCT match_id) AS matches,
                SUM(batsman_runs) AS runs,
                SUM(CASE WHEN extras_type IS NULL OR extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END) AS balls,
                SUM(CASE WHEN batsman_runs = 4 THEN 1 ELSE 0 END) AS fours,
                SUM(CASE WHEN batsman_runs = 6 THEN 1 ELSE 0 END) AS sixes,
                SUM(CASE WHEN is_wicket = TRUE AND player_dismissed_id = batsman_id THEN 1 ELSE 0 END) AS dismissals,
                SUM(CASE WHEN batsman_runs = 0 AND extra_runs = 0 THEN 1 ELSE 0 END) AS dots
            FROM deliveries
            WHERE batsman_id = :bat_id AND bowler_id = :bowl_id
        """), {"bat_id": batsman_id, "bowl_id": bowler_id}).fetchone()

    if not row or row[2] == 0:
        return {"matches": 0, "runs": 0, "balls": 0, "dismissals": 0}

    return {
        "matches": row[0],
        "runs": row[1],
        "balls": row[2],
        "fours": row[3],
        "sixes": row[4],
        "dismissals": row[5],
        "dot_balls": row[6],
        "strike_rate": round(row[1] * 100.0 / row[2], 2) if row[2] else 0,
    }


def get_phase_stats(player_id: UUID, phase: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get batting stats by match phase (powerplay/middle/death).

    Uses the fact_deliveries view for automatic phase classification.
    """
    engine = get_engine()
    query = """
        SELECT
            match_phase,
            SUM(batsman_runs) AS runs,
            SUM(CASE WHEN is_legal THEN 1 ELSE 0 END) AS balls,
            SUM(CASE WHEN is_four THEN 1 ELSE 0 END) AS fours,
            SUM(CASE WHEN is_six THEN 1 ELSE 0 END) AS sixes,
            SUM(CASE WHEN is_dot THEN 1 ELSE 0 END) AS dots,
            SUM(CASE WHEN is_wicket = TRUE AND player_dismissed_id = batsman_id THEN 1 ELSE 0 END) AS dismissals
        FROM fact_deliveries
        WHERE batsman_id = :pid
    """
    params: Dict[str, Any] = {"pid": player_id}
    if phase:
        query += " AND match_phase = :phase"
        params["phase"] = phase
    query += " GROUP BY match_phase ORDER BY match_phase"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    return [
        {
            "phase": r[0],
            "runs": r[1],
            "balls": r[2],
            "fours": r[3],
            "sixes": r[4],
            "dots": r[5],
            "dismissals": r[6],
            "strike_rate": round(r[1] * 100.0 / r[2], 2) if r[2] else 0,
        }
        for r in rows
    ]


def get_venue_stats(player_id: UUID) -> List[Dict[str, Any]]:
    """Get batting stats per venue for a player."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                v.venue_name,
                v.city,
                COUNT(DISTINCT fd.match_id) AS matches,
                SUM(fd.batsman_runs) AS runs,
                SUM(CASE WHEN fd.is_legal THEN 1 ELSE 0 END) AS balls,
                SUM(CASE WHEN fd.is_four THEN 1 ELSE 0 END) AS fours,
                SUM(CASE WHEN fd.is_six THEN 1 ELSE 0 END) AS sixes,
                SUM(CASE WHEN fd.is_wicket = TRUE AND fd.player_dismissed_id = fd.batsman_id THEN 1 ELSE 0 END) AS dismissals
            FROM fact_deliveries fd
            JOIN venues v ON fd.venue_id = v.venue_id
            WHERE fd.batsman_id = :pid
            GROUP BY v.venue_name, v.city
            ORDER BY runs DESC
        """), {"pid": player_id}).fetchall()

    return [
        {
            "venue": r[0], "city": r[1], "matches": r[2],
            "runs": r[3], "balls": r[4], "fours": r[5], "sixes": r[6],
            "dismissals": r[7],
            "strike_rate": round(r[3] * 100.0 / r[4], 2) if r[4] else 0,
        }
        for r in rows
    ]


def get_form_index(player_id: UUID, last_n: int = 10) -> Dict[str, Any]:
    """Calculate recent form index based on last N innings.

    Form index is a weighted combination of strike rate and average
    over the last N innings compared to career averages.
    """
    engine = get_engine()
    with engine.connect() as conn:
        # Get last N innings
        rows = conn.execute(text("""
            WITH innings_data AS (
                SELECT
                    m.match_date,
                    m.season,
                    d.match_id,
                    d.innings,
                    SUM(d.batsman_runs) AS runs,
                    SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END) AS balls,
                    MAX(CASE WHEN d.is_wicket = TRUE AND d.player_dismissed_id = d.batsman_id THEN 1 ELSE 0 END) AS dismissed
                FROM deliveries d
                JOIN matches m ON d.match_id = m.match_id
                WHERE d.batsman_id = :pid
                GROUP BY m.match_date, m.season, d.match_id, d.innings
                ORDER BY m.match_date DESC
                LIMIT :n
            )
            SELECT
                COUNT(*) AS innings,
                SUM(runs) AS total_runs,
                SUM(balls) AS total_balls,
                SUM(dismissed) AS dismissals,
                AVG(runs) AS avg_runs_per_innings
            FROM innings_data
        """), {"pid": player_id, "n": last_n}).fetchone()

    if not rows or rows[0] == 0:
        return {"innings": 0, "form_index": 0}

    innings = rows[0]
    total_runs = rows[1] or 0
    total_balls = rows[2] or 0
    dismissals = rows[3] or 0
    avg_runs = float(rows[4]) if rows[4] else 0

    recent_sr = (total_runs * 100.0 / total_balls) if total_balls > 0 else 0
    recent_avg = (total_runs / dismissals) if dismissals > 0 else total_runs

    # Form index: normalized score (0-100) combining SR and average
    # Higher is better. Baseline IPL SR ~130, Avg ~25
    sr_score = min(recent_sr / 1.3, 100)  # Normalize against ~130 SR
    avg_score = min(recent_avg / 0.4, 100)  # Normalize against ~40 avg
    form_index = round((sr_score * 0.5 + avg_score * 0.5), 1)

    return {
        "innings": innings,
        "recent_runs": total_runs,
        "recent_balls": total_balls,
        "recent_dismissals": dismissals,
        "recent_strike_rate": round(recent_sr, 2),
        "recent_average": round(recent_avg, 2),
        "avg_runs_per_innings": round(avg_runs, 2),
        "form_index": form_index,
    }
