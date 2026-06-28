"""News NLP — regex-based entity extraction for injury data.

This module re-exports the extract_injury_entities function from the
news_scraper module and adds additional NLP utilities.
"""

from __future__ import annotations

from ..scrapers.news_scraper import extract_injury_entities

__all__ = ["extract_injury_entities"]
