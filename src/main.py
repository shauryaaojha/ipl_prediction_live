"""IPL 2026 Data Scraper — Application Entry Point.

Usage:
    python -m src.main          # Start the application
    python -m src.cli --help    # CLI commands
"""

from __future__ import annotations

import asyncio
import sys

from loguru import logger

from .core.config_manager import load_config, setup_logging
from .core.orchestrator import ScraperOrchestrator
from .storage.connection import init_db, init_warehouse, check_db_health


def main():
    """Application entry point."""
    # Load configuration
    config = load_config()
    setup_logging(config)

    logger.info("=" * 60)
    logger.info("IPL 2026 Data Scraper v{}", config.get("version", "1.0.0"))
    logger.info("=" * 60)

    # Initialize storage
    try:
        init_warehouse()
        logger.info("SQLite JSON warehouse initialized.")
    except Exception as e:
        logger.error("Failed to initialize JSON warehouse: {}", e)

    # Check PostgreSQL
    health = check_db_health()
    if health["status"] == "healthy":
        logger.info("PostgreSQL connection: HEALTHY ({})", health.get("database"))
    else:
        logger.warning(
            "PostgreSQL connection: UNHEALTHY — {}. "
            "Some features will be unavailable.",
            health.get("error", "unknown"),
        )

    # Create orchestrator
    orchestrator = ScraperOrchestrator(config)

    # Run event loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Start scheduler for daemon mode
        scheduler = orchestrator.schedule_jobs()

        if scheduler:
            logger.info("Daemon mode — press Ctrl+C to stop.")
            try:
                loop.run_forever()
            except KeyboardInterrupt:
                logger.info("Shutting down...")
        else:
            logger.info("No scheduler available. Use CLI commands instead.")

    except Exception as e:
        logger.error("Application error: {}", e)
        sys.exit(1)
    finally:
        loop.run_until_complete(orchestrator.close())
        loop.close()


if __name__ == "__main__":
    main()
