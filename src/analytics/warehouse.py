"""Analytics Warehouse Manager.

Manages materialized view lifecycle: creation, refresh, and status monitoring.
All materialized views are defined in scripts/analytics_views.sql and managed
here for programmatic refresh via CLI or API.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import text

from ..storage.connection import get_engine

# Ordered list of materialized views managed by this module
MATERIALIZED_VIEWS = [
    "mv_batting_career_stats",
    "mv_bowling_career_stats",
    "mv_batting_season_stats",
    "mv_bowling_season_stats",
    "mv_venue_stats",
    "mv_team_season_stats",
]


def apply_analytics_schema() -> None:
    """Apply the analytics_views.sql schema to create all views.

    This is idempotent — views are created with DROP IF EXISTS + CREATE.
    """
    sql_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "analytics_views.sql"
    if not sql_path.exists():
        logger.error("analytics_views.sql not found at: {}", sql_path)
        raise FileNotFoundError(f"Missing: {sql_path}")

    engine = get_engine()
    sql_content = sql_path.read_text(encoding="utf-8")

    # Split on semicolons and execute statements one by one
    # (psycopg2 doesn't support multi-statement execution well)
    statements = [s.strip() for s in sql_content.split(";") if s.strip() and not s.strip().startswith("--")]

    with engine.connect() as conn:
        for stmt in statements:
            if stmt:
                try:
                    conn.execute(text(stmt))
                except Exception as e:
                    logger.warning("Statement failed (may be OK): {}", str(e)[:200])
        conn.commit()

    logger.info("Analytics schema applied successfully ({} statements)", len(statements))


def refresh_view(view_name: str, concurrently: bool = True) -> float:
    """Refresh a single materialized view.

    Args:
        view_name: Name of the materialized view to refresh.
        concurrently: If True, use CONCURRENTLY (requires unique index).

    Returns:
        Duration in seconds.
    """
    engine = get_engine()
    mode = "CONCURRENTLY" if concurrently else ""

    start = datetime.utcnow()
    with engine.connect() as conn:
        conn.execute(text(f"REFRESH MATERIALIZED VIEW {mode} {view_name}"))
        conn.commit()
    duration = (datetime.utcnow() - start).total_seconds()

    logger.info("Refreshed {} in {:.2f}s", view_name, duration)
    return duration


def refresh_all_views(concurrently: bool = True) -> Dict[str, float]:
    """Refresh all materialized views in order.

    Returns:
        Dictionary mapping view name to refresh duration in seconds.
    """
    results = {}
    total_start = datetime.utcnow()

    for view_name in MATERIALIZED_VIEWS:
        try:
            duration = refresh_view(view_name, concurrently=concurrently)
            results[view_name] = duration
        except Exception as e:
            logger.error("Failed to refresh {}: {}", view_name, e)
            # Try without CONCURRENTLY as fallback
            if concurrently:
                try:
                    logger.info("Retrying {} without CONCURRENTLY...", view_name)
                    duration = refresh_view(view_name, concurrently=False)
                    results[view_name] = duration
                except Exception as e2:
                    logger.error("Retry also failed for {}: {}", view_name, e2)
                    results[view_name] = -1
            else:
                results[view_name] = -1

    total_duration = (datetime.utcnow() - total_start).total_seconds()
    logger.info("All views refreshed in {:.2f}s", total_duration)
    return results


def get_view_status() -> List[Dict[str, Any]]:
    """Get row counts and existence status for all materialized views.

    Returns:
        List of dicts with view_name, row_count, and exists fields.
    """
    engine = get_engine()
    status = []

    for view_name in MATERIALIZED_VIEWS:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {view_name}"))
                count = result.scalar()
                status.append({
                    "view_name": view_name,
                    "row_count": count,
                    "exists": True,
                })
        except Exception:
            status.append({
                "view_name": view_name,
                "row_count": 0,
                "exists": False,
            })

    return status


def get_summary_report() -> Dict[str, Any]:
    """Generate a high-level analytics summary report.

    Queries the materialized views to produce headline stats:
    - Top run scorers
    - Top wicket takers
    - Venue rankings
    - Team standings per season
    """
    engine = get_engine()
    report = {}

    try:
        with engine.connect() as conn:
            # Top 10 run scorers (career)
            rows = conn.execute(text("""
                SELECT full_name, total_runs, matches, innings, strike_rate, batting_average, fours, sixes
                FROM mv_batting_career_stats
                ORDER BY total_runs DESC
                LIMIT 10
            """)).fetchall()
            report["top_run_scorers"] = [
                {
                    "player": r[0], "runs": r[1], "matches": r[2],
                    "innings": r[3], "sr": float(r[4]) if r[4] else 0,
                    "avg": float(r[5]) if r[5] else 0,
                    "fours": r[6], "sixes": r[7],
                }
                for r in rows
            ]

            # Top 10 wicket takers (career)
            rows = conn.execute(text("""
                SELECT full_name, wickets, matches, overs_bowled, economy_rate, bowling_average, bowling_strike_rate
                FROM mv_bowling_career_stats
                ORDER BY wickets DESC
                LIMIT 10
            """)).fetchall()
            report["top_wicket_takers"] = [
                {
                    "player": r[0], "wickets": r[1], "matches": r[2],
                    "overs": float(r[3]) if r[3] else 0,
                    "econ": float(r[4]) if r[4] else 0,
                    "avg": float(r[5]) if r[5] else 0,
                    "sr": float(r[6]) if r[6] else 0,
                }
                for r in rows
            ]

            # Venue summary (top 10 by matches)
            rows = conn.execute(text("""
                SELECT venue_name, city, total_matches,
                       avg_first_innings_score, avg_second_innings_score, chase_success_pct
                FROM mv_venue_stats
                ORDER BY total_matches DESC
                LIMIT 10
            """)).fetchall()
            report["top_venues"] = [
                {
                    "venue": r[0], "city": r[1], "matches": r[2],
                    "avg_1st": float(r[3]) if r[3] else 0,
                    "avg_2nd": float(r[4]) if r[4] else 0,
                    "chase_pct": float(r[5]) if r[5] else 0,
                }
                for r in rows
            ]

            # Latest season team standings
            latest_season_row = conn.execute(text("""
                SELECT MAX(season) FROM mv_team_season_stats
            """)).scalar()

            if latest_season_row:
                rows = conn.execute(text("""
                    SELECT team_code, team_name, matches_played, wins, losses,
                           win_percentage, tosses_won, bat_first_wins, chase_wins
                    FROM mv_team_season_stats
                    WHERE season = :season
                    ORDER BY win_percentage DESC
                """), {"season": latest_season_row}).fetchall()
                report["latest_season"] = latest_season_row
                report["team_standings"] = [
                    {
                        "code": r[0], "name": r[1], "played": r[2],
                        "wins": r[3], "losses": r[4],
                        "win_pct": float(r[5]) if r[5] else 0,
                        "tosses": r[6], "bat_first_w": r[7], "chase_w": r[8],
                    }
                    for r in rows
                ]

    except Exception as e:
        logger.error("Failed to generate report: {}", e)
        report["error"] = str(e)

    return report
