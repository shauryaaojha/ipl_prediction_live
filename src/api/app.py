"""FastAPI application factory.

Creates the main FastAPI app with CORS middleware, lifespan management,
and all routers registered.

Run with:
    uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from ..storage.connection import get_engine
from .routers import analytics, health, matches, players, search, teams, venues


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    # Startup: warm up the DB connection pool
    logger.info("🚀 IPL Data Platform API starting up...")
    engine = get_engine()
    logger.info("Database connection pool initialized")
    yield
    # Shutdown
    logger.info("API shutting down...")
    engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title="IPL Data Platform API",
    description=(
        "REST API for India's most comprehensive IPL cricket analytics platform.\n\n"
        "**Features:**\n"
        "- 1,095+ matches across 17 seasons (2008–2024)\n"
        "- 260,920+ ball-by-ball deliveries\n"
        "- 880+ players with career & season stats\n"
        "- 58 venues with scoring profiles\n"
        "- Head-to-head matchups, form indexes, and death overs specialist rankings\n\n"
        "Built with FastAPI • PostgreSQL • Materialized Views"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS Middleware — allow all origins for development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Register Routers
# ---------------------------------------------------------------------------
app.include_router(health.router)
app.include_router(matches.router)
app.include_router(players.router)
app.include_router(teams.router)
app.include_router(venues.router)
app.include_router(analytics.router)
app.include_router(search.router)


# ---------------------------------------------------------------------------
# Root Endpoint
# ---------------------------------------------------------------------------

@app.get("/", tags=["Root"])
def root():
    """API information and navigation links."""
    return {
        "name": "IPL Data Platform API",
        "version": "1.0.0",
        "description": "Comprehensive IPL cricket analytics REST API",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
        },
        "endpoints": {
            "health": "/health",
            "matches": "/matches",
            "players": "/players",
            "teams": "/teams",
            "venues": "/venues",
            "analytics": {
                "batting_leaders": "/analytics/batting/leaders",
                "bowling_leaders": "/analytics/bowling/leaders",
                "death_specialists": "/analytics/bowling/death-specialists",
            },
            "search": "/search?q={query}",
        },
    }
