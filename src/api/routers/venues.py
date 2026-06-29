"""Venues router — list, profile, trends, phase breakdown."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..deps import get_db_engine
from ..schemas import (
    VenuePhaseResponse,
    VenueResponse,
    VenueStatsResponse,
    VenueTrendResponse,
)
from ...analytics import venue_analytics

router = APIRouter(prefix="/venues", tags=["Venues"])


@router.get("", response_model=list[VenueStatsResponse])
def list_venues():
    """List all venues with their analytics stats."""
    results = venue_analytics.get_all_venues()
    return [VenueStatsResponse(**v) for v in results]


@router.get("/{venue_id}", response_model=VenueStatsResponse)
def get_venue(venue_id: UUID):
    """Get detailed venue profile from materialized view."""
    result = venue_analytics.get_venue_profile(venue_id)
    if not result:
        raise HTTPException(status_code=404, detail="Venue not found")
    return VenueStatsResponse(**result)


@router.get("/{venue_id}/trends", response_model=list[VenueTrendResponse])
def get_venue_trends(venue_id: UUID):
    """Get season-over-season scoring trends for a venue."""
    results = venue_analytics.get_venue_trend(venue_id)
    if not results:
        raise HTTPException(status_code=404, detail="No trend data found")
    return [VenueTrendResponse(**t) for t in results]


@router.get("/{venue_id}/phases", response_model=list[VenuePhaseResponse])
def get_venue_phases(venue_id: UUID):
    """Get powerplay/middle/death breakdown for a venue."""
    results = venue_analytics.get_venue_phase_breakdown(venue_id)
    if not results:
        raise HTTPException(status_code=404, detail="No phase data found")
    return [VenuePhaseResponse(**p) for p in results]
