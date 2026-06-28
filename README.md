# ipl_prediction_live

> **Data Ingestion Layer for the IPL 2026 Championship Prediction System**

A modular, resilient, local Windows-based data scraping application that collects IPL cricket data from multiple sources for machine learning prediction models.

## Features

- 🏏 **Multi-source scraping** — ESPNcricinfo (primary), Cricbuzz, IPLT20 (fallbacks)
- ⚡ **Async HTTP** — High-performance data collection with HTTP/2, retries, and rate-limiting
- 🗄️ **Dual storage** — PostgreSQL (structured) + SQLite (raw JSON warehouse)
- 📊 **Complete data coverage**:
  - Historical match results (2008-2025)
  - Ball-by-ball delivery records (~1.8M records)
  - Player statistics (batting, bowling, fielding)
  - Playing XI compositions
  - Venue metadata and pitch conditions
  - Player injuries and availability
  - Match-day weather conditions
- 🔄 **Incremental updates** — Only fetches new/changed data
- 🖥️ **Rich CLI** — Beautiful terminal interface with progress tracking
- ⏰ **Scheduled jobs** — APScheduler for automated data collection
- 🪟 **Windows native** — Desktop notifications, service integration

## Quick Start

```powershell
# Setup
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env         # Edit with your DB credentials

# Initialize
python -m src.cli init-db
python -m scripts.seed_teams_venues

# Scrape
python -m src.cli historical-scrape --start-season 2023 --end-season 2025
python -m src.cli incremental-scrape
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `historical-scrape` | Full scrape of historical seasons |
| `incremental-scrape` | Update latest season data |
| `scrape-match` | Scrape a specific match |
| `scrape-player` | Scrape a player's statistics |
| `check-injuries` | Scan news for injury updates |
| `db-health` | Check database connectivity |
| `init-db` | Create database tables |
| `export` | Export data to CSV/Parquet/JSON |
| `daemon` | Run as background service |
| `info` | Show configuration details |

## Architecture

```
┌──────────────────────────────────────────────┐
│              Orchestrator Engine              │
│        (Coordinates all scrapers)            │
├──────────┬──────────┬──────────┬─────────────┤
│   ESPN   │ Cricbuzz │  IPLT20  │   Weather   │
│ Scraper  │ Scraper  │ Scraper  │   Scraper   │
├──────────┴──────────┴──────────┴─────────────┤
│        Data Validation & Parsing Layer       │
│         (Pydantic + Custom Validators)       │
├──────────────────┬───────────────────────────┤
│   PostgreSQL     │    SQLite JSON Warehouse  │
│   (Structured)   │    (Raw HTML / API data)  │
└──────────────────┴───────────────────────────┘
```

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Windows 10/11

See **[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** for detailed installation instructions.

## Project Structure

```
iplscraper/
├── config/              # YAML configuration files
├── src/
│   ├── core/            # Orchestrator, config, state management
│   ├── scrapers/        # Data source scrapers (ESPN, Cricbuzz, IPLT20)
│   ├── parsers/         # Data normalization and parsing
│   ├── models/          # Pydantic validation schemas
│   ├── storage/         # Database repositories and connections
│   ├── utils/           # HTTP client, fuzzy matching, validators
│   ├── cli.py           # Typer CLI interface
│   └── main.py          # Application entry point
├── scripts/             # Setup and seed scripts
├── migrations/          # Alembic database migrations
├── docs/                # Documentation
├── requirements.txt     # Python dependencies
└── pyproject.toml       # Project metadata
```

## License

For personal and academic research use only. See specification for full terms.

## Credits

- Data sources: ESPNcricinfo, Cricbuzz, IPLT20
- SQAC, SRM University, Potheri, Chennai
