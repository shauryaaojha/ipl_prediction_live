"""Unified search router — search across players, teams, venues.

Uses PostgreSQL ILIKE for fuzzy matching. A future upgrade could add
pg_trgm trigram indexes or Elasticsearch for better typo tolerance.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import text

from ..deps import get_db_engine
from ..schemas import SearchResponse, SearchResult

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=SearchResponse)
def unified_search(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(20, ge=1, le=50, description="Max results per category"),
):
    """Search across players, teams, and venues.

    Returns a combined, ranked list of results. Player matches are boosted
    for exact name matches.
    """
    engine = get_db_engine()
    pattern = f"%{q}%"
    results: list[SearchResult] = []

    with engine.connect() as conn:
        # Search players
        player_rows = conn.execute(text("""
            SELECT player_id, full_name, role, nationality,
                   CASE
                       WHEN full_name ILIKE :exact THEN 100
                       WHEN full_name ILIKE :starts THEN 80
                       ELSE 50
                   END AS relevance
            FROM players
            WHERE full_name ILIKE :pattern
            ORDER BY relevance DESC, full_name
            LIMIT :limit
        """), {
            "pattern": pattern,
            "exact": q,
            "starts": f"{q}%",
            "limit": limit,
        }).fetchall()

        for r in player_rows:
            detail_parts = [p for p in [r[2], r[3]] if p]
            results.append(SearchResult(
                type="player",
                id=str(r[0]),
                name=r[1],
                detail=", ".join(detail_parts) if detail_parts else None,
                score=r[4],
            ))

        # Search player aliases
        alias_rows = conn.execute(text("""
            SELECT p.player_id, p.full_name, pa.alias_name, p.role
            FROM player_aliases pa
            JOIN players p ON pa.player_id = p.player_id
            WHERE pa.alias_name ILIKE :pattern
              AND p.player_id NOT IN (
                  SELECT player_id FROM players WHERE full_name ILIKE :pattern
              )
            LIMIT :limit
        """), {"pattern": pattern, "limit": limit}).fetchall()

        for r in alias_rows:
            results.append(SearchResult(
                type="player",
                id=str(r[0]),
                name=r[1],
                detail=f"alias: {r[2]}",
                score=40,
            ))

        # Search teams
        team_rows = conn.execute(text("""
            SELECT team_id, team_code, team_name,
                   CASE
                       WHEN team_code ILIKE :exact THEN 100
                       WHEN team_name ILIKE :starts THEN 80
                       ELSE 50
                   END AS relevance
            FROM teams
            WHERE team_code ILIKE :pattern OR team_name ILIKE :pattern
            ORDER BY relevance DESC
            LIMIT :limit
        """), {
            "pattern": pattern,
            "exact": q,
            "starts": f"{q}%",
            "limit": limit,
        }).fetchall()

        for r in team_rows:
            results.append(SearchResult(
                type="team",
                id=str(r[0]),
                name=f"{r[1]} — {r[2]}",
                detail=None,
                score=r[3],
            ))

        # Search venues
        venue_rows = conn.execute(text("""
            SELECT venue_id, venue_name, city,
                   CASE
                       WHEN venue_name ILIKE :starts THEN 80
                       WHEN city ILIKE :starts THEN 70
                       ELSE 50
                   END AS relevance
            FROM venues
            WHERE venue_name ILIKE :pattern OR city ILIKE :pattern
            ORDER BY relevance DESC
            LIMIT :limit
        """), {
            "pattern": pattern,
            "starts": f"{q}%",
            "limit": limit,
        }).fetchall()

        for r in venue_rows:
            results.append(SearchResult(
                type="venue",
                id=str(r[0]),
                name=r[1],
                detail=r[2],
                score=r[3],
            ))

    # Sort all results by relevance score
    results.sort(key=lambda x: x.score, reverse=True)

    return SearchResponse(
        query=q,
        total=len(results),
        results=results,
    )
