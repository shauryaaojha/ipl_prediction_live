"""Matches router — list, detail, scorecard, deliveries."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from ..deps import PaginationParams, get_db_engine
from ..schemas import (
    DeliveryResponse,
    InningsScorecard,
    MatchResponse,
    PaginatedResponse,
    PaginationMeta,
    ScorecardBatting,
    ScorecardBowling,
    TeamBrief,
    VenueBrief,
)

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.get("", response_model=PaginatedResponse[MatchResponse])
def list_matches(
    pagination: PaginationParams = Depends(),
    season: Optional[int] = Query(None, ge=2008, le=2030),
    team: Optional[str] = Query(None, description="Team code filter"),
    status: Optional[str] = Query(None, description="Match status filter"),
    sort: str = Query("match_date", description="Sort field"),
    order: str = Query("desc", description="Sort order: asc or desc"),
):
    """List matches with pagination and filtering."""
    engine = get_db_engine()

    # Build WHERE clauses
    conditions = []
    params: dict = {}
    if season:
        conditions.append("m.season = :season")
        params["season"] = season
    if team:
        conditions.append(
            "(ta.team_code = :team OR tb.team_code = :team)"
        )
        params["team"] = team
    if status:
        conditions.append("m.match_status = :status")
        params["status"] = status

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Allowed sort columns
    sort_map = {
        "match_date": "m.match_date",
        "season": "m.season",
        "match_number": "m.match_number",
    }
    sort_col = sort_map.get(sort, "m.match_date")
    order_dir = "DESC" if order.lower() == "desc" else "ASC"

    with engine.connect() as conn:
        # Count
        count_sql = f"""
            SELECT COUNT(*) FROM matches m
            LEFT JOIN teams ta ON m.team_a_id = ta.team_id
            LEFT JOIN teams tb ON m.team_b_id = tb.team_id
            {where_clause}
        """
        total = conn.execute(text(count_sql), params).scalar()

        # Data
        data_sql = f"""
            SELECT
                m.match_id, m.season, m.match_number, m.match_date,
                m.match_type, m.match_status,
                m.venue_id, v.venue_name, v.city,
                m.team_a_id, ta.team_code AS ta_code, ta.team_name AS ta_name,
                m.team_b_id, tb.team_code AS tb_code, tb.team_name AS tb_name,
                m.toss_winner_id, tw.team_code AS tw_code, tw.team_name AS tw_name,
                m.toss_decision,
                m.winner_id, w.team_code AS w_code, w.team_name AS w_name,
                m.win_margin, m.win_type, m.dl_applied, m.source
            FROM matches m
            LEFT JOIN venues v ON m.venue_id = v.venue_id
            LEFT JOIN teams ta ON m.team_a_id = ta.team_id
            LEFT JOIN teams tb ON m.team_b_id = tb.team_id
            LEFT JOIN teams tw ON m.toss_winner_id = tw.team_id
            LEFT JOIN teams w ON m.winner_id = w.team_id
            {where_clause}
            ORDER BY {sort_col} {order_dir}
            LIMIT :limit OFFSET :offset
        """
        params["limit"] = pagination.per_page
        params["offset"] = pagination.offset
        rows = conn.execute(text(data_sql), params).fetchall()

    matches = []
    for r in rows:
        matches.append(MatchResponse(
            match_id=r[0], season=r[1], match_number=r[2], match_date=r[3],
            match_type=r[4], match_status=r[5],
            venue=VenueBrief(venue_id=r[6], venue_name=r[7], city=r[8]) if r[6] else None,
            team_a=TeamBrief(team_id=r[9], team_code=r[10], team_name=r[11]) if r[9] else None,
            team_b=TeamBrief(team_id=r[12], team_code=r[13], team_name=r[14]) if r[12] else None,
            toss_winner=TeamBrief(team_id=r[15], team_code=r[16], team_name=r[17]) if r[15] else None,
            toss_decision=r[18],
            winner=TeamBrief(team_id=r[19], team_code=r[20], team_name=r[21]) if r[19] else None,
            win_margin=r[22], win_type=r[23], dl_applied=r[24] or False, source=r[25],
        ))

    return PaginatedResponse(data=matches, pagination=PaginationMeta(**pagination.meta(total)))


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(match_id: UUID):
    """Get a single match by ID."""
    engine = get_db_engine()
    with engine.connect() as conn:
        r = conn.execute(text("""
            SELECT
                m.match_id, m.season, m.match_number, m.match_date,
                m.match_type, m.match_status,
                m.venue_id, v.venue_name, v.city,
                m.team_a_id, ta.team_code, ta.team_name,
                m.team_b_id, tb.team_code, tb.team_name,
                m.toss_winner_id, tw.team_code, tw.team_name,
                m.toss_decision,
                m.winner_id, w.team_code, w.team_name,
                m.win_margin, m.win_type, m.dl_applied, m.source
            FROM matches m
            LEFT JOIN venues v ON m.venue_id = v.venue_id
            LEFT JOIN teams ta ON m.team_a_id = ta.team_id
            LEFT JOIN teams tb ON m.team_b_id = tb.team_id
            LEFT JOIN teams tw ON m.toss_winner_id = tw.team_id
            LEFT JOIN teams w ON m.winner_id = w.team_id
            WHERE m.match_id = :mid
        """), {"mid": match_id}).fetchone()

    if not r:
        raise HTTPException(status_code=404, detail="Match not found")

    return MatchResponse(
        match_id=r[0], season=r[1], match_number=r[2], match_date=r[3],
        match_type=r[4], match_status=r[5],
        venue=VenueBrief(venue_id=r[6], venue_name=r[7], city=r[8]) if r[6] else None,
        team_a=TeamBrief(team_id=r[9], team_code=r[10], team_name=r[11]) if r[9] else None,
        team_b=TeamBrief(team_id=r[12], team_code=r[13], team_name=r[14]) if r[12] else None,
        toss_winner=TeamBrief(team_id=r[15], team_code=r[16], team_name=r[17]) if r[15] else None,
        toss_decision=r[18],
        winner=TeamBrief(team_id=r[19], team_code=r[20], team_name=r[21]) if r[19] else None,
        win_margin=r[22], win_type=r[23], dl_applied=r[24] or False, source=r[25],
    )


@router.get("/{match_id}/scorecard", response_model=list[InningsScorecard])
def get_scorecard(match_id: UUID):
    """Get aggregated scorecard for a match."""
    engine = get_db_engine()

    # Verify match exists
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM matches WHERE match_id = :mid"), {"mid": match_id}
        ).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Match not found")

    with engine.connect() as conn:
        # Get distinct innings
        innings_rows = conn.execute(text("""
            SELECT DISTINCT innings FROM deliveries
            WHERE match_id = :mid ORDER BY innings
        """), {"mid": match_id}).fetchall()

        scorecards = []
        for (inn_num,) in innings_rows:
            # Batting aggregation
            batting_rows = conn.execute(text("""
                SELECT
                    d.batsman_id, p.full_name,
                    SUM(d.batsman_runs) AS runs,
                    SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END) AS balls,
                    SUM(CASE WHEN d.batsman_runs = 4 THEN 1 ELSE 0 END) AS fours,
                    SUM(CASE WHEN d.batsman_runs = 6 THEN 1 ELSE 0 END) AS sixes
                FROM deliveries d
                LEFT JOIN players p ON d.batsman_id = p.player_id
                WHERE d.match_id = :mid AND d.innings = :inn
                GROUP BY d.batsman_id, p.full_name
                ORDER BY MIN(d.over_number), MIN(d.ball_number)
            """), {"mid": match_id, "inn": inn_num}).fetchall()

            batting = [
                ScorecardBatting(
                    player_id=r[0], player_name=r[1] or "Unknown",
                    runs=r[2], balls=r[3], fours=r[4], sixes=r[5],
                    strike_rate=round(r[2] * 100.0 / r[3], 1) if r[3] else 0,
                )
                for r in batting_rows
            ]

            # Bowling aggregation
            bowling_rows = conn.execute(text("""
                SELECT
                    d.bowler_id, p.full_name,
                    SUM(CASE WHEN d.extras_type IS NULL OR d.extras_type NOT IN ('wide', 'noball') THEN 1 ELSE 0 END) AS legal_balls,
                    SUM(d.total_runs) AS runs,
                    SUM(CASE WHEN d.is_wicket = TRUE
                              AND d.wicket_type NOT IN ('run out', 'retired hurt', 'retired out', 'obstructing the field')
                         THEN 1 ELSE 0 END) AS wickets,
                    SUM(CASE WHEN d.batsman_runs = 0 AND d.extra_runs = 0 THEN 1 ELSE 0 END) AS dots,
                    SUM(CASE WHEN d.extras_type = 'wide' THEN 1 ELSE 0 END) AS wides,
                    SUM(CASE WHEN d.extras_type = 'noball' THEN 1 ELSE 0 END) AS noballs
                FROM deliveries d
                LEFT JOIN players p ON d.bowler_id = p.player_id
                WHERE d.match_id = :mid AND d.innings = :inn
                GROUP BY d.bowler_id, p.full_name
                ORDER BY MIN(d.over_number)
            """), {"mid": match_id, "inn": inn_num}).fetchall()

            bowling = [
                ScorecardBowling(
                    player_id=r[0], player_name=r[1] or "Unknown",
                    overs=round(r[2] / 6, 1) if r[2] else 0,
                    runs=r[3], wickets=r[4],
                    economy=round(r[3] * 6.0 / r[2], 2) if r[2] else 0,
                    dots=r[5], wides=r[6], noballs=r[7],
                )
                for r in bowling_rows
            ]

            # Innings total
            total_row = conn.execute(text("""
                SELECT
                    SUM(total_runs),
                    SUM(CASE WHEN is_wicket THEN 1 ELSE 0 END),
                    MAX(over_number) + 1
                FROM deliveries
                WHERE match_id = :mid AND innings = :inn
            """), {"mid": match_id, "inn": inn_num}).fetchone()

            scorecards.append(InningsScorecard(
                innings=inn_num,
                total_runs=total_row[0] or 0,
                total_wickets=total_row[1] or 0,
                total_overs=total_row[2] or 0,
                batting=batting,
                bowling=bowling,
            ))

    return scorecards


@router.get("/{match_id}/deliveries", response_model=list[DeliveryResponse])
def get_deliveries(
    match_id: UUID,
    innings: Optional[int] = Query(None, ge=1, le=10),
):
    """Get ball-by-ball data for a match."""
    engine = get_db_engine()

    query = """
        SELECT innings, over_number, ball_number, batsman_runs, extra_runs,
               total_runs, extras_type, is_wicket, wicket_type
        FROM deliveries
        WHERE match_id = :mid
    """
    params: dict = {"mid": match_id}
    if innings:
        query += " AND innings = :inn"
        params["inn"] = innings
    query += " ORDER BY innings, over_number, ball_number"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No deliveries found for this match")

    return [
        DeliveryResponse(
            innings=r[0], over_number=r[1], ball_number=r[2],
            batsman_runs=r[3], extra_runs=r[4], total_runs=r[5],
            extras_type=r[6], is_wicket=r[7] or False, wicket_type=r[8],
        )
        for r in rows
    ]
