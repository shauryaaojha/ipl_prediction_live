"""Health check router."""

from fastapi import APIRouter
from ..deps import get_db_engine
from ...storage.connection import check_db_health

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Check API and database connectivity."""
    db_status = check_db_health()
    return {
        "status": "healthy" if db_status["status"] == "healthy" else "degraded",
        "api": "running",
        "database": db_status,
    }
