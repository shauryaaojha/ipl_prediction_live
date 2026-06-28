"""Pydantic schemas for Match data."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TossDecision(str, Enum):
    BAT = "bat"
    FIELD = "field"


class WinType(str, Enum):
    RUNS = "runs"
    WICKETS = "wickets"
    TIE = "tie"
    NO_RESULT = "no_result"
    SUPER_OVER = "super_over"


class MatchType(str, Enum):
    LEAGUE = "league"
    QUALIFIER_1 = "qualifier_1"
    ELIMINATOR = "eliminator"
    QUALIFIER_2 = "qualifier_2"
    FINAL = "final"


class MatchStatus(str, Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    COMPLETE = "complete"
    ABANDONED = "abandoned"
    TIED = "tied"


# ---------------------------------------------------------------------------
# Create / Input schema
# ---------------------------------------------------------------------------

class MatchCreate(BaseModel):
    """Schema for creating a new match record."""

    sources: dict[str, str] = Field(default_factory=dict)
    source: str = "unknown"
    season: int = Field(..., ge=2008, le=2030)
    match_number: int = Field(..., ge=0)
    match_date: datetime
    venue_name: str
    team_a: str
    team_b: str
    toss_winner: Optional[str] = None
    toss_decision: Optional[TossDecision] = None
    winner: Optional[str] = None
    win_margin: Optional[int] = Field(None, ge=0)
    win_type: Optional[WinType] = None
    player_of_match: Optional[str] = None
    dl_applied: bool = False
    match_type: MatchType = MatchType.LEAGUE
    match_status: MatchStatus = MatchStatus.UPCOMING

    @field_validator("team_a", "team_b")
    @classmethod
    def team_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Team name cannot be empty")
        return v.strip()


# ---------------------------------------------------------------------------
# Read / Output schema
# ---------------------------------------------------------------------------

class MatchRead(BaseModel):
    """Schema for reading a match record from the database."""

    match_id: UUID
    sources: dict[str, str] = Field(default_factory=dict)
    source: str
    season: int
    match_number: int
    match_date: datetime
    venue_name: str
    team_a: str
    team_b: str
    toss_winner: Optional[str] = None
    toss_decision: Optional[TossDecision] = None
    winner: Optional[str] = None
    win_margin: Optional[int] = None
    win_type: Optional[WinType] = None
    player_of_match: Optional[str] = None
    dl_applied: bool = False
    match_type: MatchType = MatchType.LEAGUE
    match_status: MatchStatus = MatchStatus.UPCOMING
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Update schema
# ---------------------------------------------------------------------------

class MatchUpdate(BaseModel):
    """Schema for updating an existing match record."""

    toss_winner: Optional[str] = None
    toss_decision: Optional[TossDecision] = None
    winner: Optional[str] = None
    win_margin: Optional[int] = None
    win_type: Optional[WinType] = None
    player_of_match: Optional[str] = None
    dl_applied: Optional[bool] = None
    match_status: Optional[MatchStatus] = None


# ---------------------------------------------------------------------------
# Match-Day Conditions
# ---------------------------------------------------------------------------

class MatchConditionsCreate(BaseModel):
    """Schema for match-day environmental conditions."""

    match_id: Optional[UUID] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = Field(None, ge=0, le=100)
    weather_condition: Optional[str] = None
    wind_speed: Optional[float] = Field(None, ge=0)
    dew_probability: Optional[float] = Field(None, ge=0, le=1)
    rest_days_team_a: int = 0
    rest_days_team_b: int = 0
    home_away_team_a: Optional[str] = None
    home_away_team_b: Optional[str] = None


class MatchConditionsRead(MatchConditionsCreate):
    """Schema for reading match conditions from DB."""

    condition_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
