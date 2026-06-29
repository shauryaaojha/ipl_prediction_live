"""API response schemas and pagination models.

These are API-specific Pydantic models for shaping responses.
The existing src/models/ schemas handle DB I/O; these handle API output.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    """Pagination metadata included in every list response."""
    page: int
    per_page: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    data: List[T]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Match Responses
# ---------------------------------------------------------------------------

class TeamBrief(BaseModel):
    team_id: Optional[UUID] = None
    team_code: Optional[str] = None
    team_name: Optional[str] = None


class VenueBrief(BaseModel):
    venue_id: Optional[UUID] = None
    venue_name: Optional[str] = None
    city: Optional[str] = None


class MatchResponse(BaseModel):
    match_id: UUID
    season: int
    match_number: int
    match_date: datetime
    match_type: Optional[str] = None
    match_status: Optional[str] = None
    venue: Optional[VenueBrief] = None
    team_a: Optional[TeamBrief] = None
    team_b: Optional[TeamBrief] = None
    toss_winner: Optional[TeamBrief] = None
    toss_decision: Optional[str] = None
    winner: Optional[TeamBrief] = None
    win_margin: Optional[int] = None
    win_type: Optional[str] = None
    dl_applied: bool = False
    source: Optional[str] = None


class ScorecardBatting(BaseModel):
    player_id: Optional[UUID] = None
    player_name: Optional[str] = None
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    strike_rate: float = 0
    dismissed_by: Optional[str] = None
    dismissal_type: Optional[str] = None


class ScorecardBowling(BaseModel):
    player_id: Optional[UUID] = None
    player_name: Optional[str] = None
    overs: float = 0
    runs: int = 0
    wickets: int = 0
    economy: float = 0
    dots: int = 0
    wides: int = 0
    noballs: int = 0


class InningsScorecard(BaseModel):
    innings: int
    batting_team: Optional[str] = None
    total_runs: int = 0
    total_wickets: int = 0
    total_overs: float = 0
    batting: List[ScorecardBatting] = []
    bowling: List[ScorecardBowling] = []


class DeliveryResponse(BaseModel):
    innings: int
    over_number: int
    ball_number: int
    batsman_runs: int
    extra_runs: int
    total_runs: int
    extras_type: Optional[str] = None
    is_wicket: bool = False
    wicket_type: Optional[str] = None


# ---------------------------------------------------------------------------
# Player Responses
# ---------------------------------------------------------------------------

class PlayerResponse(BaseModel):
    player_id: UUID
    full_name: str
    short_name: Optional[str] = None
    batting_hand: Optional[str] = None
    bowling_arm: Optional[str] = None
    bowling_type: Optional[str] = None
    role: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[date] = None


class BattingStatsResponse(BaseModel):
    player_id: str
    full_name: str
    matches: int = 0
    innings: int = 0
    total_runs: int = 0
    balls_faced: int = 0
    highest_score: Optional[int] = None
    fours: int = 0
    sixes: int = 0
    dot_balls: int = 0
    dismissals: int = 0
    not_outs: int = 0
    strike_rate: float = 0
    batting_average: Optional[float] = None
    boundary_percentage: float = 0


class BowlingStatsResponse(BaseModel):
    player_id: str
    full_name: str
    matches: int = 0
    innings: int = 0
    overs_bowled: float = 0
    runs_conceded: int = 0
    wickets: int = 0
    dot_balls: int = 0
    boundaries_conceded: int = 0
    economy_rate: Optional[float] = None
    bowling_average: Optional[float] = None
    bowling_strike_rate: Optional[float] = None
    dot_ball_percentage: float = 0


class SeasonStatsResponse(BaseModel):
    season: int
    matches: int = 0
    innings: int = 0
    runs: int = 0
    balls_faced: int = 0
    fours: int = 0
    sixes: int = 0
    dismissals: int = 0
    strike_rate: float = 0
    average: Optional[float] = None


class MatchupResponse(BaseModel):
    matches: int = 0
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    dismissals: int = 0
    dot_balls: int = 0
    strike_rate: float = 0


class FormResponse(BaseModel):
    innings: int = 0
    recent_runs: int = 0
    recent_balls: int = 0
    recent_dismissals: int = 0
    recent_strike_rate: float = 0
    recent_average: float = 0
    avg_runs_per_innings: float = 0
    form_index: float = 0


# ---------------------------------------------------------------------------
# Team Responses
# ---------------------------------------------------------------------------

class TeamResponse(BaseModel):
    team_id: UUID
    team_code: str
    team_name: str
    founded_year: Optional[int] = None
    home_venue: Optional[str] = None


class TeamRecordResponse(BaseModel):
    team_code: str
    team_name: str
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    no_results: int = 0
    win_percentage: float = 0
    tosses_won: int = 0
    toss_win_pct: float = 0
    bat_first_wins: int = 0
    chase_wins: int = 0


class TeamSeasonResponse(BaseModel):
    team_id: str
    team_code: str
    team_name: str
    played: int = 0
    wins: int = 0
    losses: int = 0
    nr: int = 0
    win_pct: float = 0
    bat_first_wins: int = 0
    chase_wins: int = 0


class TossImpactResponse(BaseModel):
    total_matches: int = 0
    tosses_won: int = 0
    toss_won_match_won: int = 0
    toss_won_match_won_pct: float = 0
    chose_bat: int = 0
    chose_bat_won: int = 0
    chose_bat_win_pct: float = 0
    chose_field: int = 0
    chose_field_won: int = 0
    chose_field_win_pct: float = 0
    toss_lost_match_won: int = 0
    toss_lost_win_pct: float = 0


class HeadToHeadResponse(BaseModel):
    team_a: Optional[str] = None
    team_b: Optional[str] = None
    total_matches: int = 0
    team_a_wins: int = 0
    team_b_wins: int = 0
    no_results: int = 0
    matches: List[dict] = []


# ---------------------------------------------------------------------------
# Venue Responses
# ---------------------------------------------------------------------------

class VenueResponse(BaseModel):
    venue_id: UUID
    venue_name: str
    city: Optional[str] = None
    country: Optional[str] = None
    capacity: Optional[int] = None
    pitch_type: Optional[str] = None


class VenueStatsResponse(BaseModel):
    venue_id: str
    venue_name: str
    city: Optional[str] = None
    total_matches: int = 0
    avg_first_innings_score: float = 0
    avg_second_innings_score: float = 0
    avg_boundaries_per_innings: float = 0
    avg_wickets_per_innings: float = 0
    chase_success_pct: float = 0
    bat_first_win_pct: float = 0
    field_first_win_pct: float = 0


class VenueTrendResponse(BaseModel):
    season: int
    matches: int = 0
    avg_1st_score: float = 0
    avg_2nd_score: float = 0
    avg_boundaries: float = 0
    avg_wickets: float = 0


class VenuePhaseResponse(BaseModel):
    phase: str
    matches: int = 0
    total_runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    wickets: int = 0
    dots: int = 0
    run_rate: float = 0
    boundary_pct: float = 0


# ---------------------------------------------------------------------------
# Search Responses
# ---------------------------------------------------------------------------

class SearchResult(BaseModel):
    type: str  # "player", "team", "venue"
    id: str
    name: str
    detail: Optional[str] = None
    score: float = 0  # relevance


class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResult]


# ---------------------------------------------------------------------------
# Analytics Leaderboard Responses
# ---------------------------------------------------------------------------

class BattingLeaderEntry(BaseModel):
    rank: int
    player_id: Optional[str] = None
    player: str
    runs: int = 0
    matches: int = 0
    innings: int = 0
    strike_rate: float = 0
    average: Optional[float] = None
    fours: int = 0
    sixes: int = 0


class BowlingLeaderEntry(BaseModel):
    rank: int
    player_id: Optional[str] = None
    player: str
    wickets: int = 0
    matches: int = 0
    overs: float = 0
    economy: float = 0
    average: Optional[float] = None
    strike_rate: Optional[float] = None


class DeathSpecialistEntry(BaseModel):
    rank: int
    player_id: str
    player: str
    overs: float = 0
    runs: int = 0
    wickets: int = 0
    dots: int = 0
    economy: float = 0
