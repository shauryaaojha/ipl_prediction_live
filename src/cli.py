"""IPL 2026 Data Scraper — CLI Interface.

Provides command-line access to all scraping operations via Typer.

Usage:
    python -m src.cli --help
    python -m src.cli historical-scrape --start-season 2008 --end-season 2025
    python -m src.cli incremental-scrape
    python -m src.cli scrape-match --match-id 12345
    python -m src.cli db-health
    python -m src.cli export --format csv
    python -m src.cli daemon
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .core.config_manager import load_config, setup_logging
from .core.orchestrator import ScraperOrchestrator
from .storage.connection import check_db_health, init_db, init_warehouse

app = typer.Typer(
    name="ipl-scraper",
    help="IPL 2026 Data Scraper — Collect IPL cricket data for prediction models.",
    add_completion=False,
)
console = Console()


def _get_orchestrator() -> ScraperOrchestrator:
    """Initialize and return the orchestrator."""
    config = load_config()
    setup_logging(config)
    init_warehouse()
    return ScraperOrchestrator(config)


def _run_async(orchestrator: ScraperOrchestrator, coro):
    """Run an async command with proper cleanup in a single event loop."""
    async def _runner():
        try:
            return await coro
        finally:
            await orchestrator.close()
    return asyncio.run(_runner())


# ===========================================================================
# Historical Scrape
# ===========================================================================

@app.command("historical-scrape")
def historical_scrape(
    start_season: int = typer.Option(2008, "--start-season", "-s", help="Start year"),
    end_season: int = typer.Option(2025, "--end-season", "-e", help="End year"),
):
    """Run a full historical scrape for IPL seasons."""
    console.print(f"\n[bold green]📊 Starting historical scrape: {start_season} to {end_season}[/bold green]\n")

    orchestrator = _get_orchestrator()
    try:
        _run_async(orchestrator, orchestrator.run_full_historical_scrape(start_season, end_season))
        
        # Validation checks
        from sqlalchemy import text
        from .storage.connection import get_session
        with get_session() as session:
            matches_count = session.execute(text("SELECT COUNT(*) FROM matches")).scalar() or 0
            deliveries_count = session.execute(text("SELECT COUNT(*) FROM deliveries")).scalar() or 0
            players_count = session.execute(text("SELECT COUNT(*) FROM players")).scalar() or 0
            venues_count = session.execute(text("SELECT COUNT(*) FROM venues")).scalar() or 0
            
            season_counts = session.execute(text("SELECT season, COUNT(*) FROM matches GROUP BY season ORDER BY season")).fetchall()
            
        console.print("\n[bold cyan]=== Historical Import Summary ===[/bold cyan]")
        console.print(f"Matches imported:     [bold]{matches_count}[/bold]")
        console.print(f"Deliveries imported:  [bold]{deliveries_count}[/bold]")
        console.print(f"Players in DB:        [bold]{players_count}[/bold]")
        console.print(f"Venues in DB:         [bold]{venues_count}[/bold]")
        
        console.print("\n[bold cyan]--- Season Breakdown ---[/bold cyan]")
        for row in season_counts:
            console.print(f"Season {row[0]}: {row[1]} matches")
            
        console.print("\n[bold cyan]--- Validation Checks ---[/bold cyan]")
        matches_ok = matches_count > 0
        delivs_ok = deliveries_count > 0
        players_ok = players_count > 0
        venues_ok = venues_count > 0
        
        console.print(f"Matches          {'[bold green]✓[/bold green]' if matches_ok else '[bold red]✗[/bold red]'}")
        console.print(f"Venues           {'[bold green]✓[/bold green]' if venues_ok else '[bold red]✗[/bold red]'}")
        console.print(f"Deliveries       {'[bold green]✓[/bold green]' if delivs_ok else '[bold red]✗[/bold red]'}")
        console.print(f"Players          {'[bold green]✓[/bold green]' if players_ok else '[bold red]✗[/bold red]'}")
        
        if matches_ok and delivs_ok and players_ok and venues_ok:
            console.print("\nOverall          [bold green]SUCCESS[/bold green]")
            console.print("\n[bold green]✅ Historical scrape completed successfully![/bold green]")
        elif matches_ok or delivs_ok or players_ok or venues_ok:
            console.print("\nOverall          [bold yellow]PARTIAL SUCCESS[/bold yellow]")
            console.print("\n[bold yellow]⚠️ Historical scrape completed with partial success![/bold yellow]")
        else:
            console.print("\nOverall          [bold red]FAILED[/bold red]")
            console.print("\n[bold red]❌ Historical scrape failed![/bold red]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Scrape interrupted. Progress has been saved.[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Scrape failed: {e}[/bold red]")
        raise typer.Exit(code=1)


# ===========================================================================
# Incremental Scrape
# ===========================================================================

@app.command("incremental-scrape")
def incremental_scrape():
    """Run an incremental scrape for the current/latest season."""
    console.print("\n[bold cyan]🔄 Starting incremental scrape...[/bold cyan]\n")

    orchestrator = _get_orchestrator()
    try:
        _run_async(orchestrator, orchestrator.run_incremental_scrape())
        console.print("\n[bold green]✅ Incremental scrape completed![/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Scrape failed: {e}[/bold red]")
        raise typer.Exit(code=1)


# ===========================================================================
# System Health & Utilities
# ===========================================================================

@app.command("db-health")
def db_health():
    """Check database connection and scraper endpoints."""
    console.print("\n[bold cyan]🏥 Checking system health...[/bold cyan]\n")
    
    # Check DB
    db_ok = check_db_health()
    console.print(f"PostgreSQL Database: {'[bold green]OK[/bold green]' if db_ok else '[bold red]FAILED[/bold red]'}")
    
    # Check Scrapers
    orchestrator = _get_orchestrator()
    
    async def _check_scrapers():
        checks = {
            "Cricsheet": orchestrator.cricsheet.health_check(),
            "ESPN": orchestrator.espn.health_check(),
            "Cricbuzz": orchestrator.cricbuzz.health_check(),
            "IPLT20": orchestrator.iplt20.health_check(),
        }
        for name, task in checks.items():
            try:
                ok = await task
                console.print(f"{name} Scraper: {'[bold green]OK[/bold green]' if ok else '[bold red]UNREACHABLE[/bold red]'}")
            except Exception:
                console.print(f"{name} Scraper: [bold red]ERROR[/bold red]")
                
    _run_async(orchestrator, _check_scrapers())


@app.command("download-cricsheet")
def download_cricsheet():
    """Force download of Cricsheet historical data ZIP."""
    console.print("\n[bold cyan]📥 Downloading Cricsheet data...[/bold cyan]\n")
    orchestrator = _get_orchestrator()
    
    async def _dl():
        cache_dir = await orchestrator.cricsheet._ensure_data()
        console.print(f"[bold green]✅ Downloaded and extracted to {cache_dir}[/bold green]")
        
    _run_async(orchestrator, _dl())


# ===========================================================================
# Scrape Single Match
# ===========================================================================

@app.command("scrape-match")
def scrape_match(
    match_id: str = typer.Option(..., "--match-id", "-m", help="ESPN match ID"),
    source: str = typer.Option("espncricinfo", "--source", help="Data source"),
):
    """Scrape data for a specific match."""
    console.print(f"\n[bold cyan]🏏 Scraping match {match_id} from {source}...[/bold cyan]\n")

    orchestrator = _get_orchestrator()
    try:
        result = _run_async(orchestrator, orchestrator.scrape_single_match(match_id, source))
        if result:
            console.print_json(json.dumps(result, indent=2, default=str))
            console.print("\n[bold green]✅ Match data scraped successfully![/bold green]")
        else:
            console.print("[yellow]⚠️  No data returned for this match.[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Failed: {e}[/bold red]")
        raise typer.Exit(code=1)


# ===========================================================================
# Scrape Player Stats
# ===========================================================================

@app.command("scrape-player")
def scrape_player(
    player_id: str = typer.Option(..., "--player-id", "-p", help="ESPN player ID"),
    source: str = typer.Option("espncricinfo", "--source", help="Data source"),
):
    """Scrape statistics for a specific player."""
    console.print(f"\n[bold cyan]👤 Scraping player {player_id}...[/bold cyan]\n")

    orchestrator = _get_orchestrator()
    try:
        result = _run_async(orchestrator, orchestrator.scrape_player(player_id, source))
        if result:
            console.print_json(json.dumps(result, indent=2, default=str))
        else:
            console.print("[yellow]⚠️  No data returned.[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Failed: {e}[/bold red]")
        raise typer.Exit(code=1)


# ===========================================================================
# Check Injuries
# ===========================================================================

@app.command("check-injuries")
def check_injuries():
    """Scrape news sites for IPL injury and availability updates."""
    console.print("\n[bold cyan]🏥 Checking injury updates...[/bold cyan]\n")

    orchestrator = _get_orchestrator()
    try:
        results = _run_async(orchestrator, orchestrator.check_injuries())
        if results:
            table = Table(title="Injury Updates Found")
            table.add_column("Source", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("Status", style="yellow")
            table.add_column("Confidence", style="green")

            for r in results:
                entities = r.get("entities", {})
                table.add_row(
                    r.get("url", "")[:40],
                    r.get("title", "")[:60],
                    entities.get("status", "unknown"),
                    f"{entities.get('confidence', 0):.0%}",
                )
            console.print(table)
        else:
            console.print("[green]No injury updates found.[/green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Failed: {e}[/bold red]")


# ===========================================================================
# Database Health Check
# ===========================================================================

@app.command("db-health")
def db_health():
    """Check database connectivity and health."""
    console.print("\n[bold cyan]🔍 Checking database health...[/bold cyan]\n")

    # PostgreSQL
    pg_health = check_db_health()
    if pg_health["status"] == "healthy":
        console.print(f"  [green]✅ PostgreSQL:[/green] Connected to '{pg_health.get('database')}'")
    else:
        console.print(f"  [red]❌ PostgreSQL:[/red] {pg_health.get('error', 'Connection failed')}")

    # SQLite Warehouse
    try:
        init_warehouse()
        console.print("  [green]✅ SQLite Warehouse:[/green] Initialized")
    except Exception as e:
        console.print(f"  [red]❌ SQLite Warehouse:[/red] {e}")

    console.print()


# ===========================================================================
# Initialize Database
# ===========================================================================

@app.command("init-db")
def init_database():
    """Initialize database tables (create if not exists)."""
    console.print("\n[bold cyan]🗄️  Initializing database...[/bold cyan]\n")

    try:
        init_db()
        init_warehouse()
        console.print("[bold green]✅ All database tables created successfully![/bold green]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Failed: {e}[/bold red]")
        raise typer.Exit(code=1)


# ===========================================================================
# Export Data
# ===========================================================================

@app.command("export")
def export_data(
    format: str = typer.Option("csv", "--format", "-f", help="Export format: csv, parquet, json"),
    output: str = typer.Option("./data/exports", "--output", "-o", help="Output directory"),
    season: Optional[int] = typer.Option(None, "--season", help="Filter by season"),
):
    """Export scraped data to CSV, Parquet, or JSON files."""
    console.print(f"\n[bold cyan]📁 Exporting data as {format.upper()}...[/bold cyan]\n")

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        import pandas as pd
        from sqlalchemy import create_engine, text
        from .storage.connection import get_engine

        engine = get_engine()

        tables = ["matches", "players", "teams", "venues", "player_stats", "playing_xi"]
        for table in tables:
            query = f"SELECT * FROM {table}"
            if season and table in ("matches", "player_stats"):
                query += f" WHERE season = {season}"

            try:
                df = pd.read_sql(text(query), engine)
                if df.empty:
                    console.print(f"  [dim]⏭️  {table}: no data[/dim]")
                    continue

                if format == "csv":
                    filepath = output_path / f"{table}.csv"
                    df.to_csv(filepath, index=False)
                elif format == "parquet":
                    filepath = output_path / f"{table}.parquet"
                    df.to_parquet(filepath, index=False)
                elif format == "json":
                    filepath = output_path / f"{table}.json"
                    df.to_json(filepath, orient="records", indent=2, default_handler=str)
                else:
                    console.print(f"[red]Unknown format: {format}[/red]")
                    return

                console.print(f"  [green]✅ {table}:[/green] {len(df)} rows → {filepath}")
            except Exception as e:
                console.print(f"  [yellow]⚠️  {table}: {e}[/yellow]")

        console.print(f"\n[bold green]📁 Export complete → {output_path}[/bold green]")

    except ImportError:
        console.print("[red]pandas is required for export. Install with: pip install pandas[/red]")
        raise typer.Exit(code=1)


# ===========================================================================
# Daemon Mode
# ===========================================================================

@app.command("daemon")
def daemon():
    """Run the scraper as a background daemon with scheduled jobs."""
    console.print("\n[bold green]🚀 Starting IPL Scraper Daemon...[/bold green]\n")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    config = load_config()
    setup_logging(config)
    init_warehouse()

    orchestrator = ScraperOrchestrator(config)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        scheduler = orchestrator.schedule_jobs()
        if scheduler:
            console.print("[green]✅ Scheduler started. Jobs:[/green]")
            for job in scheduler.get_jobs():
                console.print(f"  📌 {job.name} (next run: {job.next_run_time})")
            console.print()
            loop.run_forever()
        else:
            console.print("[yellow]⚠️  APScheduler not available. Install with: pip install apscheduler[/yellow]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down daemon...[/yellow]")
    finally:
        loop.run_until_complete(orchestrator.close())
        loop.close()
        console.print("[green]Daemon stopped.[/green]")


# ===========================================================================
# Status / Info
# ===========================================================================

@app.command("info")
def info():
    """Show application configuration and status."""
    config = load_config()

    table = Table(title="IPL 2026 Data Scraper — Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("App Name", config.get("name", "N/A"))
    table.add_row("Version", config.get("version", "N/A"))
    table.add_row("Environment", config.get("environment", "N/A"))
    table.add_row("Data Path", config.get("storage", {}).get("data_path", "N/A"))
    table.add_row("Concurrent Requests", str(config.get("concurrent_requests", "N/A")))
    table.add_row("Request Delay", f"{config.get('request_delay', 'N/A')}s")
    table.add_row("Max Retries", str(config.get("max_retries", "N/A")))
    table.add_row("HTTP/2 Enabled", str(config.get("http2_enabled", "N/A")))
    table.add_row("Browser Fallback", str(config.get("browser_fallback", "N/A")))

    # Sources
    sources = config.get("sources", {})
    for domain, src in sources.items():
        primary = src.get("primary", "N/A") if isinstance(src, dict) else str(src)
        fallback = src.get("fallback", []) if isinstance(src, dict) else []
        if isinstance(fallback, list):
            fallback = ", ".join(fallback)
        table.add_row(f"Source: {domain}", f"{primary} (fallback: {fallback})")

    console.print()
    console.print(table)
    console.print()


# ===========================================================================
# Entry Point
# ===========================================================================

def main():
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
