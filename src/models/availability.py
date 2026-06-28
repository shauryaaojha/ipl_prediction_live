"""Pydantic schemas for Player Availability & Injury data."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    INJURED = "injured"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"
    UNAVAILABLE = "unavailable"
    RESTED = "rested"


class PlayerAvailabilityCreate(BaseModel):
    """Schema for creating a player availability record."""

    player_name: str
    team: str
    season: int = Field(..., ge=2008, le=2030)
    status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    injury_type: Optional[str] = None
    injury_description: Optional[str] = None
    expected_return_date: Optional[date] = None
    replacement_player: Optional[str] = None
    source_url: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1)


class PlayerAvailabilityRead(BaseModel):
    """Schema for reading a player availability record from the database."""

    availability_id: UUID
    player_name: str
    team: str
    season: int
    status: AvailabilityStatus
    injury_type: Optional[str] = None
    injury_description: Optional[str] = None
    expected_return_date: Optional[date] = None
    replacement_player: Optional[str] = None
    source_url: Optional[str] = None
    confidence_score: Optional[float] = None
    last_updated: datetime

    model_config = {"from_attributes": True}
