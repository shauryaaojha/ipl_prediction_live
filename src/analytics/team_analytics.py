"""Team Analytics Module.

Provides query functions for team-level statistics: win/loss records,
toss impact analysis, and head-to-head matchups.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import text

from ..storage.connection import get_engine


def get_team_record(team_id: UUID, season: Optional[int] = None) -> Dict[str, Any]:
    """Get team win/loss record from the materialized view.

    If season is provided, returns that season only; otherwise career aggregate.
    """
    engine = get_engine()

    if season:
        query = """
            SELECT team_code, team_name, matches_played, wins, losses, no_results,
                   win_percentage, tosses_won, toss_win_pct, bat_first_wins, chase_wins
            FROM mv_team_season_stats
            WHERE team_id = :tid AND season = :season
        """
        params = {"tid": team_id, "season": season}
    else:
        query = """
            SELECT team_code, team_name,
                   SUM(matches_played) AS matches_played,
                   SUM(wins) AS wins,
                   SUM(losses) AS losses,
                   SUM(no_results) AS no_results,
                   ROUND(SUM(wins)::NUMERIC * 100.0 / NULLIF(SUM(matches_played), 0), 1) AS win_percentage,
                   SUM(tosses_won) AS tosses_won,
                   ROUND(SUM(tosses_won)::NUMERIC * 100.0 / NULLIF(SUM(matches_played), 0), 1) AS toss_win_pct,
                   SUM(bat_first_wins) AS bat_first_wins,
                   SUM(chase_wins) AS chase_wins
            FROM mv_team_season_stats
            WHERE team_id = :tid
            GROUP BY team_code, team_name
        """
        params = {"tid": team_id}

    with engine.connect() as conn:
        row = conn.execute(text(query), params).fetchone()

    if not row:
        return {}

    return {
        "team_code": row[0],
        "team_name": row[1],
        "matches_played": row[2],
        "wins": row[3],
        "losses": row[4],
        "no_results": row[5],
        "win_percentage": float(row[6]) if row[6] else 0,
        "tosses_won": row[7],
        "toss_win_pct": float(row[8]) if row[8] else 0,
        "bat_first_wins": row[9],
        "chase_wins": row[10],
    }


def get_all_team_records(season: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get all teams' records, optionally filtered by season."""
    engine = get_engine()

    if season:
        query = """
            SELECT team_id, team_code, team_name, matches_played, wins, losses,
                   no_results, win_percentage, bat_first_wins, chase_wins
            FROM mv_team_season_stats
            WHERE season = :season
            ORDER BY win_percentage DESC
        """
        params = {"season": season}
    else:
        query = """
            SELECT team_id, team_code, team_name,
                   SUM(matches_played) AS matches_played,
                   SUM(wins) AS wins,
                   SUM(losses) AS losses,
                   SUM(no_results) AS no_results,
                   ROUND(SUM(wins)::NUMERIC * 100.0 / NULLIF(SUM(matches_played), 0), 1) AS win_percentage,
                   SUM(bat_first_wins) AS bat_first_wins,
                   SUM(chase_wins) AS chase_wins
            FROM mv_team_season_stats
            GROUP BY team_id, team_code, team_name
            ORDER BY win_percentage DESC
        """
        params = {}

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    return [
        {
            "team_id": str(r[0]), "team_code": r[1], "team_name": r[2],
            "played": r[3], "wins": r[4], "losses": r[5], "nr": r[6],
            "win_pct": float(r[7]) if r[7] else 0,
            "bat_first_wins": r[8], "chase_wins": r[9],
        }
        for r in rows
    ]


def get_toss_impact(team_id: UUID) -> Dict[str, Any]:
    """Analyze how toss decisions affect match outcomes for a team."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                COUNT(*) AS total_matches,
                SUM(CASE WHEN m.toss_winner_id = :tid THEN 1 ELSE 0 END) AS tosses_won,
                SUM(CASE WHEN m.toss_winner_id = :tid AND m.winner_id = :tid THEN 1 ELSE 0 END) AS toss_won_match_won,
                SUM(CASE WHEN m.toss_winner_id = :tid AND m.toss_decision = 'bat' THEN 1 ELSE 0 END) AS chose_bat,
                SUM(CASE WHEN m.toss_winner_id = :tid AND m.toss_decision = 'bat' AND m.winner_id = :tid THEN 1 ELSE 0 END) AS chose_bat_won,
                SUM(CASE WHEN m.toss_winner_id = :tid AND m.toss_decision = 'field' THEN 1 ELSE 0 END) AS chose_field,
                SUM(CASE WHEN m.toss_winner_id = :tid AND m.toss_decision = 'field' AND m.winner_id = :tid THEN 1 ELSE 0 END) AS chose_field_won,
                SUM(CASE WHEN m.toss_winner_id != :tid AND m.winner_id = :tid THEN 1 ELSE 0 END) AS toss_lost_match_won
            FROM matches m
            WHERE (m.team_a_id = :tid OR m.team_b_id = :tid)
              AND m.match_status = 'complete'
              AND m.winner_id IS NOT NULL
        """), {"tid": team_id}).fetchone()

    if not row or row[0] == 0:
        return {}

    return {
        "total_matches": row[0],
        "tosses_won": row[1],
        "toss_won_match_won": row[2],
        "toss_won_match_won_pct": round(row[2] * 100.0 / row[1], 1) if row[1] else 0,
        "chose_bat": row[3],
        "chose_bat_won": row[4],
        "chose_bat_win_pct": round(row[4] * 100.0 / row[3], 1) if row[3] else 0,
        "chose_field": row[5],
        "chose_field_won": row[6],
        "chose_field_win_pct": round(row[6] * 100.0 / row[5], 1) if row[5] else 0,
        "toss_lost_match_won": row[7],
        "toss_lost_win_pct": round(row[7] * 100.0 / (row[0] - row[1]), 1) if (row[0] - row[1]) else 0,
    }


def get_head_to_head(team_a_id: UUID, team_b_id: UUID) -> Dict[str, Any]:
    """Get head-to-head record between two teams."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                m.match_id,
                m.season,
                m.match_date,
                m.match_type,
                ta.team_code AS team_a_code,
                tb.team_code AS team_b_code,
                tw.team_code AS toss_winner_code,
                m.toss_decision,
                w.team_code AS winner_code,
                m.win_margin,
                m.win_type,
                v.venue_name
            FROM matches m
            JOIN teams ta ON m.team_a_id = ta.team_id
            JOIN teams tb ON m.team_b_id = tb.team_id
            LEFT JOIN teams tw ON m.toss_winner_id = tw.team_id
            LEFT JOIN teams w ON m.winner_id = w.team_id
            LEFT JOIN venues v ON m.venue_id = v.venue_id
            WHERE (
                (m.team_a_id = :ta AND m.team_b_id = :tb) OR
                (m.team_a_id = :tb AND m.team_b_id = :ta)
            )
            AND m.match_status = 'complete'
            ORDER BY m.match_date
        """), {"ta": team_a_id, "tb": team_b_id}).fetchall()

    # Get team codes for summary
    with engine.connect() as conn:
        team_a = conn.execute(text("SELECT team_code FROM teams WHERE team_id = :tid"), {"tid": team_a_id}).scalar()
        team_b = conn.execute(text("SELECT team_code FROM teams WHERE team_id = :tid"), {"tid": team_b_id}).scalar()

    total = len(rows)
    a_wins = sum(1 for r in rows if r[8] == team_a)
    b_wins = sum(1 for r in rows if r[8] == team_b)
    no_results = total - a_wins - b_wins

    matches_list = [
        {
            "season": r[1], "date": str(r[2]), "type": r[3],
            "team_a": r[4], "team_b": r[5],
            "toss_winner": r[6], "toss_decision": r[7],
            "winner": r[8], "margin": r[9], "win_type": r[10],
            "venue": r[11],
        }
        for r in rows
    ]

    return {
        "team_a": team_a,
        "team_b": team_b,
        "total_matches": total,
        "team_a_wins": a_wins,
        "team_b_wins": b_wins,
        "no_results": no_results,
        "matches": matches_list,
    }
