# IPL 2026 Data Scraper — Setup & Dependency Installation Guide

This guide walks you through installing **all external dependencies** that
the scraper requires but cannot install automatically. Follow the sections
in order.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Python Installation](#2-python-installation)
3. [PostgreSQL Installation](#3-postgresql-installation)
4. [Python Dependencies (pip)](#4-python-dependencies-pip)
5. [Playwright Browser Setup](#5-playwright-browser-setup-optional)
6. [Weather API Keys](#6-weather-api-keys-optional)
7. [Database Initialization](#7-database-initialization)
8. [Running the Application](#8-running-the-application)
9. [Windows Service Setup](#9-windows-service-setup-optional)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. System Requirements

| Requirement           | Minimum        | Recommended     |
|-----------------------|----------------|-----------------|
| **Operating System**  | Windows 10 64-bit | Windows 11 64-bit |
| **RAM**               | 8 GB           | 16 GB           |
| **Disk Space**        | 20 GB free     | 50 GB free      |
| **Internet**          | Required       | Stable broadband |
| **Python**            | 3.11+          | 3.12+           |
| **PostgreSQL**        | 15+            | 16+             |

---

## 2. Python Installation

### Option A: Official Installer (Recommended)

1. Go to **[python.org/downloads](https://www.python.org/downloads/)**
2. Download **Python 3.11** or **3.12** (64-bit)
3. Run the installer:
   - ✅ Check **"Add Python to PATH"**
   - ✅ Check **"Install pip"**
   - Click **"Install Now"**
4. Verify:
   ```powershell
   python --version
   pip --version
   ```

### Option B: winget (Windows Package Manager)

```powershell
winget install Python.Python.3.12
```

### Create Virtual Environment

```powershell
# Navigate to the project directory
cd C:\Users\shaur\Documents\iplscraper

# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# If you get an execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\venv\Scripts\Activate.ps1
```

> **Note:** Always activate the virtual environment before running any
> `pip install` or `python` commands for this project.

---

## 3. PostgreSQL Installation

PostgreSQL is required for storing structured match, player, and venue data.

### Step-by-Step

1. **Download** the installer from:
   **[postgresql.org/download/windows](https://www.postgresql.org/download/windows/)**

   Or use the EDB installer:
   **[enterprisedb.com/downloads/postgres-postgresql-downloads](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)**

2. **Run the installer:**
   - Choose **PostgreSQL 15** or **16**
   - Set the **superuser password** (remember this!)
   - Keep the **default port: 5432**
   - Leave the **default locale**
   - Install **pgAdmin 4** (optional GUI) and **Stack Builder** (optional)

3. **Add to PATH** (if not done by installer):
   ```powershell
   # Add PostgreSQL bin to PATH (adjust version number)
   $env:PATH += ";C:\Program Files\PostgreSQL\16\bin"

   # Or permanently:
   [Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Program Files\PostgreSQL\16\bin", [EnvironmentVariableTarget]::User)
   ```

4. **Create the database and user:**

   Open a terminal and run:
   ```powershell
   # Connect as superuser
   psql -U postgres

   # Inside the psql shell:
   CREATE DATABASE ipl2026;
   CREATE USER ipl_user WITH ENCRYPTED PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE ipl2026 TO ipl_user;
   \c ipl2026
   GRANT ALL ON SCHEMA public TO ipl_user;
   \q
   ```

5. **Verify connection:**
   ```powershell
   psql -U ipl_user -d ipl2026 -c "SELECT 1;"
   ```

### Alternative: Chocolatey

```powershell
choco install postgresql16 --params '/Password:your_postgres_password'
```

---

## 4. Python Dependencies (pip)

With the virtual environment activated:

```powershell
# Install all required dependencies
pip install -r requirements.txt
```

### What gets installed:

| Package              | Purpose                          |
|----------------------|----------------------------------|
| `httpx[http2]`       | Async HTTP client with HTTP/2    |
| `beautifulsoup4`     | HTML parsing                     |
| `lxml`               | Fast XML/HTML parser             |
| `fake-useragent`     | User-Agent rotation              |
| `pandas`             | Data manipulation                |
| `numpy`              | Numerical operations             |
| `pydantic`           | Data validation                  |
| `sqlalchemy`         | Database ORM                     |
| `psycopg2-binary`    | PostgreSQL driver                |
| `alembic`            | Database migrations              |
| `apscheduler`        | Job scheduling                   |
| `typer`              | CLI framework                    |
| `rich`               | Beautiful terminal output        |
| `loguru`             | Structured logging               |
| `pyyaml`             | YAML config parsing              |
| `python-dotenv`      | Environment variable loading     |
| `rapidfuzz`          | Fuzzy name matching              |
| `tqdm`               | Progress bars                    |
| `tenacity`           | Retry logic                      |

### Optional Dependencies

```powershell
# Browser automation (for JS-heavy sites)
pip install playwright
playwright install chromium

# Windows desktop notifications
pip install win10toast plyer

# Parquet export support
pip install pyarrow

# Or install everything:
pip install -e ".[all]"
```

---

## 5. Playwright Browser Setup (Optional)

Playwright is needed **only** for:
- Scraping IPLT20.com (JavaScript-rendered)
- Fallback when APIs return 403 (bot detection)

### Installation

```powershell
# Install the Python package
pip install playwright

# Download Chromium browser binary (~300 MB)
playwright install chromium
```

> **Note:** The Chromium binary is downloaded to
> `%LOCALAPPDATA%\ms-playwright`. This is a **one-time download**.

### Skip if...

You only plan to use the ESPNcricinfo API (which returns JSON and doesn't
need a browser). Set `ENABLE_BROWSER=false` in your `.env` file.

---

## 6. Weather API Keys (Optional)

Weather data is optional. If you want match-day temperature, humidity, and
dew probability:

### OpenWeatherMap (Free Tier)

1. Sign up at **[openweathermap.org](https://openweathermap.org/)**
2. Go to **API Keys** in your account
3. Copy the key to your `.env` file:
   ```
   OPENWEATHER_API_KEY=your_key_here
   ```
4. Free tier allows **1,000 calls/day** — more than enough.

### VisualCrossing (Alternative)

1. Sign up at **[visualcrossing.com/weather-api](https://www.visualcrossing.com/weather-api)**
2. Copy the key to your `.env` file:
   ```
   VISUALCROSSING_API_KEY=your_key_here
   ```

---

## 7. Database Initialization

### Configure Environment

```powershell
# Copy the template
Copy-Item .env.example .env

# Edit with your PostgreSQL credentials
notepad .env
```

Set these values in `.env`:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ipl2026
DB_USER=ipl_user
DB_PASSWORD=your_secure_password
```

### Create Tables

```powershell
# Option A: Using the SQL script directly
psql -U ipl_user -d ipl2026 -f scripts/setup_databases.sql

# Option B: Using the CLI (creates tables via SQLAlchemy)
python -m src.cli init-db

# Option C: Using Alembic migrations
alembic upgrade head
```

### Seed Initial Data

```powershell
# Populate teams and venues
python -m scripts.seed_teams_venues
```

This creates:
- **15 teams** (10 current + 5 historical/defunct)
- **20 venues** (Indian grounds + UAE venues)

---

## 8. Running the Application

### Check Everything Works

```powershell
# Check database connectivity
python -m src.cli db-health

# View configuration
python -m src.cli info

# Show all available commands
python -m src.cli --help
```

### Run Scraping

```powershell
# Historical scrape (2008-2025) — takes several hours
python -m src.cli historical-scrape --start-season 2023 --end-season 2025

# Incremental scrape (latest season only)
python -m src.cli incremental-scrape

# Scrape a single match
python -m src.cli scrape-match --match-id 1422130

# Check injury news
python -m src.cli check-injuries
```

### Run as Daemon

```powershell
# Runs continuously with scheduled jobs
python -m src.cli daemon
```

### Export Data

```powershell
# Export to CSV
python -m src.cli export --format csv --output ./data/exports

# Export to Parquet (requires pyarrow)
python -m src.cli export --format parquet --season 2025
```

---

## 9. Windows Service Setup (Optional)

To run the scraper as a background Windows service:

### Using NSSM (Non-Sucking Service Manager)

1. **Download NSSM** from [nssm.cc/download](https://nssm.cc/download)
2. Extract to `C:\nssm\`
3. Install the service:
   ```powershell
   C:\nssm\nssm.exe install IPL2026Scraper
   ```
4. In the NSSM GUI:
   - **Path:** `C:\Users\shaur\Documents\iplscraper\venv\Scripts\python.exe`
   - **Startup directory:** `C:\Users\shaur\Documents\iplscraper`
   - **Arguments:** `-m src.cli daemon`
5. Start the service:
   ```powershell
   C:\nssm\nssm.exe start IPL2026Scraper
   ```

### Using Task Scheduler

1. Open **Task Scheduler** (`taskschd.msc`)
2. Create a new task:
   - **Trigger:** Daily at 3:00 AM (or your preferred schedule)
   - **Action:** Start a program
   - **Program:** `C:\Users\shaur\Documents\iplscraper\venv\Scripts\python.exe`
   - **Arguments:** `-m src.cli incremental-scrape`
   - **Start in:** `C:\Users\shaur\Documents\iplscraper`

---

## 10. Troubleshooting

### PostgreSQL won't start

```powershell
# Check service status
Get-Service postgresql*

# Start manually
net start postgresql-x64-16
```

### `psycopg2` installation fails

If `pip install psycopg2-binary` fails, try:
```powershell
# Install Visual C++ Build Tools first
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Or use the pure-python driver:
pip install psycopg2-binary
```

### Permission errors with `.ps1` scripts

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### HTTP 403 / Bot Detection

- Increase `request_delay` in `config/scraper.yaml`
- Enable browser fallback: set `ENABLE_BROWSER=true` in `.env`
- Add proxies to `PROXY_LIST` in `.env`

### lxml installation fails

```powershell
# Pre-built wheel:
pip install lxml

# If that fails, install from conda:
conda install lxml
```

### Import errors

Make sure you're running from the project root directory and the virtual
environment is activated:
```powershell
cd C:\Users\shaur\Documents\iplscraper
.\venv\Scripts\Activate.ps1
python -m src.cli --help
```

---

## Quick Start Summary

```powershell
# 1. Install Python 3.11+ from python.org
# 2. Install PostgreSQL 15+ from postgresql.org
# 3. Then run:

cd C:\Users\shaur\Documents\iplscraper
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your DB credentials
python -m src.cli init-db
python -m scripts.seed_teams_venues
python -m src.cli db-health
python -m src.cli historical-scrape --start-season 2023 --end-season 2025
```

---

*Document generated for the IPL 2026 Data Scraper project.*
*Last updated: June 2026*
