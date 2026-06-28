@echo off
title IPL 2026 Data Scraper (Local Mode)
echo =======================================================
echo     Starting IPL 2026 Data Scraper (Local Mode)
echo =======================================================
echo.

:: Check if virtual environment exists, create if not
if not exist venv\ (
    echo [1/4] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/4] Virtual environment already exists.
)

:: Activate virtual environment
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

:: Install requirements
echo [3/4] Installing / Updating dependencies...
pip install -r requirements.txt

:: Check for .env file
if not exist .env (
    echo Copying .env.example to .env
    copy .env.example .env
)

:: Ensure PostgreSQL is running and credentials are set in .env before this step
echo.
echo [4/4] Initializing Database and Starting Scraper...
echo.

:: Initialize the DB (will not overwrite existing data)
python -m src.cli init-db
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to initialize the database. 
    echo Please make sure PostgreSQL is installed and running, and check your .env credentials.
    pause
    exit /b %ERRORLEVEL%
)

:: Run the daemon
echo.
echo Starting the Daemon... Press Ctrl+C to stop.
python -m src.cli daemon

pause
