@echo off
title IPL 2026 Data Scraper (Docker Mode)
echo =======================================================
echo     Starting IPL 2026 Data Scraper via Docker
echo =======================================================
echo.
echo Make sure Docker Desktop is open and running!
echo.

docker compose up --build -d

echo.
echo =======================================================
echo Containers are now running in the background.
echo.
echo Useful Commands:
echo  - To view logs: docker compose logs -f scraper
echo  - To stop the scraper: docker compose down
echo =======================================================
pause
