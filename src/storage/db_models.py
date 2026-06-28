"""SQLAlchemy ORM models for all PostgreSQL tables.

These models define the database schema and are used by Alembic for migrations
and by the repository classes for CRUD operations.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ===========================================================================
# Players
# ===========================================================================

class Player(Base):
    __tablename__ = "players"

    player_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    full_name = Column(String(100), nullable=False)
    short_name = Column(String(50), nullable=True)
    batting_hand = Column(String(10), nullable=True)
    bowling_arm = Column(String(10), nullable=True)
    bowling_type = Column(String(20), nullable=True)
    role = Column(String(30), nullable=True)
    nationality = Column(String(50), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    debut_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    aliases = relationship("PlayerAlias", back_populates="player", cascade="all, delete-orphan")
    stats = relationship("PlayerStats", back_populates="player")
    sources = relationship("PlayerSource", back_populates="player", cascade="all, delete-orphan")


class PlayerSource(Base):
    __tablename__ = "player_sources"

    player_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id", ondelete="CASCADE"), primary_key=True)
    source = Column(String(50), primary_key=True)
    source_id = Column(String(100), nullable=False)

    __table_args__ = (UniqueConstraint("source", "source_id"),)

    player = relationship("Player", back_populates="sources")


class PlayerAlias(Base):
    __tablename__ = "player_aliases"

    alias_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    player_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id", ondelete="CASCADE"), nullable=False)
    alias_name = Column(String(100), nullable=False)
    source = Column(String(50), nullable=True)

    __table_args__ = (UniqueConstraint("player_id", "alias_name"),)

    player = relationship("Player", back_populates="aliases")


# ===========================================================================
# Venues
# ===========================================================================

class Venue(Base):
    __tablename__ = "venues"

    venue_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    venue_name = Column(String(200), nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(50), default="India")
    capacity = Column(Integer, nullable=True)
    pitch_type = Column(String(20), nullable=True)
    avg_first_innings_score = Column(Numeric(6, 2), nullable=True)
    avg_second_innings_score = Column(Numeric(6, 2), nullable=True)
    chase_success_rate = Column(Numeric(5, 4), nullable=True)
    pace_advantage_index = Column(Numeric(3, 2), nullable=True)
    spin_advantage_index = Column(Numeric(3, 2), nullable=True)
    dew_factor = Column(Numeric(3, 2), nullable=True)
    espncricinfo_id = Column(String(50), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ===========================================================================
# Dataset Imports
# ===========================================================================

class DatasetImport(Base):
    __tablename__ = "dataset_imports"

    import_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    source = Column(String(50), nullable=False)
    dataset_version = Column(String(50), nullable=True)
    sha256_checksum = Column(String(64), nullable=True)
    imported_at = Column(DateTime, default=datetime.utcnow)


# ===========================================================================
# Teams
# ===========================================================================

class Team(Base):
    __tablename__ = "teams"

    team_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    team_code = Column(String(30), unique=True, nullable=False)
    team_name = Column(String(100), nullable=False)
    home_venue_id = Column(PG_UUID(as_uuid=True), ForeignKey("venues.venue_id"), nullable=True)
    founded_year = Column(Integer, nullable=True)

    home_venue = relationship("Venue")


# ===========================================================================
# Matches
# ===========================================================================

class Match(Base):
    __tablename__ = "matches"

    match_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    source = Column(String(50), default="unknown")
    season = Column(Integer, nullable=False)
    match_number = Column(Integer, nullable=False)
    match_date = Column(DateTime, nullable=False)
    venue_id = Column(PG_UUID(as_uuid=True), ForeignKey("venues.venue_id"), nullable=True)
    team_a_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    team_b_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    toss_winner_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    toss_decision = Column(String(10), nullable=True)
    winner_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    win_margin = Column(Integer, nullable=True)
    win_type = Column(String(20), nullable=True)
    player_of_match_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=True)
    dl_applied = Column(Boolean, default=False)
    match_type = Column(String(20), default="league")
    match_status = Column(String(20), default="upcoming")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("season", "match_number"),
        Index("idx_matches_season", "season"),
        Index("idx_matches_date", "match_date"),
        Index("idx_matches_status", "match_status"),
    )

    # Relationships
    venue = relationship("Venue")
    team_a = relationship("Team", foreign_keys=[team_a_id])
    team_b = relationship("Team", foreign_keys=[team_b_id])
    toss_winner = relationship("Team", foreign_keys=[toss_winner_id])
    winner = relationship("Team", foreign_keys=[winner_id])
    player_of_match = relationship("Player")
    deliveries = relationship("Delivery", back_populates="match", cascade="all, delete-orphan")
    playing_xi = relationship("PlayingXI", back_populates="match", cascade="all, delete-orphan")
    sources = relationship("MatchSource", back_populates="match", cascade="all, delete-orphan")
    conditions = relationship("MatchCondition", back_populates="match", cascade="all, delete-orphan")


class MatchSource(Base):
    __tablename__ = "match_sources"

    match_id = Column(PG_UUID(as_uuid=True), ForeignKey("matches.match_id", ondelete="CASCADE"), primary_key=True)
    source = Column(String(50), primary_key=True)
    source_id = Column(String(100), nullable=False)

    __table_args__ = (UniqueConstraint("source", "source_id"),)

    match = relationship("Match", back_populates="sources")


# ===========================================================================
# Deliveries (Ball-by-Ball)
# ===========================================================================

class Delivery(Base):
    __tablename__ = "deliveries"

    delivery_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    match_id = Column(PG_UUID(as_uuid=True), ForeignKey("matches.match_id", ondelete="CASCADE"), nullable=False)
    innings = Column(Integer, nullable=False)
    over_number = Column(Integer, nullable=False)
    ball_number = Column(Integer, nullable=False)
    batting_team_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    bowling_team_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    batsman_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=True)
    non_striker_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=True)
    bowler_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=True)
    batsman_runs = Column(Integer, default=0)
    extra_runs = Column(Integer, default=0)
    total_runs = Column(Integer, default=0)
    extras_type = Column(String(20), nullable=True)
    is_wicket = Column(Boolean, default=False)
    wicket_type = Column(String(50), nullable=True)
    player_dismissed_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=True)
    fielder_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=True)
    match_phase = Column(String(20), nullable=True)
    source = Column(String(50), default="unknown")
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("match_id", "innings", "over_number", "ball_number"),
        Index("idx_deliveries_match", "match_id"),
        Index("idx_deliveries_batsman", "batsman_id"),
        Index("idx_deliveries_bowler", "bowler_id"),
    )

    match = relationship("Match", back_populates="deliveries")


# ===========================================================================
# Playing XI
# ===========================================================================

class PlayingXI(Base):
    __tablename__ = "playing_xi"

    xi_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    match_id = Column(PG_UUID(as_uuid=True), ForeignKey("matches.match_id", ondelete="CASCADE"), nullable=False)
    team_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    player_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=True)
    batting_position = Column(Integer, nullable=True)
    is_captain = Column(Boolean, default=False)
    is_wicketkeeper = Column(Boolean, default=False)
    is_impact_sub = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("match_id", "team_id", "player_id"),
        Index("idx_playing_xi_match", "match_id"),
    )

    match = relationship("Match", back_populates="playing_xi")


# ===========================================================================
# Player Statistics (Season-wise)
# ===========================================================================

class PlayerStats(Base):
    __tablename__ = "player_stats"

    stat_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    player_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=False)
    season = Column(Integer, nullable=False)
    team_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)

    # Batting
    matches = Column(Integer, default=0)
    innings = Column(Integer, default=0)
    not_outs = Column(Integer, default=0)
    runs = Column(Integer, default=0)
    balls_faced = Column(Integer, default=0)
    highest_score = Column(Integer, default=0)
    highest_score_not_out = Column(Boolean, default=False)
    hundreds = Column(Integer, default=0)
    fifties = Column(Integer, default=0)
    fours = Column(Integer, default=0)
    sixes = Column(Integer, default=0)
    ducks = Column(Integer, default=0)
    batting_average = Column(Numeric(6, 2), nullable=True)
    batting_strike_rate = Column(Numeric(6, 2), nullable=True)
    boundary_percentage = Column(Numeric(5, 2), nullable=True)

    # Bowling
    overs_bowled = Column(Numeric(5, 1), nullable=True)
    wickets = Column(Integer, default=0)
    runs_conceded = Column(Integer, default=0)
    bowling_average = Column(Numeric(6, 2), nullable=True)
    bowling_economy = Column(Numeric(5, 2), nullable=True)
    bowling_strike_rate = Column(Numeric(6, 2), nullable=True)
    four_wickets = Column(Integer, default=0)
    five_wickets = Column(Integer, default=0)
    dot_ball_percentage = Column(Numeric(5, 2), nullable=True)

    # Fielding
    catches = Column(Integer, default=0)
    stumpings = Column(Integer, default=0)
    run_outs_direct = Column(Integer, default=0)
    run_outs_assisted = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("player_id", "season", "team_id"),
        Index("idx_player_stats_player", "player_id"),
        Index("idx_player_stats_season", "season"),
    )

    player = relationship("Player", back_populates="stats")


# ===========================================================================
# Player Availability
# ===========================================================================

class PlayerAvailability(Base):
    __tablename__ = "player_availability"

    availability_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    player_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=True)
    team_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    season = Column(Integer, nullable=False)
    status = Column(String(20), default="available")
    injury_type = Column(String(100), nullable=True)
    injury_description = Column(Text, nullable=True)
    expected_return_date = Column(Date, nullable=True)
    replacement_player_id = Column(PG_UUID(as_uuid=True), ForeignKey("players.player_id"), nullable=True)
    source_url = Column(String(500), nullable=True)
    confidence_score = Column(Numeric(3, 2), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)


# ===========================================================================
# Match-Day Conditions
# ===========================================================================

class MatchCondition(Base):
    __tablename__ = "match_conditions"

    condition_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    match_id = Column(PG_UUID(as_uuid=True), ForeignKey("matches.match_id", ondelete="CASCADE"), nullable=False)
    temperature = Column(Numeric(4, 1), nullable=True)
    humidity = Column(Numeric(5, 2), nullable=True)
    weather_condition = Column(String(50), nullable=True)
    wind_speed = Column(Numeric(5, 2), nullable=True)
    dew_probability = Column(Numeric(3, 2), nullable=True)
    rest_days_team_a = Column(Integer, default=0)
    rest_days_team_b = Column(Integer, default=0)
    home_away_team_a = Column(String(10), nullable=True)
    home_away_team_b = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="conditions")


# ===========================================================================
# Scrape Log (Audit Trail)
# ===========================================================================

class ScrapeLog(Base):
    __tablename__ = "scrape_log"

    log_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    job_name = Column(String(50), nullable=False)
    source = Column(String(50), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    records_fetched = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    status = Column(String(20), default="running")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_scrape_log_job", "job_name", "start_time"),
    )
