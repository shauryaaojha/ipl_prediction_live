"""Bowling Analytics Module.

Provides query functions for bowling statistics using the raw deliveries
table and materialized views.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import text

from ..storage.connection import get_engine


def get_career_stats(bowler_id: UUID) -> Optional[Dict[str, Any]]:
    """Get full career bowling stats from the materialized view."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT full_name, matches, innings, overs_bowled, runs_conceded,
                   wickets, dot_balls, boundaries_conceded,
                   economy_rate, bowling_average, bowling_strike_rate, dot_ball_percentage
            FROM mv_bowling_career_stats
            WHERE bowler_id = :bid
        """), {"bid": bowler_id}).fetchone()

    if not row:
        return None

    return {
        "player_id": str(bowler_id),
        "full_name": row[0],
        "matches": row[1],
        "innings": row[2],
        "overs_bowled": float(row[3]) if row[3] else 0,
        "runs_conceded": row[4],
        "wickets": row[5],
        "dot_balls": row[6],
        "boundaries_conceded": row[7],
        "economy_rate": float(row[8]) if row[8] else None,
        "bowling_average": float(row[9]) if row[9] else None,
        "bowling_strike_rate": float(row[10]) if row[10] else None,
        "dot_ball_percentage": float(row[11]) if row[11] else 0,
    }


def get_season_stats(bowler_id: UUID, season: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get season-wise bowling stats."""
    engine = get_engine()
    query = """
        SELECT season, matches, innings, overs_bowled, runs_conceded,
               wickets, dot_balls, economy_rate, bowling_average
        FROM mv_bowling_season_stats
        WHERE bowler_id = :bid
    """
    params: Dict[str, Any] = {"bid": bowler_id}
    if season:
        query += " AND season = :season"
        params["season"] = season
    query += " ORDER BY season"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    return [
        {
            "season": r[0], "matches": r[1], "innings": r[2],
            "overs": float(r[3]) if r[3] else 0,
            "runs_conceded": r[4], "wickets": r[5], "dots": r[6],
            "economy": float(r[7]) if r[7] else None,
            "average": float(r[8]) if r[8] else None,
        }
        for r in rows
    ]


def get_vs_batter(bowler_id: UUID, batsman_id: UUID) -> Dict[str, Any]:
    """Get head-to-head bowling stats against a specific batter."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                COUNT(DISTINCT match_id) AS matches,
                SUM(total_runs) AS runs_conceded,
                SUM(CASE WHEN extras_type IS NULL OR extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END) AS balls,
                SUM(CASE WHEN is_wicket = TRUE
                          AND wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
                          AND player_dismissed_id = :bat_id
                     THEN 1 ELSE 0 END) AS wickets,
                SUM(CASE WHEN batsman_runs = 0 AND extra_runs = 0 THEN 1 ELSE 0 END) AS dots,
                SUM(CASE WHEN batsman_runs IN (4, 6) THEN 1 ELSE 0 END) AS boundaries
            FROM deliveries
            WHERE bowler_id = :bowl_id AND batsman_id = :bat_id
        """), {"bowl_id": bowler_id, "bat_id": batsman_id}).fetchone()

    if not row or row[2] == 0:
        return {"matches": 0, "runs": 0, "balls": 0, "wickets": 0}

    return {
        "matches": row[0],
        "runs_conceded": row[1],
        "balls": row[2],
        "wickets": row[3],
        "dot_balls": row[4],
        "boundaries": row[5],
        "economy": round(row[1] * 6.0 / row[2], 2) if row[2] else 0,
        "strike_rate": round(row[2] / row[3], 1) if row[3] else None,
    }


def get_phase_stats(bowler_id: UUID, phase: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get bowling stats by match phase (powerplay/middle/death)."""
    engine = get_engine()
    query = """
        SELECT
            match_phase,
            SUM(total_runs) AS runs,
            SUM(CASE WHEN is_legal THEN 1 ELSE 0 END) AS balls,
            SUM(CASE WHEN is_wicket = TRUE
                      AND wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
                 THEN 1 ELSE 0 END) AS wickets,
            SUM(CASE WHEN is_dot THEN 1 ELSE 0 END) AS dots,
            SUM(CASE WHEN is_four THEN 1 ELSE 0 END) AS fours,
            SUM(CASE WHEN is_six THEN 1 ELSE 0 END) AS sixes
        FROM fact_deliveries
        WHERE bowler_id = :bid
    """
    params: Dict[str, Any] = {"bid": bowler_id}
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
            "wickets": r[3],
            "dots": r[4],
            "fours": r[5],
            "sixes": r[6],
            "economy": round(r[1] * 6.0 / r[2], 2) if r[2] else 0,
            "dot_pct": round(r[4] * 100.0 / r[2], 1) if r[2] else 0,
        }
        for r in rows
    ]


def get_death_specialist_ranking(
    season: Optional[int] = None,
    min_overs: float = 10.0,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Rank bowlers by death overs (overs 16-20) economy rate.

    Only includes bowlers with a minimum number of death overs bowled.
    """
    engine = get_engine()
    query = """
        SELECT
            fd.bowler_id,
            p.full_name,
            SUM(CASE WHEN fd.is_legal THEN 1 ELSE 0 END) AS balls,
            ROUND(SUM(CASE WHEN fd.is_legal THEN 1 ELSE 0 END)::NUMERIC / 6, 1) AS overs,
            SUM(fd.total_runs) AS runs,
            SUM(CASE WHEN fd.is_wicket = TRUE
                      AND fd.wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
                 THEN 1 ELSE 0 END) AS wickets,
            SUM(CASE WHEN fd.is_dot THEN 1 ELSE 0 END) AS dots,
            ROUND(
                SUM(fd.total_runs)::NUMERIC * 6.0 /
                NULLIF(SUM(CASE WHEN fd.is_legal THEN 1 ELSE 0 END), 0),
                2
            ) AS economy
        FROM fact_deliveries fd
        JOIN players p ON fd.bowler_id = p.player_id
        WHERE fd.match_phase = 'death'
          AND fd.bowler_id IS NOT NULL
    """
    params: Dict[str, Any] = {}
    if season:
        query += " AND fd.season = :season"
        params["season"] = season

    query += """
        GROUP BY fd.bowler_id, p.full_name
        HAVING SUM(CASE WHEN fd.is_legal THEN 1 ELSE 0 END)::NUMERIC / 6 >= :min_overs
        ORDER BY economy ASC
        LIMIT :limit
    """
    params["min_overs"] = min_overs
    params["limit"] = limit

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    return [
        {
            "player_id": str(r[0]), "player": r[1], "balls": r[2],
            "overs": float(r[3]), "runs": r[4], "wickets": r[5],
            "dots": r[6], "economy": float(r[7]),
        }
        for r in rows
    ]
