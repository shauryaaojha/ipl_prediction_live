# ipl_prediction_live

> **An Industry-Grade IPL Cricket Data Platform & Ingestion Engine for Analytics, AI, and ML Prediction Models**

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15%2B-316192?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Research%20Only-green?style=flat-square)](LICENSE)

---

## 🌟 Overview

`ipl_prediction_live` is a highly resilient, enterprise-grade cricket data pipeline designed to ingest, clean, normalize, and store Indian Premier League (IPL) data. Built to power downstream machine learning prediction models, analytical dashboards, and AI chatbots, the platform solves standard web-scraping brittleness by employing a **dual-pipeline architecture** with cascading multi-source fallbacks.

### 📊 Current Database Status (Completed Backfill)
- **1,095 Matches** fully normalized across **17 Seasons** (2008–2024).
- **260,920 Ball-by-Ball Deliveries** including detailed extras, wicket types, and super overs.
- **880 Players** and **58 Venues** mapped with provenance tracking.
- **Zero Orphan Records**: 100% referential integrity across foreign keys.

---

## 🏗️ Architecture & Data Flow

The ingestion architecture separates **bulk historical data acquisition** from **live incremental updates** to maximize both completeness and reliability.

```
                     EXTERNAL DATA SOURCES
 ┌──────────────────────────────────────────────────────────────┐
 │   Cricsheet (JSON)   │   IPLT20 S3   │  Cricbuzz  │   ESPN   │
 └───────────┬──────────┴───────┬───────┴─────┬──────┴────┬─────┘
             │                  │             │           │
             │ (Historical)     │             │           │ (Incremental Fallback Chain)
             ▼                  ▼             ▼           ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                Orchestrator & Fallback Engine                │
 │         [ IPLT20 S3 ──► Cricbuzz ──► ESPN ──► Retry ]        │
 └──────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                 Validation & Parsing Layer                   │
 │       (Pydantic Models • Provenance • Entity Resolution)     │
 └──────────────┬───────────────────────────────┬───────────────┘
                │                               │
                ▼                               ▼
 ┌──────────────────────────────┐   ┌───────────────────────────┐
 │          PostgreSQL          │   │   SQLite JSON Warehouse   │
 │      (Normalized Schema)     │   │     (Raw HTML / JSON)     │
 └──────────────────────────────┘   └───────────────────────────┘
```

### 1. Historical Pipeline (`Cricsheet`)
For full backfills (2008–2024), the platform pulls curated structured JSON releases from [Cricsheet](https://cricsheet.org/). This guarantees 100% accurate historical coverage without relying on brittle DOM scraping, preserving complex edge cases like tied super-overs, DLS adjustments, and retired hurts.

### 2. Incremental Pipeline (`Fallback Chain`)
For ongoing seasons and live match days, the engine uses a priority-based fallback chain:
1. **Primary (`IPLT20 S3 Feeds`)**: Undocumented, highly responsive JSONP endpoints powering official scorecards. Bypasses React hydration traps.
2. **Secondary (`Cricbuzz`)**: Fast REST API and structured HTML fallback.
3. **Tertiary (`ESPNcricinfo`)**: Fallback parser for comprehensive match metadata.
4. **Dead-Letter / Retry Queue**: Unresolved fetches are backoff-scheduled automatically via `Tenacity`.

### 3. Dual Storage Engine
- **PostgreSQL**: Serves as the primary analytical relational data warehouse. Features normalized provenance tables (`match_sources`, `player_sources`) to resolve external cross-platform IDs cleanly.
- **SQLite JSON Warehouse**: Retains raw payloads and API responses for audit trails, debugging, and lossless re-parsing.

---

## 🚀 Quick Start (Docker Compose)

The easiest way to run the entire platform is via Docker Compose.

```powershell
# 1. Clone the repository
git clone https://github.com/shauryaaojha/ipl_prediction_live.git
cd ipl_prediction_live

# 2. Setup environment variables
copy .env.example .env

# 3. Spin up PostgreSQL and build the Scraper container
docker compose up -d postgres
docker compose build scraper

# 4. Initialize Database & Seed Base Teams/Venues
docker compose run --rm scraper python -m src.cli init-db
docker compose run --rm scraper python -m scripts.seed_teams_venues

# 5. Run a Full Historical Backfill (2008-2024)
docker compose run --rm scraper python -m src.cli historical-scrape -s 2008 -e 2024

# 6. Run an Incremental Scrape for Latest Matches
docker compose run --rm scraper python -m src.cli incremental-scrape
```

---

## 🛠️ CLI Interface

The platform exposes a powerful CLI built with `Typer` and rich logging formatted by `Loguru`.

| Command | Description |
|---|---|
| `historical-scrape -s <start> -e <end>` | Bulk backfill ball-by-ball match data across season ranges. |
| `incremental-scrape` | Execute the multi-source fallback chain for latest unrecorded matches. |
| `scrape-match --id <external_id>` | Scrape and ingest a singular match by ID. |
| `init-db` | Apply database schemas and foreign key constraints. |
| `db-health` | Ping database connections and print storage stats. |

---

## 🗺️ Project Roadmap

We are following a structured **20-Phase Roadmap** to evolve this data engine into an enterprise cricket analytics platform. See the complete breakdown in **[`roadmap.md`](roadmap.md)**.

- [x] **Phase 0 & 1**: Platform Foundation & 100% Data Integrity Audits (Completed: 1,095 matches verified).
- [ ] **Phase 1.5 & 2**: Analytics Warehouse (Materialized Views, Star Schema `fact`/`dim` tables, derived stats).
- [ ] **Phase 2.5**: Search Engine Integration (Meilisearch / Elasticsearch).
- [ ] **Phase 3 & 3.5**: Interactive Next.js Dashboard (Wagon wheels, match replay, player comparisons).
- [ ] **Phase 4 & 4.5**: Public Developer Platform (FastAPI backend, API Keys, OAuth, Rate Limiting).
- [ ] **Phase 5 & 5.5**: AI Assistant & Auto-Insights (RAG, Natural Language to SQL, Scouting reports).
- [ ] **Phase 6 & 8.5**: Automated CRON Schedulers & ML Feature Store (`player_form`, `venue_bias`).

---

## 📁 Repository Structure

```text
ipl_prediction_live/
├── config/              # YAML configuration lists (scrapers, sources, logging)
├── docs/                # API endpoints and extended setup guides
├── migrations/          # Alembic database migrations
├── scripts/             # Database initialization and seeding sql/scripts
├── src/
│   ├── cli.py           # Typer command line interface entrypoint
│   ├── core/            # ScraperOrchestrator, config loader, notification system
│   ├── models/          # Pydantic data schemas (Match, Delivery, Player, Venue)
│   ├── parsers/         # Normalization modules (Cricsheet JSON parser, delivery parser)
│   ├── scrapers/        # Source modules (IPLT20, Cricbuzz, ESPNcricinfo, Weather)
│   ├── storage/         # SQLAlchemy repository pattern & SQLite warehouse
│   └── utils/           # Proxy rotator, fuzzy matcher, custom HTTP client
├── docker-compose.yml   # Multi-container Docker orchestration
├── Dockerfile           # Python 3.12-slim production container def
├── roadmap.md           # Detailed 20-phase architecture & platform evolution plan
└── requirements.txt     # Python project dependencies
```

---

## 📄 License

Developed for educational, portfolio, and analytical research purposes. All cricket metadata belongs to their respective broadcasting and governing rights holders.
