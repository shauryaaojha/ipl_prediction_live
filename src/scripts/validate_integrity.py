"""Data Integrity Validation Script.

Runs comprehensive audit checks against the PostgreSQL database to verify
data completeness, referential integrity, duplicate detection, and data
quality. Outputs a structured report suitable for Phase 1 sign-off.

Usage:
    python -m src.scripts.validate_integrity
    docker compose run --rm scraper python -m src.scripts.validate_integrity
"""

from __future__ import annotations

import sys
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from sqlalchemy import text

from ..storage.connection import get_engine

console = Console()

# Expected match counts per season (from official IPL records)
EXPECTED_MATCHES = {
    2008: 59, 2009: 57, 2010: 60, 2011: 73, 2012: 76,
    2013: 76, 2014: 60, 2015: 60, 2016: 60, 2017: 59,
    2018: 60, 2019: 60, 2020: 60, 2021: 60, 2022: 74,
    2023: 74, 2024: 74,
}


def _query(engine, sql: str, params: dict = None) -> List[Any]:
    """Execute a raw SQL query and return all rows."""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return result.fetchall()


def _query_one(engine, sql: str, params: dict = None) -> Any:
    """Execute a raw SQL query and return a single value."""
    rows = _query(engine, sql, params)
    return rows[0][0] if rows else None


# ---------------------------------------------------------------------------
# Audit Checks
# ---------------------------------------------------------------------------

def check_completeness(engine) -> Dict[str, Any]:
    """Check season-wise match counts against expected totals."""
    rows = _query(engine, """
        SELECT season, COUNT(*) as match_count
        FROM matches
        GROUP BY season
        ORDER BY season
    """)

    results = []
    total_actual = 0
    total_expected = 0
    issues = 0

    for season, count in rows:
        expected = EXPECTED_MATCHES.get(season, "?")
        status = "✅" if expected != "?" and count >= expected else "⚠️"
        if status == "⚠️":
            issues += 1
        total_actual += count
        total_expected += expected if isinstance(expected, int) else 0
        results.append((season, count, expected, status))

    return {
        "name": "Historical Completeness",
        "results": results,
        "total_actual": total_actual,
        "total_expected": total_expected,
        "issues": issues,
    }


def check_referential_integrity(engine) -> Dict[str, Any]:
    """Check for orphan records across all foreign key relationships."""
    checks = [
        ("Orphan Deliveries (no match)", """
            SELECT COUNT(*) FROM deliveries d
            LEFT JOIN matches m ON d.match_id = m.match_id
            WHERE m.match_id IS NULL
        """),
        ("Orphan Batsmen in Deliveries", """
            SELECT COUNT(*) FROM deliveries d
            LEFT JOIN players p ON d.batsman_id = p.player_id
            WHERE d.batsman_id IS NOT NULL AND p.player_id IS NULL
        """),
        ("Orphan Bowlers in Deliveries", """
            SELECT COUNT(*) FROM deliveries d
            LEFT JOIN players p ON d.bowler_id = p.player_id
            WHERE d.bowler_id IS NOT NULL AND p.player_id IS NULL
        """),
        ("Orphan Dismissed Players", """
            SELECT COUNT(*) FROM deliveries d
            LEFT JOIN players p ON d.player_dismissed_id = p.player_id
            WHERE d.player_dismissed_id IS NOT NULL AND p.player_id IS NULL
        """),
        ("Orphan Fielders", """
            SELECT COUNT(*) FROM deliveries d
            LEFT JOIN players p ON d.fielder_id = p.player_id
            WHERE d.fielder_id IS NOT NULL AND p.player_id IS NULL
        """),
        ("Orphan Venues in Matches", """
            SELECT COUNT(*) FROM matches m
            LEFT JOIN venues v ON m.venue_id = v.venue_id
            WHERE m.venue_id IS NOT NULL AND v.venue_id IS NULL
        """),
        ("Orphan Teams (team_a)", """
            SELECT COUNT(*) FROM matches m
            LEFT JOIN teams t ON m.team_a_id = t.team_id
            WHERE m.team_a_id IS NOT NULL AND t.team_id IS NULL
        """),
        ("Orphan Teams (team_b)", """
            SELECT COUNT(*) FROM matches m
            LEFT JOIN teams t ON m.team_b_id = t.team_id
            WHERE m.team_b_id IS NOT NULL AND t.team_id IS NULL
        """),
    ]

    results = []
    issues = 0
    for name, sql in checks:
        count = _query_one(engine, sql)
        status = "✅" if count == 0 else "⚠️"
        if count > 0:
            issues += 1
        results.append((name, count, status))

    return {"name": "Referential Integrity", "results": results, "issues": issues}


def check_duplicates(engine) -> Dict[str, Any]:
    """Check for duplicate records in key tables."""
    checks = [
        ("Duplicate match_sources", """
            SELECT COUNT(*) FROM (
                SELECT source, source_id, COUNT(*) as cnt
                FROM match_sources
                GROUP BY source, source_id
                HAVING COUNT(*) > 1
            ) dups
        """),
        ("Duplicate player_sources", """
            SELECT COUNT(*) FROM (
                SELECT source, source_id, COUNT(*) as cnt
                FROM player_sources
                GROUP BY source, source_id
                HAVING COUNT(*) > 1
            ) dups
        """),
        ("Duplicate deliveries (same ball)", """
            SELECT COUNT(*) FROM (
                SELECT match_id, innings, over_number, ball_number, COUNT(*) as cnt
                FROM deliveries
                GROUP BY match_id, innings, over_number, ball_number
                HAVING COUNT(*) > 1
            ) dups
        """),
        ("Duplicate players (same name)", """
            SELECT COUNT(*) FROM (
                SELECT full_name, COUNT(*) as cnt
                FROM players
                GROUP BY full_name
                HAVING COUNT(*) > 1
            ) dups
        """),
    ]

    results = []
    issues = 0
    for name, sql in checks:
        count = _query_one(engine, sql)
        status = "✅" if count == 0 else "⚠️"
        if count > 0:
            issues += 1
        results.append((name, count, status))

    return {"name": "Duplicate Detection", "results": results, "issues": issues}


def check_data_quality(engine) -> Dict[str, Any]:
    """Check for data quality issues in the dataset."""
    checks = [
        ("Deliveries with NULL bowler_id", """
            SELECT COUNT(*) FROM deliveries WHERE bowler_id IS NULL
        """),
        ("Deliveries with NULL batsman_id", """
            SELECT COUNT(*) FROM deliveries WHERE batsman_id IS NULL
        """),
        ("Invalid innings (> 4)", """
            SELECT COUNT(*) FROM deliveries WHERE innings > 4
        """),
        ("Invalid overs (> 19)", """
            SELECT COUNT(*) FROM deliveries WHERE over_number > 19
        """),
        ("Completed matches without winner", """
            SELECT COUNT(*) FROM matches
            WHERE match_status = 'complete'
            AND winner_id IS NULL
            AND win_type NOT IN ('tie', 'no_result')
        """),
        ("Matches without toss info", """
            SELECT COUNT(*) FROM matches
            WHERE match_status = 'complete'
            AND (toss_winner_id IS NULL OR toss_decision IS NULL)
        """),
        ("Matches without venue", """
            SELECT COUNT(*) FROM matches WHERE venue_id IS NULL
        """),
        ("Deliveries with invalid ball_number (< 1)", """
            SELECT COUNT(*) FROM deliveries WHERE ball_number < 1
        """),
    ]

    results = []
    issues = 0
    for name, sql in checks:
        count = _query_one(engine, sql)
        status = "✅" if count == 0 else "⚠️"
        if count > 0:
            issues += 1
        results.append((name, count, status))

    return {"name": "Data Quality", "results": results, "issues": issues}


def investigate_null_fks(engine) -> Dict[str, Any]:
    """Investigate the NULL bowler_id and batsman_id deliveries in detail."""
    null_bowler_details = _query(engine, """
        SELECT m.season, m.match_number, d.innings, d.over_number, d.ball_number,
               d.extras_type, d.is_wicket, d.total_runs
        FROM deliveries d
        JOIN matches m ON d.match_id = m.match_id
        WHERE d.bowler_id IS NULL
        ORDER BY m.season, m.match_number, d.innings, d.over_number
        LIMIT 30
    """)

    null_batsman_details = _query(engine, """
        SELECT m.season, m.match_number, d.innings, d.over_number, d.ball_number,
               d.extras_type, d.is_wicket, d.total_runs
        FROM deliveries d
        JOIN matches m ON d.match_id = m.match_id
        WHERE d.batsman_id IS NULL
        ORDER BY m.season, m.match_number, d.innings, d.over_number
        LIMIT 10
    """)

    return {
        "name": "NULL FK Investigation",
        "null_bowlers": null_bowler_details,
        "null_batsmen": null_batsman_details,
    }


def get_summary_stats(engine) -> Dict[str, int]:
    """Get high-level database stats."""
    return {
        "total_matches": _query_one(engine, "SELECT COUNT(*) FROM matches"),
        "total_deliveries": _query_one(engine, "SELECT COUNT(*) FROM deliveries"),
        "total_players": _query_one(engine, "SELECT COUNT(*) FROM players"),
        "total_venues": _query_one(engine, "SELECT COUNT(*) FROM venues"),
        "total_teams": _query_one(engine, "SELECT COUNT(*) FROM teams"),
        "total_match_sources": _query_one(engine, "SELECT COUNT(*) FROM match_sources"),
        "total_player_sources": _query_one(engine, "SELECT COUNT(*) FROM player_sources"),
    }


# ---------------------------------------------------------------------------
# Report Output
# ---------------------------------------------------------------------------

def print_report(engine) -> int:
    """Run all checks and print a formatted report. Returns total issue count."""
    console.print(Panel("[bold cyan]🏏 IPL Data Platform — Integrity Audit Report[/]", expand=False))

    # Summary stats
    stats = get_summary_stats(engine)
    summary_table = Table(title="📊 Database Summary", show_header=True)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="bold white", justify="right")
    for key, val in stats.items():
        label = key.replace("total_", "").replace("_", " ").title()
        summary_table.add_row(label, f"{val:,}")
    console.print(summary_table)
    console.print()

    total_issues = 0

    # 1. Completeness
    comp = check_completeness(engine)
    total_issues += comp["issues"]
    comp_table = Table(title=f"1️⃣  {comp['name']}", show_header=True)
    comp_table.add_column("Season", style="cyan", justify="center")
    comp_table.add_column("Actual", justify="right")
    comp_table.add_column("Expected", justify="right")
    comp_table.add_column("Status", justify="center")
    for season, actual, expected, status in comp["results"]:
        comp_table.add_row(str(season), str(actual), str(expected), status)
    comp_table.add_row(
        "[bold]TOTAL[/]",
        f"[bold]{comp['total_actual']}[/]",
        f"[bold]{comp['total_expected']}[/]",
        "✅" if comp["issues"] == 0 else "⚠️",
    )
    console.print(comp_table)
    console.print()

    # 2. Referential Integrity
    ref = check_referential_integrity(engine)
    total_issues += ref["issues"]
    ref_table = Table(title=f"2️⃣  {ref['name']}", show_header=True)
    ref_table.add_column("Check", style="cyan")
    ref_table.add_column("Count", justify="right")
    ref_table.add_column("Status", justify="center")
    for name, count, status in ref["results"]:
        ref_table.add_row(name, str(count), status)
    console.print(ref_table)
    console.print()

    # 3. Duplicates
    dup = check_duplicates(engine)
    total_issues += dup["issues"]
    dup_table = Table(title=f"3️⃣  {dup['name']}", show_header=True)
    dup_table.add_column("Check", style="cyan")
    dup_table.add_column("Count", justify="right")
    dup_table.add_column("Status", justify="center")
    for name, count, status in dup["results"]:
        dup_table.add_row(name, str(count), status)
    console.print(dup_table)
    console.print()

    # 4. Data Quality
    dq = check_data_quality(engine)
    total_issues += dq["issues"]
    dq_table = Table(title=f"4️⃣  {dq['name']}", show_header=True)
    dq_table.add_column("Check", style="cyan")
    dq_table.add_column("Count", justify="right")
    dq_table.add_column("Status", justify="center")
    for name, count, status in dq["results"]:
        dq_table.add_row(name, str(count), status)
    console.print(dq_table)
    console.print()

    # 5. NULL FK Investigation
    null_fks = investigate_null_fks(engine)
    if null_fks["null_bowlers"]:
        console.print(Panel("[bold yellow]5️⃣  NULL bowler_id Deliveries (sample)[/]"))
        nb_table = Table(show_header=True)
        nb_table.add_column("Season", justify="center")
        nb_table.add_column("Match#", justify="center")
        nb_table.add_column("Inn", justify="center")
        nb_table.add_column("Over", justify="center")
        nb_table.add_column("Ball", justify="center")
        nb_table.add_column("Extras", justify="center")
        nb_table.add_column("Wicket", justify="center")
        nb_table.add_column("Runs", justify="center")
        for row in null_fks["null_bowlers"][:15]:
            nb_table.add_row(*[str(v) if v is not None else "-" for v in row])
        console.print(nb_table)
        console.print()

    if null_fks["null_batsmen"]:
        console.print(Panel("[bold yellow]5️⃣  NULL batsman_id Deliveries (sample)[/]"))
        nb_table = Table(show_header=True)
        nb_table.add_column("Season", justify="center")
        nb_table.add_column("Match#", justify="center")
        nb_table.add_column("Inn", justify="center")
        nb_table.add_column("Over", justify="center")
        nb_table.add_column("Ball", justify="center")
        nb_table.add_column("Extras", justify="center")
        nb_table.add_column("Wicket", justify="center")
        nb_table.add_column("Runs", justify="center")
        for row in null_fks["null_batsmen"]:
            nb_table.add_row(*[str(v) if v is not None else "-" for v in row])
        console.print(nb_table)
        console.print()

    # Final verdict
    if total_issues == 0:
        console.print(Panel("[bold green]✅ ALL CHECKS PASSED — Data integrity verified![/]", expand=False))
    else:
        console.print(Panel(f"[bold yellow]⚠️  {total_issues} issue(s) found — review above for details[/]", expand=False))

    return total_issues


def run():
    """Entry point for the validation script."""
    try:
        engine = get_engine()
        issues = print_report(engine)
        sys.exit(0 if issues == 0 else 1)
    except Exception as e:
        logger.error("Validation failed: {}", e)
        console.print(f"[bold red]Error: {e}[/]")
        sys.exit(2)


if __name__ == "__main__":
    run()
