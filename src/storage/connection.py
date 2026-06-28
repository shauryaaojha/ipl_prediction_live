"""Database connection management.

Provides SQLAlchemy engine, session factory, and SQLite connection for the
JSON warehouse.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from .db_models import Base


def _build_postgres_url() -> str:
    """Build PostgreSQL connection URL from environment variables."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    db = os.getenv("DB_NAME", "ipl2026")
    user = os.getenv("DB_USER", "ipl_user")
    password = os.getenv("DB_PASSWORD", "")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


# ---------------------------------------------------------------------------
# PostgreSQL Engine & Session
# ---------------------------------------------------------------------------

_engine = None
_SessionFactory = None


def get_engine(echo: bool = False):
    """Get or create the SQLAlchemy engine (singleton)."""
    global _engine
    if _engine is None:
        url = _build_postgres_url()
        _engine = create_engine(
            url,
            echo=echo,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        logger.info("PostgreSQL engine created: {}", url.split("@")[-1])
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory (singleton)."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionFactory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager that yields a database session.

    Automatically commits on success, rolls back on error, and closes the
    session when done.
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables defined by ORM models.

    Typically used during development or first-time setup. In production,
    Alembic migrations should be used instead.
    """
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("All database tables created (if not exists).")


def check_db_health() -> dict:
    """Check database connectivity and return health status."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return {"status": "healthy", "database": os.getenv("DB_NAME", "ipl2026")}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# ---------------------------------------------------------------------------
# SQLite JSON Warehouse
# ---------------------------------------------------------------------------

_warehouse_path: str | None = None


def _get_warehouse_path() -> str:
    """Get the SQLite warehouse path from config / env."""
    global _warehouse_path
    if _warehouse_path is None:
        data_path = os.getenv("DATA_PATH", "./data")
        _warehouse_path = str(Path(data_path) / "json_warehouse.db")
        Path(_warehouse_path).parent.mkdir(parents=True, exist_ok=True)
    return _warehouse_path


def get_warehouse_connection() -> sqlite3.Connection:
    """Get a new SQLite connection for the JSON warehouse."""
    path = _get_warehouse_path()
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn


def init_warehouse() -> None:
    """Create JSON warehouse tables in SQLite."""
    conn = get_warehouse_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS raw_match_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                source TEXT NOT NULL,
                url TEXT,
                html_content TEXT,
                etag TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS raw_ball_by_ball (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                source TEXT NOT NULL,
                json_payload TEXT,
                page INTEGER DEFAULT 1,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS raw_player_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                source TEXT NOT NULL,
                profile_html TEXT,
                stats_json TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS raw_news_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                content_text TEXT,
                published_date TIMESTAMP,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                nlp_entities TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_raw_match_id ON raw_match_pages(match_id);
            CREATE INDEX IF NOT EXISTS idx_raw_bbb_match ON raw_ball_by_ball(match_id);
            CREATE INDEX IF NOT EXISTS idx_raw_player ON raw_player_profiles(player_id);
        """)
        conn.commit()
        logger.info("SQLite JSON warehouse initialized at: {}", _get_warehouse_path())
    finally:
        conn.close()
