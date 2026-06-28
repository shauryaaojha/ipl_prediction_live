"""Pydantic schemas for Player and Player Statistics data."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BattingHand(str, Enum):
    RIGHT = "right"
    LEFT = "left"


class BowlingArm(str, Enum):
    RIGHT = "right"
    LEFT = "left"


class BowlingType(str, Enum):
    PACE = "pace"
    SPIN = "spin"
    NONE = "none"


class PlayerRole(str, Enum):
    BATSMAN = "batsman"
    BOWLER = "bowler"
    ALL_ROUNDER = "all_rounder"
    WICKETKEEPER = "wicketkeeper"
    WICKETKEEPER_BATSMAN = "wicketkeeper_batsman"


# ---------------------------------------------------------------------------
# Player Master
# ---------------------------------------------------------------------------

class PlayerCreate(BaseModel):
    """Schema for creating a player record."""

    sources: dict[str, str] = Field(default_factory=dict)
    full_name: str = Field(..., min_length=1, max_length=100)
    short_name: Optional[str] = Field(None, max_length=50)
    batting_hand: Optional[BattingHand] = None
    bowling_arm: Optional[BowlingArm] = None
    bowling_type: Optional[BowlingType] = None
    role: Optional[PlayerRole] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[date] = None
    debut_date: Optional[date] = None

    @field_validator("full_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Player name cannot be empty")
        return v.strip()


class PlayerRead(BaseModel):
    """Schema for reading a player record from the database."""

    player_id: UUID
    sources: dict[str, str] = Field(default_factory=dict)
    full_name: str
    short_name: Optional[str] = None
    batting_hand: Optional[BattingHand] = None
    bowling_arm: Optional[BowlingArm] = None
    bowling_type: Optional[BowlingType] = None
    role: Optional[PlayerRole] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[date] = None
    debut_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Player Statistics (Season-wise)
# ---------------------------------------------------------------------------

class PlayerStatsCreate(BaseModel):
    """Schema for creating season-wise player statistics."""

    player_id: Optional[str] = None  # Resolved to UUID later
    player_name: Optional[str] = None
    season: int = Field(..., ge=2008, le=2030)
    team: Optional[str] = None

    # Batting
    matches: int = Field(0, ge=0)
    innings: int = Field(0, ge=0)
    not_outs: int = Field(0, ge=0)
    runs: int = Field(0, ge=0)
    balls_faced: int = Field(0, ge=0)
    highest_score: int = Field(0, ge=0)
    highest_score_not_out: bool = False
    hundreds: int = Field(0, ge=0)
    fifties: int = Field(0, ge=0)
    fours: int = Field(0, ge=0)
    sixes: int = Field(0, ge=0)
    ducks: int = Field(0, ge=0)
    batting_average: Optional[float] = Field(None, ge=0)
    batting_strike_rate: Optional[float] = Field(None, ge=0)
    boundary_percentage: Optional[float] = Field(None, ge=0, le=100)

    # Bowling
    overs_bowled: Optional[float] = Field(None, ge=0)
    wickets: int = Field(0, ge=0)
    runs_conceded: int = Field(0, ge=0)
    bowling_average: Optional[float] = Field(None, ge=0)
    bowling_economy: Optional[float] = Field(None, ge=0)
    bowling_strike_rate: Optional[float] = Field(None, ge=0)
    four_wickets: int = Field(0, ge=0)
    five_wickets: int = Field(0, ge=0)
    dot_ball_percentage: Optional[float] = Field(None, ge=0, le=100)

    # Fielding
    catches: int = Field(0, ge=0)
    stumpings: int = Field(0, ge=0)
    run_outs_direct: int = Field(0, ge=0)
    run_outs_assisted: int = Field(0, ge=0)


class PlayerStatsRead(PlayerStatsCreate):
    """Schema for reading player stats from the database."""

    stat_id: UUID
    player_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Playing XI
# ---------------------------------------------------------------------------

class PlayingXICreate(BaseModel):
    """Schema for a player in a Playing XI."""

    match_id: Optional[str] = None
    team: str
    player_name: str
    batting_position: Optional[int] = Field(None, ge=1, le=11)
    is_captain: bool = False
    is_wicketkeeper: bool = False
    is_impact_sub: bool = False


class PlayingXIRead(BaseModel):
    """Schema for reading Playing XI from the database."""

    xi_id: UUID
    match_id: UUID
    team: str
    player_name: str
    batting_position: Optional[int] = None
    is_captain: bool
    is_wicketkeeper: bool
    is_impact_sub: bool

    model_config = {"from_attributes": True}
