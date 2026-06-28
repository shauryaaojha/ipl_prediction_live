"""Pydantic schemas for Ball-by-Ball Delivery data."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MatchPhase(str, Enum):
    POWERPLAY = "powerplay"
    MIDDLE = "middle"
    DEATH = "death"


class ExtrasType(str, Enum):
    WIDE = "wide"
    NOBALL = "noball"
    BYE = "bye"
    LEGBYE = "legbye"
    PENALTY = "penalty"


class WicketType(str, Enum):
    BOWLED = "bowled"
    CAUGHT = "caught"
    LBW = "lbw"
    RUN_OUT = "run_out"
    STUMPED = "stumped"
    HIT_WICKET = "hit_wicket"
    CAUGHT_AND_BOWLED = "caught_and_bowled"
    RETIRED_HURT = "retired_hurt"
    RETIRED_OUT = "retired_out"
    OBSTRUCTING = "obstructing_the_field"
    TIMED_OUT = "timed_out"
    HIT_TWICE = "hit_the_ball_twice"


# ---------------------------------------------------------------------------
# Create / Input schema
# ---------------------------------------------------------------------------

class DeliveryCreate(BaseModel):
    """Schema for creating a ball-by-ball delivery record."""

    match_id: Optional[str] = None  # ESPN match ID (resolved to UUID later)
    innings: int = Field(..., ge=1, le=10)
    over_number: int = Field(..., ge=0, le=19)
    ball_number: int = Field(..., ge=1, le=25)
    batting_team: Optional[str] = None
    bowling_team: Optional[str] = None
    batsman: str
    non_striker: Optional[str] = None
    bowler: str
    batsman_runs: int = Field(0, ge=0)
    extra_runs: int = Field(0, ge=0)
    total_runs: int = Field(0, ge=0)
    extras_type: Optional[ExtrasType] = None
    is_wicket: bool = False
    wicket_type: Optional[WicketType] = None
    player_dismissed: Optional[str] = None
    fielder: Optional[str] = None
    match_phase: Optional[MatchPhase] = None

    @field_validator("batsman", "bowler")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Player name cannot be empty")
        return v.strip()

    @field_validator("match_phase", mode="before")
    @classmethod
    def auto_classify_phase(cls, v, info):
        """Auto-classify phase from over number if not provided."""
        if v is not None:
            return v
        over = info.data.get("over_number")
        if over is not None:
            if over <= 5:
                return MatchPhase.POWERPLAY
            elif over <= 14:
                return MatchPhase.MIDDLE
            else:
                return MatchPhase.DEATH
        return None


# ---------------------------------------------------------------------------
# Read / Output schema
# ---------------------------------------------------------------------------

class DeliveryRead(BaseModel):
    """Schema for reading a delivery record from the database."""

    delivery_id: UUID
    match_id: UUID
    innings: int
    over_number: int
    ball_number: int
    batting_team: Optional[str] = None
    bowling_team: Optional[str] = None
    batsman: str
    non_striker: Optional[str] = None
    bowler: str
    batsman_runs: int
    extra_runs: int
    total_runs: int
    extras_type: Optional[ExtrasType] = None
    is_wicket: bool
    wicket_type: Optional[WicketType] = None
    player_dismissed: Optional[str] = None
    fielder: Optional[str] = None
    match_phase: Optional[MatchPhase] = None
    created_at: datetime

    model_config = {"from_attributes": True}
