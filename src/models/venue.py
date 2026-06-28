"""Pydantic schemas for Venue data."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VenueCreate(BaseModel):
    """Schema for creating a venue record."""

    venue_name: str = Field(..., min_length=1, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    country: str = Field("India", max_length=50)
    capacity: Optional[int] = Field(None, ge=0)
    pitch_type: Optional[str] = None
    avg_first_innings_score: Optional[float] = Field(None, ge=0)
    avg_second_innings_score: Optional[float] = Field(None, ge=0)
    chase_success_rate: Optional[float] = Field(None, ge=0, le=1)
    pace_advantage_index: Optional[float] = Field(None, ge=0, le=1)
    spin_advantage_index: Optional[float] = Field(None, ge=0, le=1)
    dew_factor: Optional[float] = Field(None, ge=0, le=1)
    home_teams: List[str] = Field(default_factory=list)
    espncricinfo_id: Optional[str] = None


class VenueRead(BaseModel):
    """Schema for reading a venue record from the database."""

    venue_id: UUID
    venue_name: str
    city: str
    country: str
    capacity: Optional[int] = None
    pitch_type: Optional[str] = None
    avg_first_innings_score: Optional[float] = None
    avg_second_innings_score: Optional[float] = None
    chase_success_rate: Optional[float] = None
    pace_advantage_index: Optional[float] = None
    spin_advantage_index: Optional[float] = None
    dew_factor: Optional[float] = None
    home_teams: List[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}
