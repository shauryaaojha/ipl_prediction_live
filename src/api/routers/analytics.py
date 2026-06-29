"""Analytics leaderboard router — batting leaders, bowling leaders, death specialists."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import text

from ..deps import cached, get_db_engine
from ..schemas import BattingLeaderEntry, BowlingLeaderEntry, DeathSpecialistEntry
from ...analytics import bowling as bowling_analytics

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/batting/leaders", response_model=list[BattingLeaderEntry])
def batting_leaders(
    season: Optional[int] = Query(None, ge=2008, le=2030, description="Filter by season"),
    limit: int = Query(25, ge=1, le=100),
):
    """Get top run scorers (career or season)."""
    return _get_batting_leaders(season, limit)


@cached(ttl=300)
def _get_batting_leaders(season: Optional[int], limit: int) -> list[dict]:
    engine = get_db_engine()

    if season:
        query = """
            SELECT batsman_id, full_name, total_runs, matches, innings,
                   strike_rate, batting_average, fours, sixes
            FROM mv_batting_season_stats
            WHERE season = :season
            ORDER BY total_runs DESC
            LIMIT :limit
        """
        params = {"season": season, "limit": limit}
    else:
        query = """
            SELECT batsman_id, full_name, total_runs, matches, innings,
                   strike_rate, batting_average, fours, sixes
            FROM mv_batting_career_stats
            ORDER BY total_runs DESC
            LIMIT :limit
        """
        params = {"limit": limit}

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    return [
        BattingLeaderEntry(
            rank=i,
            player_id=str(r[0]) if r[0] else None,
            player=r[1],
            runs=r[2], matches=r[3], innings=r[4],
            strike_rate=float(r[5]) if r[5] else 0,
            average=float(r[6]) if r[6] else None,
            fours=r[7], sixes=r[8],
        )
        for i, r in enumerate(rows, 1)
    ]


@router.get("/bowling/leaders", response_model=list[BowlingLeaderEntry])
def bowling_leaders(
    season: Optional[int] = Query(None, ge=2008, le=2030),
    limit: int = Query(25, ge=1, le=100),
):
    """Get top wicket takers (career or season)."""
    return _get_bowling_leaders(season, limit)


@cached(ttl=300)
def _get_bowling_leaders(season: Optional[int], limit: int) -> list[dict]:
    engine = get_db_engine()

    if season:
        query = """
            SELECT bowler_id, full_name, wickets, matches, overs_bowled,
                   economy_rate, bowling_average, innings
            FROM mv_bowling_season_stats
            WHERE season = :season
            ORDER BY wickets DESC
            LIMIT :limit
        """
        params = {"season": season, "limit": limit}
    else:
        query = """
            SELECT bowler_id, full_name, wickets, matches, overs_bowled,
                   economy_rate, bowling_average, bowling_strike_rate
            FROM mv_bowling_career_stats
            ORDER BY wickets DESC
            LIMIT :limit
        """
        params = {"limit": limit}

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    return [
        BowlingLeaderEntry(
            rank=i,
            player_id=str(r[0]) if r[0] else None,
            player=r[1],
            wickets=r[2], matches=r[3],
            overs=float(r[4]) if r[4] else 0,
            economy=float(r[5]) if r[5] else 0,
            average=float(r[6]) if r[6] else None,
            strike_rate=float(r[7]) if r[7] else None,
        )
        for i, r in enumerate(rows, 1)
    ]


@router.get("/bowling/death-specialists", response_model=list[DeathSpecialistEntry])
def death_specialists(
    season: Optional[int] = Query(None, ge=2008, le=2030),
    min_overs: float = Query(10.0, ge=1.0),
    limit: int = Query(20, ge=1, le=100),
):
    """Rank bowlers by death overs (16-20) economy rate."""
    results = bowling_analytics.get_death_specialist_ranking(season, min_overs, limit)
    return [
        DeathSpecialistEntry(rank=i, **r)
        for i, r in enumerate(results, 1)
    ]
