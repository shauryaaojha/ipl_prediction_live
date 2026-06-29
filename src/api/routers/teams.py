"""Teams router — list, profile, seasons, toss impact, head-to-head."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from ..deps import get_db_engine
from ..schemas import (
    HeadToHeadResponse,
    TeamRecordResponse,
    TeamResponse,
    TeamSeasonResponse,
    TossImpactResponse,
)
from ...analytics import team_analytics

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=list[TeamResponse])
def list_teams():
    """List all IPL teams."""
    engine = get_db_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT t.team_id, t.team_code, t.team_name, t.founded_year,
                   v.venue_name
            FROM teams t
            LEFT JOIN venues v ON t.home_venue_id = v.venue_id
            ORDER BY t.team_name
        """)).fetchall()

    return [
        TeamResponse(
            team_id=r[0], team_code=r[1], team_name=r[2],
            founded_year=r[3], home_venue=r[4],
        )
        for r in rows
    ]


@router.get("/head-to-head", response_model=HeadToHeadResponse)
def head_to_head(
    team_a: UUID = Query(..., description="Team A ID"),
    team_b: UUID = Query(..., description="Team B ID"),
):
    """Get head-to-head record between two teams."""
    result = team_analytics.get_head_to_head(team_a, team_b)
    if not result:
        raise HTTPException(status_code=404, detail="No matches found between these teams")
    return HeadToHeadResponse(**result)


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(team_id: UUID):
    """Get a single team profile."""
    engine = get_db_engine()
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT t.team_id, t.team_code, t.team_name, t.founded_year,
                   v.venue_name
            FROM teams t
            LEFT JOIN venues v ON t.home_venue_id = v.venue_id
            WHERE t.team_id = :tid
        """), {"tid": team_id}).fetchone()

    if not r:
        raise HTTPException(status_code=404, detail="Team not found")

    return TeamResponse(
        team_id=r[0], team_code=r[1], team_name=r[2],
        founded_year=r[3], home_venue=r[4],
    )


@router.get("/{team_id}/record", response_model=TeamRecordResponse)
def get_team_record(
    team_id: UUID,
    season: Optional[int] = Query(None, ge=2008, le=2030),
):
    """Get team win/loss record. Optionally filter by season."""
    result = team_analytics.get_team_record(team_id, season)
    if not result:
        raise HTTPException(status_code=404, detail="No records found")
    return TeamRecordResponse(**result)


@router.get("/{team_id}/seasons", response_model=list[TeamSeasonResponse])
def get_team_seasons(team_id: UUID):
    """Get all season-wise standings for a team."""
    engine = get_db_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT team_id, team_code, team_name, matches_played, wins, losses,
                   no_results, win_percentage, bat_first_wins, chase_wins, season
            FROM mv_team_season_stats
            WHERE team_id = :tid
            ORDER BY season
        """), {"tid": team_id}).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No season data found")

    return [
        TeamSeasonResponse(
            team_id=str(r[0]), team_code=r[1], team_name=r[2],
            played=r[3], wins=r[4], losses=r[5], nr=r[6],
            win_pct=float(r[7]) if r[7] else 0,
            bat_first_wins=r[8], chase_wins=r[9],
        )
        for r in rows
    ]


@router.get("/{team_id}/toss", response_model=TossImpactResponse)
def get_toss_impact(team_id: UUID):
    """Analyze toss impact for a team."""
    result = team_analytics.get_toss_impact(team_id)
    if not result:
        raise HTTPException(status_code=404, detail="No toss data found")
    return TossImpactResponse(**result)
