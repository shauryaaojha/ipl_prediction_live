"""Dependency injection for FastAPI endpoints.

Provides reusable dependencies for database sessions, pagination, and caching.
"""

from __future__ import annotations

import math
from typing import Any, Optional

from fastapi import Query
from sqlalchemy import Engine

from ..storage.connection import get_engine


def get_db_engine() -> Engine:
    """Get the SQLAlchemy engine singleton."""
    return get_engine()


class PaginationParams:
    """Reusable pagination dependency for list endpoints."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.per_page = per_page
        self.offset = (page - 1) * per_page

    def meta(self, total: int) -> dict:
        """Build pagination metadata."""
        return {
            "page": self.page,
            "per_page": self.per_page,
            "total": total,
            "total_pages": math.ceil(total / self.per_page) if self.per_page else 0,
        }


# ---------------------------------------------------------------------------
# Simple in-memory TTL cache
# ---------------------------------------------------------------------------

import time
from functools import wraps


_cache: dict[str, tuple[float, Any]] = {}
_DEFAULT_TTL = 300  # 5 minutes


def cached(ttl: int = _DEFAULT_TTL):
    """Simple decorator for caching function results with TTL."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            now = time.time()
            if key in _cache:
                expires, value = _cache[key]
                if now < expires:
                    return value
            result = func(*args, **kwargs)
            _cache[key] = (now + ttl, result)
            return result
        return wrapper
    return decorator


def clear_cache():
    """Clear all cached entries."""
    _cache.clear()
