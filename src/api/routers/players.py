"""Players router — list, profile, batting, bowling, seasons, matchups, form."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from ..deps import PaginationParams, get_db_engine
from ..schemas import (
    BattingStatsResponse,
    BowlingStatsResponse,
    FormResponse,
    MatchupResponse,
    PaginatedResponse,
    PaginationMeta,
    PlayerResponse,
    SeasonStatsResponse,
)
from ...analytics import batting as batting_analytics
from ...analytics import bowling as bowling_analytics

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("", response_model=PaginatedResponse[PlayerResponse])
def list_players(
    pagination: PaginationParams = Depends(),
    q: Optional[str] = Query(None, description="Search by player name"),
    role: Optional[str] = Query(None, description="Filter by role"),
    nationality: Optional[str] = Query(None, description="Filter by nationality"),
):
    """List players with pagination and optional search."""
    engine = get_db_engine()

    conditions = []
    params: dict = {}
    if q:
        conditions.append("p.full_name ILIKE :q")
        params["q"] = f"%{q}%"
    if role:
        conditions.append("p.role = :role")
        params["role"] = role
    if nationality:
        conditions.append("p.nationality = :nat")
        params["nat"] = nationality

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with engine.connect() as conn:
        total = conn.execute(
            text(f"SELECT COUNT(*) FROM players p {where_clause}"), params
        ).scalar()

        params["limit"] = pagination.per_page
        params["offset"] = pagination.offset
        rows = conn.execute(text(f"""
            SELECT player_id, full_name, short_name, batting_hand,
                   bowling_arm, bowling_type, role, nationality, date_of_birth
            FROM players p
            {where_clause}
            ORDER BY full_name
            LIMIT :limit OFFSET :offset
        """), params).fetchall()

    players = [
        PlayerResponse(
            player_id=r[0], full_name=r[1], short_name=r[2],
            batting_hand=r[3], bowling_arm=r[4], bowling_type=r[5],
            role=r[6], nationality=r[7], date_of_birth=r[8],
        )
        for r in rows
    ]

    return PaginatedResponse(data=players, pagination=PaginationMeta(**pagination.meta(total)))


@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(player_id: UUID):
    """Get a single player profile."""
    engine = get_db_engine()
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT player_id, full_name, short_name, batting_hand,
                   bowling_arm, bowling_type, role, nationality, date_of_birth
            FROM players WHERE player_id = :pid
        """), {"pid": player_id}).fetchone()

    if not r:
        raise HTTPException(status_code=404, detail="Player not found")

    return PlayerResponse(
        player_id=r[0], full_name=r[1], short_name=r[2],
        batting_hand=r[3], bowling_arm=r[4], bowling_type=r[5],
        role=r[6], nationality=r[7], date_of_birth=r[8],
    )


@router.get("/{player_id}/batting", response_model=BattingStatsResponse)
def get_batting_stats(player_id: UUID):
    """Get career batting stats from materialized view."""
    stats = batting_analytics.get_career_stats(player_id)
    if not stats:
        raise HTTPException(status_code=404, detail="No batting stats found")
    return BattingStatsResponse(**stats)


@router.get("/{player_id}/bowling", response_model=BowlingStatsResponse)
def get_bowling_stats(player_id: UUID):
    """Get career bowling stats from materialized view."""
    stats = bowling_analytics.get_career_stats(player_id)
    if not stats:
        raise HTTPException(status_code=404, detail="No bowling stats found")
    return BowlingStatsResponse(**stats)


@router.get("/{player_id}/seasons", response_model=list[SeasonStatsResponse])
def get_season_stats(
    player_id: UUID,
    season: Optional[int] = Query(None, ge=2008, le=2030),
):
    """Get season-by-season batting breakdown."""
    stats = batting_analytics.get_season_stats(player_id, season)
    return [SeasonStatsResponse(**s) for s in stats]


@router.get("/{player_id}/matchups", response_model=MatchupResponse)
def get_matchup(
    player_id: UUID,
    vs_player_id: UUID = Query(..., description="Opponent player ID for head-to-head"),
):
    """Get head-to-head batting stats against a specific bowler."""
    stats = batting_analytics.get_vs_bowler(player_id, vs_player_id)
    return MatchupResponse(**stats)


@router.get("/{player_id}/form", response_model=FormResponse)
def get_form(
    player_id: UUID,
    last_n: int = Query(10, ge=1, le=50, description="Number of recent innings"),
):
    """Get recent form index for a player."""
    stats = batting_analytics.get_form_index(player_id, last_n)
    return FormResponse(**stats)
